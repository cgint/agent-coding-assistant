import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI
import socketio  # type: ignore[import-untyped]

from dspy_agent_streaming_service import StreamingDspyAgentService
from dspy_pricing_service import PricingService, SingleModelPricingService
from dspy_constants import (
    MODEL_NAME_GEMINI_2_0_FLASH,
    MODEL_NAME_GEMINI_2_5_FLASH,
    MODEL_NAME_GEMINI_2_5_FLASH_LITE,
    MODEL_NAME_GEMINI_2_5_PRO,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentWebSocketManager:
    """
    WebSocket manager for handling Socket.IO connections and DSPy Agent streaming events.
    """

    def __init__(self, app: FastAPI):
        # Create Socket.IO server with ASGI integration
        self.sio = socketio.AsyncServer(
            async_mode='asgi',
            cors_allowed_origins="*",  # Configure for production
            logger=True,
            engineio_logger=True
        )
        
        # Create ASGI app
        self.socket_app = socketio.ASGIApp(self.sio, app)
        
        # Store active sessions
        self.active_sessions: Dict[str, StreamingDspyAgentService] = {}
        self.active_tasks: Dict[str, asyncio.Task[Any]] = {}
        
        # Register event handlers
        self._register_event_handlers()

    def _register_event_handlers(self) -> None:
        """Register all Socket.IO event handlers."""
        
        # --- Local helpers to augment usage with cost for history loads ---
        def _normalize_model_name(raw_model: str) -> str:
            rm = (raw_model or "").lower()
            if "/" in rm:
                rm = rm.split("/")[-1]
            if "2.5-pro" in rm:
                return MODEL_NAME_GEMINI_2_5_PRO
            if "2.5-flash-lite" in rm or "flash-lite" in rm:
                return MODEL_NAME_GEMINI_2_5_FLASH_LITE
            if "2.5-flash" in rm:
                return MODEL_NAME_GEMINI_2_5_FLASH
            if "2.0-flash" in rm or "20-flash" in rm:
                return MODEL_NAME_GEMINI_2_0_FLASH
            return MODEL_NAME_GEMINI_2_5_FLASH

        def _compute_cost_statistics(model_name_raw: Optional[str], prompt: int, completion: int) -> Optional[dict[str, Any]]:
            try:
                model_name = _normalize_model_name(model_name_raw or "")
                pricing_service = PricingService()
                model_pricing = SingleModelPricingService(model_name, pricing_service)
                stats = model_pricing.get_cost_statistics_for(prompt, completion)
                if stats is None:
                    return None
                result: dict[str, Any] = {
                    "input_cost": stats.input_cost,
                    "output_cost": stats.output_cost,
                    "total_cost": stats.total_cost,
                    "currency": stats.currency,
                }
                if (stats.currency or "").upper() == "USD":
                    result["total_cost_llm_api_usd"] = stats.total_cost
                return result
            except Exception:
                return None

        def _augment_usage_with_cost_ws(usage: Any) -> Any:
            if not isinstance(usage, dict):
                return usage
            # Already has cost?
            cost = usage.get("cost_statistics") if isinstance(usage.get("cost_statistics"), dict) else None
            if cost and (cost.get("total_cost_llm_api_usd") or cost.get("total_cost")):
                return usage
            # Flat shape
            if ("prompt_tokens" in usage) or ("completion_tokens" in usage):
                prompt = int(usage.get("prompt_tokens") or 0)
                completion = int(usage.get("completion_tokens") or 0)
                model = usage.get("model")
                cs = _compute_cost_statistics(model, prompt, completion)
                if cs is not None:
                    out = dict(usage)
                    out["cost_statistics"] = cs
                    if model:
                        out["model"] = _normalize_model_name(model)
                    return out
                return usage
            # Nested by model
            for k, v in usage.items():
                if not isinstance(v, dict):
                    continue
                if ("prompt_tokens" in v) or ("completion_tokens" in v) or ("total_tokens" in v):
                    prompt = int(v.get("prompt_tokens") or 0)
                    completion = int(v.get("completion_tokens") or 0)
                    cs = _compute_cost_statistics(k, prompt, completion)
                    if cs is not None:
                        nv = dict(v)
                        nv["cost_statistics"] = cs
                        out = dict(usage)
                        out[k] = nv
                        return out
                    return usage
            return usage
        
        @self.sio.event
        async def connect(sid, environ):  # type: ignore[no-untyped-def]
            """Handle client connection."""
            logger.info(f"Client {sid} connected")
            
            # Create streaming service for this session with event callback
            server_loop = asyncio.get_running_loop()

            async def event_callback(event_type: str, data: Dict[str, Any]) -> Any:
                await self.sio.emit(event_type, data, room=sid)

            def event_callback_threadsafe(event_type: str, data: Dict[str, Any]) -> None:
                """Fallback for sync contexts to emit via the server loop."""
                try:
                    asyncio.run_coroutine_threadsafe(
                        self.sio.emit(event_type, data, room=sid),
                        server_loop,
                    )
                except Exception as e:  # noqa: BLE001
                    logger.error(f"Thread-safe emit failed for event {event_type}: {e}")
            
            # Create service without binding persistence to Socket.IO sid
            self.active_sessions[sid] = StreamingDspyAgentService(
                event_callback=event_callback,
                threadsafe_event_callback=event_callback_threadsafe,
            )
            
            # Send welcome message
            await self.sio.emit('connection_confirmed', {
                'message': 'Connected to Google Ads Expert AI',
                'session_id': sid,
                'capabilities': [
                    'real_time_streaming',
                    'tool_progress_tracking', 
                    'grounding_information',
                    'error_handling'
                ]
            }, room=sid)

        @self.sio.event
        async def disconnect(sid):  # type: ignore[no-untyped-def]
            """Handle client disconnection."""
            logger.info(f"Client {sid} disconnected")
            
            # Cancel any active tasks
            if sid in self.active_tasks:
                self.active_tasks[sid].cancel()
                del self.active_tasks[sid]
            
            # Clean up session
            if sid in self.active_sessions:
                del self.active_sessions[sid]

        @self.sio.event
        async def ask_question(sid, data):  # type: ignore[no-untyped-def]
            """Handle question from client and start streaming response."""
            question = data.get('question', '').strip()
            client_session_id = data.get('session_id')
            
            if not question:
                await self.sio.emit('error', {
                    'message': 'Question is required and cannot be empty',
                    'error_type': 'validation_error'
                }, room=sid)
                return
            
            service = self.active_sessions.get(sid)
            if not service:
                await self.sio.emit('error', {
                    'message': 'Session not found. Please reconnect.',
                    'error_type': 'session_error'
                }, room=sid)
                return

            # If client provided a logical session id, use it for persistence
            if client_session_id:
                service.set_session_id(client_session_id)
            
            # Cancel any existing task for this session
            if sid in self.active_tasks:
                self.active_tasks[sid].cancel()
            
            # Start streaming response
            async def stream_response() -> None:
                try:
                    logger.info(f"Starting stream_response for session {sid} with question: {question[:50]}...")
                    async for event in service.stream_answer(question):
                        # Events are automatically emitted by the service callback
                        # We just need to handle the async generator
                        pass
                    logger.info(f"Successfully completed stream_response for session {sid}")
                except Exception as e:
                    import traceback
                    from builtins import BaseExceptionGroup  # Python 3.11+
                    
                    # Get full traceback
                    full_traceback = traceback.format_exc()
                    logger.error(f"=== DETAILED ERROR in streaming response for {sid} ===")
                    logger.error(f"Exception type: {type(e).__name__}")
                    logger.error(f"Exception message: {str(e)}")
                    logger.error(f"Full traceback:\n{full_traceback}")
                    
                    # If it's an ExceptionGroup, log the sub-exceptions
                    if isinstance(e, BaseExceptionGroup):
                        logger.error(f"ExceptionGroup contains {len(e.exceptions)} sub-exceptions:")
                        for i, sub_exc in enumerate(e.exceptions):
                            logger.error(f"  Sub-exception {i+1}: {type(sub_exc).__name__}: {sub_exc}")
                            # Get traceback for sub-exception if available
                            if hasattr(sub_exc, '__traceback__') and sub_exc.__traceback__:
                                sub_tb = ''.join(traceback.format_exception(type(sub_exc), sub_exc, sub_exc.__traceback__))
                                logger.error(f"  Sub-exception {i+1} traceback:\n{sub_tb}")
                    
                    logger.error("=== END DETAILED ERROR ===")
                    
                    await self.sio.emit('error', {
                        'message': f'Unexpected error: {str(e)}',
                        'error_type': 'processing_error',
                        'exception_type': type(e).__name__,
                        'traceback': full_traceback if len(full_traceback) < 1000 else full_traceback[:1000] + "..."
                    }, room=sid)
                finally:
                    # Clean up task reference
                    if sid in self.active_tasks:
                        del self.active_tasks[sid]
            
            # Create and store task
            task = asyncio.create_task(stream_response())
            self.active_tasks[sid] = task

        @self.sio.event
        async def cancel_question(sid, data):  # type: ignore[no-untyped-def]
            """Handle request to cancel current question processing."""
            if sid in self.active_tasks:
                self.active_tasks[sid].cancel()
                del self.active_tasks[sid]
                
                await self.sio.emit('question_cancelled', {
                    'message': 'Question processing cancelled',
                    'timestamp': self._get_timestamp()
                }, room=sid)
            else:
                await self.sio.emit('error', {
                    'message': 'No active question to cancel',
                    'error_type': 'state_error'
                }, room=sid)

        @self.sio.event
        async def get_session_info(sid, data):  # type: ignore[no-untyped-def]
            """Get information about the current session."""
            service = self.active_sessions.get(sid)
            has_active_task = sid in self.active_tasks
            
            await self.sio.emit('session_info', {
                'session_id': sid,
                'service_available': service is not None,
                'has_active_task': has_active_task,
                'timestamp': self._get_timestamp()
            }, room=sid)

        @self.sio.event
        async def load_session_history(sid, data):  # type: ignore[no-untyped-def]
            """Load and return session history for display."""
            service = self.active_sessions.get(sid)
            if not service:
                await self.sio.emit('session_history_loaded', {
                    'history': [],
                    'message': 'No session available'
                }, room=sid)
                return

            try:
                # Prefer client-provided logical session id, fallback to Socket.IO sid
                client_session_id = (data or {}).get('session_id')
                effective_session_id = client_session_id or service.session_id or sid

                # Ensure the service is configured and has a history manager
                if effective_session_id:
                    service.set_session_id(effective_session_id)

                history_entries = service.history_manager.get_chat_history(effective_session_id) if service.history_manager else []
                # Convert to format suitable for web display
                history_data = []
                for entry in history_entries:
                    history_data.append({
                        'question': entry.question,
                        'answer': entry.answer,
                        'timestamp': entry.timestamp.isoformat(),
                        'usage_metadata': _augment_usage_with_cost_ws(entry.usage_metadata),
                        # Expose persisted tool calls to the client if available
                        'tools': [
                            {
                                'id': tool.id,
                                'name': tool.name,
                                'status': tool.status,
                                'started_at': tool.started_at.isoformat() if tool.started_at else None,
                                'ended_at': tool.ended_at.isoformat() if tool.ended_at else None,
                                'duration_ms': tool.duration_ms,
                                'input_summary': tool.input_summary,
                                'result_preview': tool.result_preview,
                                'error': tool.error,
                            }
                            for tool in (entry.tools or [])
                        ]
                    })

                await self.sio.emit('session_history_loaded', {
                    'history': history_data,
                    'count': len(history_data)
                }, room=sid)

            except Exception as e:
                logger.error(f"Error loading session history for {sid}: {e}")
                await self.sio.emit('session_history_loaded', {
                    'history': [],
                    'error': str(e)
                }, room=sid)

        @self.sio.event
        async def ping(sid, data):  # type: ignore[no-untyped-def]
            """Handle ping for connection testing."""
            await self.sio.emit('pong', {
                'timestamp': self._get_timestamp(),
                'received_data': data
            }, room=sid)

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()

    def get_asgi_app(self) -> Any:
        """Get the ASGI app for mounting in FastAPI."""
        return self.socket_app
