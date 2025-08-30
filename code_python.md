# Directory Structure
_Includes files where the actual content might be omitted. This way the LLM can still use the file structure to understand the project._
```
.
├── api
│   ├── __init__.py
│   ├── main.py
│   ├── routes
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   └── health.py
│   └── websocket_manager.py
├── chat_history_converter.py
├── dspy_agent_classifier_credentials_passwords_examples.py
├── dspy_agent_classifier_credentials_passwords_optimized.py
├── dspy_agent_classifier_credentials_passwords.py
├── dspy_agent_expert_ai.py
├── dspy_agent_lm_vertexai.py
├── dspy_agent_refactored.py
├── dspy_agent_service.py
├── dspy_agent_streaming_service.py
├── dspy_agent_tool_internal_knowledge.py
├── dspy_agent_tool_rm_tavily.py
├── dspy_agent_tool_streaming_internal_knowledge.py
├── dspy_agent_tool_streaming_websearch_tavily.py
├── dspy_agent_tool_websearch_tavily.py
├── dspy_agent_util_grounding_manager.py
├── dspy_agent_util_streaming_grounding_manager.py
├── dspy_constants.py
├── dspy_pricing_service.py
├── session_history_manager.py
├── session_models.py
├── session_storage.py
├── start_server.py
├── test_websocket_client.py
└── web
    └── start_web_server.py
```

# File Contents

## File: `api/__init__.py`
```
# API package for Google Ads Expert AI
```

## File: `api/main.py`
```
from fastapi import FastAPI, Request, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Tuple, Any
import uvicorn
import os
import glob

from api.websocket_manager import AgentWebSocketManager
from api.routes import health, agent
from dspy_agent_streaming_service import StreamingDspyAgentService
import json
from dspy_constants import MODEL_NAME_GEMINI_2_5_FLASH

import mlflow
mlflow.set_experiment("dspy_agent_coding_assistant_api_main")
mlflow.autolog()

# Create FastAPI application
app = FastAPI(
    title="Google Ads Expert AI API",
    description="Streaming AI agent for Google Ads expertise using DSPy",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)
# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "https://support-researcher.prod.devsupport.smec.services"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Include HTTP routes
app.include_router(health.router, tags=["health"])
app.include_router(agent.router, prefix="/api/v1", tags=["agent"])

# Initialize WebSocket manager
websocket_manager = AgentWebSocketManager(app)

# Mount Socket.IO app
socket_app = websocket_manager.get_asgi_app()

# Configure DSPy only once
StreamingDspyAgentService.configure_dspy()

# --- Authentication and Config Functions (matching original pattern) ---
def get_atlassian_auth(request: Request) -> Tuple[str, str, str]:
    """Get Atlassian authentication from request headers (for future Confluence integration)."""
    atlassian_email = request.headers.get('atlassian-email')
    atlassian_token = request.headers.get('atlassian-token')
    
    if atlassian_email and atlassian_token:
        return (atlassian_email, atlassian_token, "from-request")
    else:
        # Fallback to environment variables when available
        email = os.environ.get('ATTL_EMAIL', '')
        token = os.environ.get('ATTL_KEY', '')
        return (email, token, f"from-env ({bool(atlassian_email)}, {bool(atlassian_token)})")

# --- Pydantic Models ---
class ChatRequest(BaseModel):
    query: str
    session_id: str
    model_category: Optional[str] = "medium"

class ChatResponse(BaseModel):
    answer: str
    session_id: str
    model: Optional[str] = None
    token_count: Optional[dict[str, Any]] = None


# Add Gzip middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add no-cache headers to all HTML endpoints
@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next: Any) -> Response:
    response: Response = await call_next(request)
    
    # Add no-cache headers to HTML, JS, and CSS responses
    if response.headers.get("content-type"):
        content_type: str = response.headers.get("content-type", "")
        if any(mime in content_type for mime in ["text/html", "application/javascript", "text/css"]):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
    
    return response

# --- Main Endpoints (matching original pattern) ---
@app.get("/")
async def root() -> FileResponse:
    """Serve the main interface."""
    return FileResponse("web/index.html")

@app.get("/ping")
async def ping(request: Request) -> dict[str, str]:
    """Health check endpoint that logs headers."""
    print(" | ".join([f"{k}: {v}" for k, v in request.headers.items()]))
    return {"status": "PONG"}

@app.post("/chat/ask", response_model=ChatResponse)
async def chat_endpoint(chat_request: ChatRequest, request: Request) -> ChatResponse:
    """Main chat endpoint (renamed from /chat/react to /chat/ask)."""
    try:
        # Get authentication info (for future use)
        # atlassian_email, atlassian_token, source = get_atlassian_auth(request)
        
        # Create streaming service for this request
        service = StreamingDspyAgentService()
        
        # Process the request
        final_answer, usage_metadata_str = await service.answer_one_question_async(
            chat_request.query
        )
        
        # Parse usage metadata
        usage_metadata = json.loads(usage_metadata_str) if usage_metadata_str else {}
        
        return ChatResponse(
            answer=final_answer,
            session_id=chat_request.session_id,
            model=usage_metadata.get('model', MODEL_NAME_GEMINI_2_5_FLASH),
            token_count=usage_metadata
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ChatResponse(
            answer=f"Error in process_chat_request: {e}", 
            session_id=chat_request.session_id
        )

# --- Combined JS/CSS Endpoints (matching original pattern) ---
@app.get("/js/app.js")
async def combined_js() -> Response:
    """Serve all JS files combined."""
    js_content = ""
    
    # Add our main app.js
    try:
        with open("web/app.js", "r") as f:
            js_content += "/* app.js */\n"
            js_content += f.read() + "\n\n"
    except FileNotFoundError:
        pass
    
    # Add any additional JS files from web/static if they exist
    js_files = glob.glob("web/static/*.js")
    for js_file in sorted(js_files):
        # Skip certain files
        if os.path.basename(js_file) not in ["showdown.min.js"]:
            with open(js_file, "r") as f:
                js_content += f"/* {os.path.basename(js_file)} */\n"
                js_content += f.read() + "\n\n"
    
    return Response(content=js_content, media_type="application/javascript")

@app.get("/style/style.css")
async def combined_css() -> Response:
    """Serve all CSS files combined."""
    css_content = ""
    
    # Add any CSS files from web/static if they exist
    css_files = glob.glob("web/static/*.css")
    for css_file in sorted(css_files):
        with open(css_file, "r") as f:
            css_content += f"/* {os.path.basename(css_file)} */\n"
            css_content += f.read() + "\n\n"
    
    return Response(content=css_content, media_type="text/css")

@app.get("/socket.io-info")
async def socket_io_info() -> dict[str, Any]:
    """Information about Socket.IO integration."""
    return {
        "websocket_url": "/socket.io/",
        "events": {
            "client_to_server": [
                "ask_question",
                "cancel_question",
                "get_session_info", 
                "ping"
            ],
            "server_to_client": [
                "connection_confirmed",
                "question_start",
                "tool_start",
                "tool_progress", 
                "tool_complete",
                "tool_error",
                "answer_chunk",
                "grounding_update",
                "answer_complete",
                "question_cancelled",
                "session_info",
                "error",
                "pong"
            ]
        },
        "example_usage": {
            "connect": "const socket = io('http://localhost:8000');",
            "ask_question": "socket.emit('ask_question', {question: 'Your question here'});",
            "listen_events": "socket.on('answer_chunk', (data) => console.log(data));"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "api.main:socket_app",  # Use the Socket.IO ASGI app
        host="127.0.0.1",
        port=9191,
        reload=True,
        log_level="info"
    )
```

## File: `api/routes/__init__.py`
```
# API routes package
```

## File: `api/routes/agent.py`
```
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any
import asyncio

from dspy_agent_streaming_service import StreamingDspyAgentService, create_standard_service

router = APIRouter()


class QuestionRequest(BaseModel):
    question: str


class QuestionResponse(BaseModel):
    answer: str
    usage_metadata: dict[str, Any]
    grounding: dict[str, Any]


@router.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest) -> QuestionResponse:
    """
    Ask a question to the Google Ads Expert AI (non-streaming HTTP endpoint).
    For real-time streaming, use the WebSocket connection.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    try:
        # Create a temporary streaming service for this request
        service = StreamingDspyAgentService()
        
        # Get the answer
        final_answer, usage_metadata_str = await service.answer_one_question_async(
            request.question
        )
        
        # Parse usage metadata
        import json
        usage_metadata = json.loads(usage_metadata_str) if usage_metadata_str else {}
        
        # Get grounding data
        grounding_data = service.grounding_manager.get_grounding_data()
        
        return QuestionResponse(
            answer=final_answer,
            usage_metadata=usage_metadata,
            grounding=grounding_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")


@router.post("/ask-sync", response_model=QuestionResponse)
async def ask_question_sync(request: QuestionRequest) -> QuestionResponse:
    """
    Ask a question using the original synchronous service (for compatibility).
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    try:
        # Use the original synchronous service
        service = create_standard_service()
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        final_answer, usage_metadata_str = await loop.run_in_executor(
            None, 
            service.answer_one_question,
            request.question
        )
        
        # Parse usage metadata
        import json
        usage_metadata = json.loads(usage_metadata_str) if usage_metadata_str else {}
        
        # Get grounding data from the service
        grounding_data = service.grounding_manager.get_grounding_data() if hasattr(service.grounding_manager, 'get_grounding_data') else {
            "sources": service.grounding_manager.sources,
            "queries": service.grounding_manager.queries,
            "supports": service.grounding_manager.supports
        }
        
        return QuestionResponse(
            answer=final_answer,
            usage_metadata=usage_metadata,
            grounding=grounding_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")


@router.get("/capabilities")
async def get_capabilities() -> dict[str, Any]:
    """Get AI capabilities and available features."""
    return {
        "features": [
            "google_ads_expertise",
            "internal_knowledge_base",
            "web_search_integration",
            "real_time_streaming",
            "grounding_information",
            "source_tracking"
        ],
        "tools": [
            {
                "name": "internal_knowledge",
                "description": "Search internal Google Ads knowledge base"
            },
            {
                "name": "web_search",
                "description": "Search web with Tavily integration"
            }
        ],
        "endpoints": {
            "http": {
                "ask": "/ask",
                "ask_sync": "/ask-sync",
                "capabilities": "/capabilities"
            },
            "websocket": {
                "connection": "/socket.io/",
                "events": [
                    "ask_question",
                    "cancel_question", 
                    "get_session_info",
                    "ping"
                ]
            }
        }
    }
```

## File: `api/routes/health.py`
```
from fastapi import APIRouter
from datetime import datetime
from typing import Any
import sys

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Google Ads Expert AI",
        "version": "0.1.0"
    }


@router.get("/health/detailed")
async def detailed_health_check() -> dict[str, Any]:
    """Detailed health check with system information."""
    import psutil
    import os
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Google Ads Expert AI",
        "version": "0.1.0",
        "system": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "python_version": sys.version,
        },
        "environment": {
            "has_google_api_key": bool(os.getenv("GOOGLE_API_KEY")),
            "has_tavily_api_key": bool(os.getenv("TAVILY_API_KEY")),
        }
    }
```

## File: `api/websocket_manager.py`
```
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
```

## File: `chat_history_converter.py`
```
#!/usr/bin/env python3
"""
Self-contained chat history converter for UV Python.
- Converts all chat_history_ask-*.json in history_ask/ to markdown and HTML.
- Outputs to same directory as input files (history_ask/).
- Uses proper markdown library for HTML rendering.
"""
# /// script
# dependencies = [
#     "markdown>=3.4.0",
# ]
# requires-python = ">=3.11"
# ///
import json
from pathlib import Path
from datetime import datetime
from html import escape as html_escape
from typing import Any

# Import markdown library
import markdown

INPUT_DIR = Path('history_ask')
OUTPUT_DIR = INPUT_DIR  # Output to same directory as input
MD_OVERVIEW = OUTPUT_DIR / 'chat_history_overview.md'
HTML_OVERVIEW = OUTPUT_DIR / 'chat_history_overview.html'

# --- Utility functions ---
def discover_files():
    files = list(INPUT_DIR.glob('chat_history_ask-*.json'))
    return files

def parse_chat_history(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        entries = data.get('entries', [])
        return entries
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return []

def extract_timestamp_from_filename(filename: Path) -> datetime | None:
    # Format: chat_history_ask-YYYYMMDD_HHMMSS.json
    try:
        base = filename.name.replace('chat_history_ask-', '').replace('.json', '')
        dt = datetime.strptime(base, '%Y%m%d_%H%M%S')
        return dt
    except Exception:
        return None

def sort_files_chronologically(files: list[Path]) -> list[Path]:
    files_with_ts = [(f, extract_timestamp_from_filename(f)) for f in files]
    # Only keep files with valid timestamps
    files_with_ts = [x for x in files_with_ts if x[1] is not None]
    # Sort by datetime (guaranteed not None)
    files_with_ts.sort(key=lambda x: x[1] if x[1] is not None else datetime.min)
    return [x[0] for x in files_with_ts]

def format_timestamp(ts: str) -> str:
    try:
        return datetime.strptime(ts, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M')
    except Exception:
        return ts

# --- Markdown Generation ---
def generate_markdown_session(entries: list[dict[str, Any]], session_name: str) -> str:
    md = [f'# Chat History - {session_name}\n']
    for entry in entries:
        if not entry.get('user_visible_entry', True):
            md.append('<details>')
            md.append(f'<summary>🔧 Tool Call - {format_timestamp(entry.get("timestamp_start", ""))} (Hidden)</summary>\n')
            md.append(f'**Query:** {entry.get("query", "")}')
            md.append(f'\n**Answer:** {entry.get("answer", "")}')
            md.append('</details>\n')
        else:
            md.append(f'**User Query:**\n> {entry.get("query", "")}\n')
            md.append(f'**Assistant Response:**\n{entry.get("answer", "")}\n')
    return '\n'.join(md)

# --- HTML Generation ---
def generate_html(all_entries: list[dict[str, Any]]) -> str:
    html = [
        '<!DOCTYPE html>',
        '<html>',
        '<head>',
        '<meta charset="utf-8">',
        '<title>Chat History - Complete Archive</title>',
        '<style>',
        'body { font-family: Arial, sans-serif; margin: 40px; }',
        '.entry { margin: 20px 0; border: 1px solid #ddd; }',
        '.entry-header { background: #f5f5f5; padding: 10px; cursor: pointer; }',
        '.entry-content { padding: 15px; display: none; }',
        '.user-visible { border-left: 4px solid #007bff; }',
        '.hidden-entry { border-left: 4px solid #6c757d; opacity: 0.8; }',
        '.timestamp { color: #666; font-size: 0.9em; }',
        '</style>',
        '<script>',
        'function toggleEntry(id) {',
        '  var content = document.getElementById(id);',
        '  content.style.display = content.style.display === "none" ? "block" : "none";',
        '}',
        '</script>',
        '</head>',
        '<body>',
        '<h1>Chat History - Complete Archive</h1>'
    ]
    # Table of Contents
    toc: dict[str, int] = {}
    for entry in all_entries:
        date = entry['timestamp_start'][:10]
        toc.setdefault(date, 0)
        toc[date] += 1
    html.append('<h2>Table of Contents</h2>')
    html.append('<ul>')
    for date, count in sorted(toc.items()):
        html.append(f'<li><a href="#{date}">{date}</a> ({count} entries)</li>')
    html.append('</ul>')
    # Entries by date
    last_date = None
    entry_id = 0
    for entry in all_entries:
        date = entry['timestamp_start'][:10]
        if date != last_date:
            html.append(f'<h2 id="{date}">{date}</h2>')
            last_date = date
        entry_id += 1
        eid = f'entry{entry_id}'
        if not entry.get('user_visible_entry', True):
            html.append('<div class="entry hidden-entry">')
            html.append(f'<div class="entry-header" onclick="toggleEntry(\'{eid}\')">🔧 Tool Call - {html_escape(format_timestamp(entry.get("timestamp_start", "")))} (Click to expand)</div>')
            html.append(f'<div class="entry-content" id="{eid}" style="display:none;">')
            html.append(f'<strong>Query:</strong> {html_escape(entry.get("query", ""))}<br/>')
            html.append(f'<strong>Answer:</strong> {html_escape(entry.get("answer", ""))}')
            html.append('</div></div>')
        else:
            html.append('<div class="entry user-visible">')
            html.append(f'<div class="entry-header">User Query - {html_escape(format_timestamp(entry.get("timestamp_start", "")))} </div>')
            html.append('<div class="entry-content" style="display:block;">')
            html.append(f'<strong>Query:</strong> {html_escape(entry.get("query", ""))}<br/>')
            html.append(f'<strong>Answer:</strong> {html_escape(entry.get("answer", ""))}')
            html.append('</div></div>')
    html.append('</body></html>')
    return '\n'.join(html)

def generate_html_session(entries: list[dict[str, Any]], session_name: str) -> str:
    md = markdown.Markdown(extensions=['codehilite', 'fenced_code', 'tables'])
    html = [
        '<!DOCTYPE html>',
        '<html>',
        '<head>',
        '<meta charset="utf-8">',
        f'<title>Chat History - {session_name}</title>',
        '<style>',
        'body { font-family: Arial, sans-serif; margin: 40px; }',
        '.entry { margin: 20px 0; border: 1px solid #ddd; }',
        '.entry-header { background: #f5f5f5; padding: 10px; cursor: pointer; }',
        '.entry-content { padding: 15px; display: none; }',
        '.user-visible { border-left: 4px solid #007bff; }',
        '.hidden-entry { border-left: 4px solid #6c757d; opacity: 0.8; }',
        '.timestamp { color: #666; font-size: 0.9em; }',
        'pre, code { background: #f8f8f8; border-radius: 3px; padding: 2px 4px; }',
        'pre { padding: 10px; overflow-x: auto; }',
        'table { border-collapse: collapse; width: 100%; }',
        'th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }',
        'th { background-color: #f2f2f2; }',
        '</style>',
        '<script>',
        'function toggleEntry(id) {',
        '  var content = document.getElementById(id);',
        '  content.style.display = content.style.display === "none" ? "block" : "none";',
        '}',
        '</script>',
        '</head>',
        '<body>',
        f'<h1>Chat History - {session_name}</h1>'
    ]
    entry_id = 0
    for entry in entries:
        entry_id += 1
        eid = f'entry{entry_id}'
        query_html = md.convert(entry.get("query", ""))
        answer_html = md.convert(entry.get("answer", ""))
        md.reset()  # Reset for next conversion
        if not entry.get('user_visible_entry', True):
            html.append('<div class="entry hidden-entry">')
            html.append(f'<div class="entry-header" onclick="toggleEntry(\'{eid}\')">🔧 Tool Call - {html_escape(format_timestamp(entry.get("timestamp_start", "")))} (Click to expand)</div>')
            html.append(f'<div class="entry-content" id="{eid}" style="display:none;">')
            html.append(f'<strong>Query:</strong> {query_html}<br/>')
            html.append(f'<strong>Answer:</strong> {answer_html}')
            html.append('</div></div>')
        else:
            html.append('<div class="entry user-visible">')
            html.append(f'<div class="entry-header">User Query - {html_escape(format_timestamp(entry.get("timestamp_start", "")))} </div>')
            html.append('<div class="entry-content" style="display:block;">')
            html.append(f'<strong>Query:</strong> {query_html}<br/>')
            html.append(f'<strong>Answer:</strong> {answer_html}')
            html.append('</div></div>')
    html.append('</body></html>')
    return '\n'.join(html)

# --- Main Execution ---
def main() -> None:
    files = discover_files()
    files = sort_files_chronologically(files)
    session_md_files = []
    session_html_files = []
    for file in files:
        session_name = file.name.replace('.json', '')
        md_file = OUTPUT_DIR / f"{session_name}.md"
        html_file = OUTPUT_DIR / f"{session_name}.html"
        if md_file.exists() and html_file.exists():
            session_md_files.append(md_file)
            session_html_files.append(html_file)
            continue
        entries = parse_chat_history(file)
        md_content = generate_markdown_session(entries, session_name)
        html_content = generate_html_session(entries, session_name)
        with open(md_file, 'w', encoding='utf-8') as mdf:
            mdf.write(md_content)
        with open(html_file, 'w', encoding='utf-8') as htmlf:
            htmlf.write(html_content)
        session_md_files.append(md_file)
        session_html_files.append(html_file)
    # Generate overview files
    with open(MD_OVERVIEW, 'w', encoding='utf-8') as f:
        f.write('# Chat History Overview\n\n')
        for mdfile in session_md_files:
            f.write(f'- [{mdfile.name}]({mdfile.name})\n')
    with open(HTML_OVERVIEW, 'w', encoding='utf-8') as f:
        f.write('<!DOCTYPE html><html><head><meta charset="utf-8"><title>Chat History Overview</title></head><body>\n')
        f.write('<h1>Chat History Overview</h1><ul>\n')
        for htmlfile in session_html_files:
            f.write(f'<li><a href="{htmlfile.name}">{htmlfile.name}</a></li>\n')
        f.write('</ul></body></html>\n')
    print(f"Conversion complete. Markdown overview: {MD_OVERVIEW}, HTML overview: {HTML_OVERVIEW}")

if __name__ == '__main__':
    main() ```

## File: `dspy_agent_classifier_credentials_passwords_examples.py`
```
from typing import Dict, List, Set
import dspy
import random

# ---- start train-set from codegiant -----

examples_for_classification_train_set_giant: List[Dict[str, str]] = [
    # Unsafe: Plaintext User/Password
    {
        "classify_input": "Hello, here is my user 'cgint' and password: 12356!",
        "classification": "unsafe"
    },
    {
        "classify_input": "My login is user@example.com and my password is Password123!",
        "classification": "unsafe"
    },
    {
        "classify_input": "Here are the credentials: username=testuser, password=testpassword",
        "classification": "unsafe"
    },
    {
        "classify_input": "For the FTP server, use ftp_user and P@ssw0rd!",
        "classification": "unsafe"
    },
    {
        "classify_input": "The account details are 'john.doe' with the temporary password 'changeme'.",
        "classification": "unsafe"
    },
    {
        "classify_input": "ssh login: root@192.168.1.1, password is toor",
        "classification": "unsafe"
    },
    {
        "classify_input": "Just use my credentials for now: alice / 12345678",
        "classification": "unsafe"
    },
    {
        "classify_input": "The default password for the router is 'admin123'.",
        "classification": "unsafe"
    },
    {
        "classify_input": "Here's the login for the staging server: stage_user / St@g!ngP@ss",
        "classification": "unsafe"
    },
    {
        "classify_input": "The wifi password is 'GuestNetwork123'.",
        "classification": "unsafe"
    },
    {
        "classify_input": "For the database, the user is 'db_admin' and the password is 'dbs3cr3t'.",
        "classification": "unsafe"
    },
    # Unsafe: API Keys and Tokens
    {
        "classify_input": "My OpenAI API key is sk-aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890.",
        "classification": "unsafe"
    },
    {
        "classify_input": "Use this bearer token: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.ZRrHA19WJ2ACtGgYgdHHd3xG8I5iPYZ_trc_yI-tX2A",
        "classification": "unsafe"
    },
    {
        "classify_input": "The GitHub token is ghp_xYzAbCdEfGhIjKlMnOpQrStUvWxYzAbCdEfGh.",
        "classification": "unsafe"
    },
    {
        "classify_input": "Here's the Slack bot token: xoxb-1234567890-abcdefghijklmnopqrstuvwxyz.",
        "classification": "unsafe"
    },
    {
        "classify_input": "Set the STRIPE_API_KEY to pk_live_xxxxxxxxxxxxxxxxxxxxxxxx.",
        "classification": "unsafe"
    },
    {
        "classify_input": "The authorization key is 'Authorization: Basic YWxhZGRpbjpvcGVuc2VzYW1l'.",
        "classification": "unsafe"
    },
    {
        "classify_input": "My AWS access key ID is AKIAIOSFODNN7EXAMPLE.",
        "classification": "unsafe"
    },
    {
        "classify_input": "And the AWS secret access key is wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY.",
        "classification": "unsafe"
    },
    {
        "classify_input": "The API secret for the service is 1a2b3c4d-5e6f-7g8h-9i0j-k1l2m3n4o5p6.",
        "classification": "unsafe"
    },
    {
        "classify_input": "The client secret is 'my_super_secret_client_secret_123'.",
        "classification": "unsafe"
    },
    # Unsafe: Connection Strings
    {
        "classify_input": "DB connection string: postgresql://user:password@host:5432/mydatabase",
        "classification": "unsafe"
    },
    {
        "classify_input": "The connection URL is mysql://admin:P@ssw0rd_123@db.example.com/prod_db",
        "classification": "unsafe"
    },
    {
        "classify_input": "The MongoDB connection string is mongodb+srv://myuser:myPassword@cluster0.mongodb.net/test",
        "classification": "unsafe"
    },
    # Unsafe: Private Keys
    {
        "classify_input": "-----BEGIN RSA PRIVATE KEY-----\nMIIE... (rest of the key) ...-----END RSA PRIVATE KEY-----",
        "classification": "unsafe"
    },
    {
        "classify_input": "-----BEGIN PGP PRIVATE KEY BLOCK-----\n...key data...\n-----END PGP PRIVATE KEY BLOCK-----",
        "classification": "unsafe"
    },
    # Unsafe: PII (Personally Identifiable Information)
    {
        "classify_input": "My credit card number is 4111-1111-1111-1111.",
        "classification": "unsafe"
    },
    {
        "classify_input": "My SSN is 123-45-6789.",
        "classification": "unsafe"
    },
    {
        "classify_input": "Please use my Amex: 3782 822463 10005.",
        "classification": "unsafe"
    },
    {
        "classify_input": "My full card details are Visa 4916123456789012, expiry 12/25, CVV 123.",
        "classification": "unsafe"
    },
    # Unsafe: Hardcoded secrets in code
    {
        "classify_input": "config['password'] = 's3cr3t_p4ss'",
        "classification": "unsafe"
    },
    {
        "classify_input": "const API_KEY = \"a1b2c3d4-e5f6-g7h8-i9j0-k1l2m3n4o5p6\";",
        "classification": "unsafe"
    },
    {
        "classify_input": "define('AUTH_SALT', '`+>b~U+c2N%gP_b|p(y^+JGBR(q@f`f_a_`H@Vb`j~+g`_e`H@Vb`j~+g');",
        "classification": "unsafe"
    },
    {
        "classify_input": "let secret = 'my-jwt-secret';",
        "classification": "unsafe"
    },
    {
        "classify_input": "private static final String SECRET_KEY = \"my_legacy_secret_key\";",
        "classification": "unsafe"
    },
    # Unsafe: More variations
    {
        "classify_input": "user: admin, pass: root",
        "classification": "unsafe"
    },
    {
        "classify_input": "The credentials for the test account are test_user:p4ssw0rd.",
        "classification": "unsafe"
    },
    {
        "classify_input": "Connect with this API key: 9876543210fedcba9876543210fedcba.",
        "classification": "unsafe"
    },
    {
        "classify_input": "Here's a temporary access token: temp_token_abcdef123456.",
        "classification": "unsafe"
    },
    {
        "classify_input": "For the Google Maps API, use key AIzaSyA... (full key here).",
        "classification": "unsafe"
    },
    {
        "classify_input": "The webhook secret is whsec_abcdef1234567890.",
        "classification": "unsafe"
    },
    {
        "classify_input": "My Twitter API secret is TwiTtErSeCrEtKeY12345.",
        "classification": "unsafe"
    },
    {
        "classify_input": "Here's the JWT for auth: eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
        "classification": "unsafe"
    },
    {
        "classify_input": "I set up a new account. It's 'newbie' and the pass is 'newbiepass'.",
        "classification": "unsafe"
    },
    {
        "classify_input": "My email is bob@work.com and the password is mydog'snameFido",
        "classification": "unsafe"
    },
    # Safe: General Conversation & Benign Keywords
    {
        "classify_input": "Hello, how are you today?",
        "classification": "safe"
    },
    {
        "classify_input": "Can you help me debug this Python script? It's a simple bubble sort algorithm.",
        "classification": "safe"
    },
    {
        "classify_input": "What's the best way to handle file uploads in Flask?",
        "classification": "safe"
    },
    {
        "classify_input": "The key to a good API is consistent design.",
        "classification": "safe"
    },
    {
        "classify_input": "I'm getting a 'permission denied' error, but I'm not sure why.",
        "classification": "safe"
    },
    {
        "classify_input": "The user interface needs to be more intuitive.",
        "classification": "safe"
    },
    {
        "classify_input": "This code block calculates the factorial of a number.",
        "classification": "safe"
    },
    {
        "classify_input": "I need to write a function that takes a username and validates it against a regex.",
        "classification": "safe"
    },
    {
        "classify_input": "The secret to making good bread is patience.",
        "classification": "safe"
    },
    {
        "classify_input": "I need a token to play this arcade game.",
        "classification": "safe"
    },
    {
        "classify_input": "The main key in this dictionary is 'data'.",
        "classification": "safe"
    },
    {
        "classify_input": "This document requires a password to open.",
        "classification": "safe"
    },
    {
        "classify_input": "The user needs to be authenticated.",
        "classification": "safe"
    },
    {
        "classify_input": "This is a base64 encoded string of 'hello world': aGVsbG8gd29ybGQ=",
        "classification": "safe"
    },
    {
        "classify_input": "My user ID is 12345.",
        "classification": "safe"
    },
    {
        "classify_input": "The key signature for this piece of music is C Major.",
        "classification": "safe"
    },
    {
        "classify_input": "The password for the puzzle is 'knowledge'.",
        "classification": "safe"
    },
    {
        "classify_input": "The function is called `get_user_password_hash()`.",
        "classification": "safe"
    },
    {
        "classify_input": "The database schema has a 'password_hash' column.",
        "classification": "safe"
    },
    {
        "classify_input": "The security token grants access to the event.",
        "classification": "safe"
    },
    {
        "classify_input": "The user's name is Robert'); DROP TABLE Students;--",
        "classification": "safe"
    },
    {
        "classify_input": "My username is 'test-user', can you check my account status?",
        "classification": "safe"
    },
    {
        "classify_input": "The API key format is usually a long alphanumeric string.",
        "classification": "safe"
    },
    {
        "classify_input": "You need to provide a username and password to log in.",
        "classification": "safe"
    },
    {
        "classify_input": "The variable `password` should be handled with care.",
        "classification": "safe"
    },
    # Safe: Redacted or Abstracted Secrets
    {
        "classify_input": "My password is '**********'.",
        "classification": "safe"
    },
    {
        "classify_input": "The API key is sk-....-xxxx.",
        "classification": "safe"
    },
    {
        "classify_input": "Please use the credentials: user='testuser', password='[REDACTED]'.",
        "classification": "safe"
    },
    {
        "classify_input": "The DB connection string is postgresql://user:[PASSWORD]@host:5432/db.",
        "classification": "safe"
    },
    {
        "classify_input": "My credit card ends in 1234.",
        "classification": "safe"
    },
    {
        "classify_input": "The token is `ghp_...`.",
        "classification": "safe"
    },
    {
        "classify_input": "I've reset your password. It is now `--omitted--`.",
        "classification": "safe"
    },
    {
        "classify_input": "The secret is stored in an environment variable, not here.",
        "classification": "safe"
    },
    {
        "classify_input": "My username is 'admin', but I can't share the password.",
        "classification": "safe"
    },
    {
        "classify_input": "The AWS secret key is set to '***'.",
        "classification": "safe"
    },
    {
        "classify_input": "My SSN is XXX-XX-1234.",
        "classification": "safe"
    },
    {
        "classify_input": "The client secret is `<SECRET_HIDDEN>`.",
        "classification": "safe"
    },
    {
        "classify_input": "The password for the wifi is written on the board.",
        "classification": "safe"
    },
    {
        "classify_input": "I've put the API key in the `.env` file for security.",
        "classification": "safe"
    },
    {
        "classify_input": "The user is 'test' and the password is 'test'.",
        "classification": "safe"
    },
    {
        "classify_input": "The default password is 'password', you should change it immediately.",
        "classification": "safe"
    },
    {
        "classify_input": "The key is `pk_test_...` which is a test key and not sensitive.",
        "classification": "safe"
    },
    {
        "classify_input": "The user is 'john.doe' and his password has been sent to him via a secure channel.",
        "classification": "safe"
    },
    {
        "classify_input": "The API key is loaded from `os.environ.get('API_KEY')`.",
        "classification": "safe"
    },
    {
        "classify_input": "This is a private key, but it's an example from a textbook: `-----BEGIN EXAMPLE PRIVATE KEY-----`",
        "classification": "safe"
    },
    {
        "classify_input": "The user's password must be at least 8 characters long.",
        "classification": "safe"
    },
    {
        "classify_input": "The API requires a key for authentication.",
        "classification": "safe"
    },
    {
        "classify_input": "My user account is locked.",
        "classification": "safe"
    },
    {
        "classify_input": "The classification of this text is 'safe'.",
        "classification": "safe"
    },
    {
        "classify_input": "The secret code to enter the clubhouse is 'friend'.",
        "classification": "safe"
    },
]

# ---- end train-set from codegiant -----

# ---- start test-set from codegiant -----

examples_for_classification_test_set_giant: List[Dict[str, str]] = [
    # Unsafe: User/Password variations
    {
        "classify_input": "login: myuser / mypass123",
        "classification": "unsafe"
    },
    {
        "classify_input": "The credentials are: user='app_user', pass='S3cureP@ssw0rd!'",
        "classification": "unsafe"
    },
    {
        "classify_input": "For the test environment, the user is 'tester' and the password is 'password'.",
        "classification": "unsafe"
    },
    {
        "classify_input": "My wifi password is 'LiveLaughLove2024'.",
        "classification": "unsafe"
    },
    {
        "classify_input": "The root password for the server is 'r00t_p@ssw0rd'.",
        "classification": "unsafe"
    },
    {
        "classify_input": "Use this for the demo: demo_user / Demo12345",
        "classification": "unsafe"
    },
    {
        "classify_input": "The password for the zip file is 'secret'.",
        "classification": "unsafe"
    },
    {
        "classify_input": "My email is jane.d@email.com and my password is hercat'snameWhiskers",
        "classification": "unsafe"
    },
    {
        "classify_input": "The admin account is 'administrator' with password 'adminpass'.",
        "classification": "unsafe"
    },
    {
        "classify_input": "Here's the login for the production database: prod_user / Pr0d!P@ssw0rd",
        "classification": "unsafe"
    },
    # Unsafe: API Keys/Tokens variations
    {
        "classify_input": "The SendGrid API Key is SG.xxxxxxxx.yyyyyyyyyyyyyyyy.",
        "classification": "unsafe"
    },
    {
        "classify_input": "Here's the auth token: 'Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b'",
        "classification": "unsafe"
    },
    {
        "classify_input": "My Twilio Account SID is ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx and Auth Token is yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy.",
        "classification": "unsafe"
    },
    {
        "classify_input": "The private key for the service account is: '-----BEGIN PRIVATE KEY-----\n...key data...\n-----END PRIVATE KEY-----'",
        "classification": "unsafe"
    },
    {
        "classify_input": "The Mapbox access token is pk.eyJ1IjoibXl1c2VybmFtZSI.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.",
        "classification": "unsafe"
    },
    {
        "classify_input": "The client_secret for the OAuth flow is 'a1b2c3d4e5f6g7h8i9j0'.",
        "classification": "unsafe"
    },
    {
        "classify_input": "The webhook signing secret is `whsec_aBcDeFgHiJkLmNoPqRsTuVwXyZ`",
        "classification": "unsafe"
    },
    {
        "classify_input": "My AWS_ACCESS_KEY_ID is AKIADEADBEEF... and my AWS_SECRET_ACCESS_KEY is 1234567890...",
        "classification": "unsafe"
    },
    {
        "classify_input": "The bearer token for the API is: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJPbmxpbmUgSldUIEJ1aWxkZXIiLCJpYXQiOjE2MTYyMzkwMjIsImV4cCI6MTY0NzcyNjYyMiwiYXVkIjoid3d3LmV4YW1wbGUuY29tIiwic3ViIjoianJvY2tldEBleGFtcGxlLmNvbSIsIkdpdmVuTmFtZSI6IkpvaG5ueSIsIlN1cm5hbWUiOiJSb2NrZXQiLCJFbWFpbCI6Impyb2NrZXRAZXhhbXBsZS5jb20iLCJSb2xlIjpbIk1hbmFnZXIiLCJQcm9qZWN0IEFkbWluaXN0cmF0b3IiXX0.7_I-3tC-g_t_I-3tC-g_t_I-3tC-g_t_I-3tC-g_t_I",
        "classification": "unsafe"
    },
    {
        "classify_input": "The secret key for the application is 'django-insecure-!@#$%^&*()'.",
        "classification": "unsafe"
    },
    # Unsafe: Connection Strings/PII/Keys variations
    {
        "classify_input": "My card is a Mastercard: 5412 7512 3412 3456, expires 06/24, CVV 456.",
        "classification": "unsafe"
    },
    {
        "classify_input": "The database connection is: 'mongodb://user:pass@host:port/db'",
        "classification": "unsafe"
    },
    {
        "classify_input": "My SSN is 987-65-4321, please don't share it.",
        "classification": "unsafe"
    },
    {
        "classify_input": "Here is the Redis connection URL: redis://:p@ssw0rd@redis-12345.c1.us-east-1-2.ec2.cloud.redislabs.com:12345",
        "classification": "unsafe"
    },
    {
        "classify_input": "-----BEGIN OPENSSH PRIVATE KEY-----\n...key data...\n-----END OPENSSH PRIVATE KEY-----",
        "classification": "unsafe"
    },
    {
        "classify_input": "My Visa number is 4111222233334444.",
        "classification": "unsafe"
    },
    {
        "classify_input": "The connection string for SQL Server is 'Server=myServerAddress;Database=myDataBase;User Id=myUsername;Password=myPassword;'",
        "classification": "unsafe"
    },
    {
        "classify_input": "My Amex card number is 3412 345678 91011.",
        "classification": "unsafe"
    },
    {
        "classify_input": "The authorization header is 'Basic dXNlcjpwYXNz'.",
        "classification": "unsafe"
    },
    {
        "classify_input": "The credentials for the API are client_id: 'my_client_id', client_secret: 'my_client_secret'.",
        "classification": "unsafe"
    },
    # Unsafe: More variations
    {
        "classify_input": "I'm locked out. My user is 'm_smith' and my password is 'Summer2023!'.",
        "classification": "unsafe"
    },
    {
        "classify_input": "The user is 'service_account' and the password is 'SvcAccP@ss1'.",
        "classification": "unsafe"
    },
    {
        "classify_input": "My username is 'julie7' and my password is 'julie123'.",
        "classification": "unsafe"
    },
    {
        "classify_input": "The default login for the device is user: 'support', pass: 'support01'.",
        "classification": "unsafe"
    },
    {
        "classify_input": "Here is the API key for the weather service: 11223344556677889900aabbccddeeff.",
        "classification": "unsafe"
    },
    {
        "classify_input": "The secret for the JWT is 'this-is-a-very-secret-key-that-should-not-be-in-code'.",
        "classification": "unsafe"
    },
    {
        "classify_input": "My GitHub token is ghp_abc123def456... (full token).",
        "classification": "unsafe"
    },
    {
        "classify_input": "The API key is defined in the code: const API_KEY = 'my-secret-api-key';",
        "classification": "unsafe"
    },
    {
        "classify_input": "The Slack token is xoxp-12345-67890-abcde-fghij.",
        "classification": "unsafe"
    },
    {
        "classify_input": "The JWT is eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6InRlc3QiLCJpYXQiOjE2MTYyMzkwMjJ9.4-Sz_I3o-Qo_I3o-Qo_I3o-Qo_I3o-Qo_I3o-Qo",
        "classification": "unsafe"
    },
    # Safe: General Conversation & Benign Keywords variations
    {
        "classify_input": "I think I found a bug in the password reset flow.",
        "classification": "safe"
    },
    {
        "classify_input": "This is a public API key, so it's safe to share: 'public_key_123'.",
        "classification": "safe"
    },
    {
        "classify_input": "How do I hash a password securely in PHP?",
        "classification": "safe"
    },
    {
        "classify_input": "The key insight here is that the algorithm is O(n log n).",
        "classification": "safe"
    },
    {
        "classify_input": "Let's talk about the new security policy.",
        "classification": "safe"
    },
    {
        "classify_input": "The user 'anonymous' has read-only access.",
        "classification": "safe"
    },
    {
        "classify_input": "The classification of this document is 'confidential'.",
        "classification": "safe"
    },
    {
        "classify_input": "I need a key to open this chest in the game.",
        "classification": "safe"
    },
    {
        "classify_input": "The secret to their success is a great team.",
        "classification": "safe"
    },
    {
        "classify_input": "The function `create_user` takes username and password as arguments.",
        "classification": "safe"
    },
    {
        "classify_input": "The database table 'users' has columns: 'id', 'username', 'email', 'password_hash'.",
        "classification": "safe"
    },
    {
        "classify_input": "The access control list (ACL) is misconfigured.",
        "classification": "safe"
    },
    {
        "classify_input": "The user's session token has expired.",
        "classification": "safe"
    },
    {
        "classify_input": "The primary key for the 'users' table is 'id'.",
        "classification": "safe"
    },
    {
        "classify_input": "This is a private repository.",
        "classification": "safe"
    },
    {
        "classify_input": "The secret ingredient in the sauce is a pinch of cinnamon.",
        "classification": "safe"
    },
    {
        "classify_input": "The user's password must meet the complexity requirements.",
        "classification": "safe"
    },
    {
        "classify_input": "The word 'password' appears 5 times in this document.",
        "classification": "safe"
    },
    {
        "classify_input": "My user ID is 54321.",
        "classification": "safe"
    },
    {
        "classify_input": "The key of the song is A minor.",
        "classification": "safe"
    },
    {
        "classify_input": "The password to the speakeasy is 'swordfish'.",
        "classification": "safe"
    },
    {
        "classify_input": "The function is named `check_password`.",
        "classification": "safe"
    },
    {
        "classify_input": "The database has a 'secrets' table, but access is restricted.",
        "classification": "safe"
    },
    {
        "classify_input": "The secret of the universe is 42.",
        "classification": "safe"
    },
    {
        "classify_input": "The security token is a physical device you plug into your USB port.",
        "classification": "safe"
    },
    # Safe: Redacted or Abstracted Secrets variations
    {
        "classify_input": "Hello, here is my user 'cgint' and password: --omitted--",
        "classification": "safe"
    },
    {
        "classify_input": "The API key is stored in `process.env.API_KEY`.",
        "classification": "safe"
    },
    {
        "classify_input": "My password is a secret, I can't tell you.",
        "classification": "safe"
    },
    {
        "classify_input": "The token starts with `xoxb-` but the rest is redacted.",
        "classification": "safe"
    },
    {
        "classify_input": "The DB password is in the vault.",
        "classification": "safe"
    },
    {
        "classify_input": "My credit card is a Visa ending in 4321.",
        "classification": "safe"
    },
    {
        "classify_input": "The user is 'admin' and the password is `********`.",
        "classification": "safe"
    },
    {
        "classify_input": "The secret key is `<REDACTED_FOR_SECURITY>`.",
        "classification": "safe"
    },
    {
        "classify_input": "I've shared the credentials with you via 1Password.",
        "classification": "safe"
    },
    {
        "classify_input": "The connection string is `mysql://user:****@host/db`.",
        "classification": "safe"
    },
    {
        "classify_input": "My SSN is `XXX-XX-XXXX`.",
        "classification": "safe"
    },
    {
        "classify_input": "The private key is encrypted on disk.",
        "classification": "safe"
    },
    {
        "classify_input": "You can find the API key in the environment variables.",
        "classification": "safe"
    },
    {
        "classify_input": "The password is not 'password123', I'm not that silly.",
        "classification": "safe"
    },
    {
        "classify_input": "The default password is 'admin', which you must change on first login.",
        "classification": "safe"
    },
    {
        "classify_input": "The key is a test key `pk_test_...` and is not a secret.",
        "classification": "safe"
    },
    {
        "classify_input": "The user's password has been securely hashed and stored.",
        "classification": "safe"
    },
    {
        "classify_input": "The API key is `sk-....` with the middle part removed.",
        "classification": "safe"
    },
    {
        "classify_input": "The credentials are managed by a secrets manager.",
        "classification": "safe"
    },
    {
        "classify_input": "This is a public key, not a private one: `-----BEGIN PUBLIC KEY-----`",
        "classification": "safe"
    },
    {
        "classify_input": "The secret password for the club is 'Fidelio'.",
        "classification": "safe"
    },
    {
        "classify_input": "The user's password is not stored in plaintext.",
        "classification": "safe"
    },
    {
        "classify_input": "The API requires a valid key to be passed in the header.",
        "classification": "safe"
    },
    {
        "classify_input": "My user session has expired.",
        "classification": "safe"
    },
    {
        "classify_input": "The key to open the door is in the flowerpot.",
        "classification": "safe"
    },
]

# ---- end test-set from codegiant -----

# Comprehensive training examples for credentials/passwords classification

# ---- start train-set -----

examples_for_classification_train_set: List[Dict[str, str]] = [
    # Original example
    {
        "classify_input": "Hello, here is my user 'cgint' and password: 12356!",
        "classification": "unsafe"
    },
    
    # === UNSAFE EXAMPLES - Exposed credentials ===
    
    # Basic username/password combinations
    {
        "classify_input": "My login is admin and my password is 123456",
        "classification": "unsafe"
    },
    {
        "classify_input": "Username: root, Password: secret123",
        "classification": "unsafe"
    },
    {
        "classify_input": "Use credentials: user=testuser pass=mypassword",
        "classification": "unsafe"
    },
    
    # API keys and tokens
    {
        "classify_input": "API key: sk-1234567890abcdef",
        "classification": "unsafe"
    },
    {
        "classify_input": "Bearer token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
        "classification": "unsafe"
    },
    {
        "classify_input": "Auth token: abc123def456ghi789",
        "classification": "unsafe"
    },
    
    # Database credentials
    {
        "classify_input": "Database connection: host=localhost user=dbuser password=dbpass123",
        "classification": "unsafe"
    },
    {
        "classify_input": "DB_PASSWORD=mysecretpassword",
        "classification": "unsafe"
    },
    
    # AWS/Cloud credentials
    {
        "classify_input": "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI",
        "classification": "unsafe"
    },
    {
        "classify_input": "Azure connection string: DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey123",
        "classification": "unsafe"
    },
    
    # SSH keys and certificates
    {
        "classify_input": "SSH private key: -----BEGIN RSA PRIVATE KEY----- MIIEpAIBAAKCAQEA...",
        "classification": "unsafe"
    },
    {
        "classify_input": "Certificate: -----BEGIN CERTIFICATE----- MIIC...",
        "classification": "unsafe"
    },
    
    # Email/SMTP credentials
    {
        "classify_input": "SMTP settings: smtp.gmail.com, username: user@gmail.com, password: myemailpass",
        "classification": "unsafe"
    },
    
    # FTP credentials
    {
        "classify_input": "FTP login: ftp://username:password@ftp.example.com",
        "classification": "unsafe"
    },
    
    # Generic secrets
    {
        "classify_input": "Secret key: abc123secretkey456",
        "classification": "unsafe"
    },
    {
        "classify_input": "Encryption key: AES256-key-1234567890abcdef",
        "classification": "unsafe"
    },
    
    # === SAFE EXAMPLES - Redacted or no credentials ===
    
    # Redacted passwords
    {
        "classify_input": "My login is admin and my password is [REDACTED]",
        "classification": "safe"
    },
    {
        "classify_input": "Username: root, Password: ***hidden***",
        "classification": "safe"
    },
    {
        "classify_input": "API key: ••••••••••••••••",
        "classification": "safe"
    },
    {
        "classify_input": "Database password: --omitted--",
        "classification": "safe"
    },
    {
        "classify_input": "Token: <masked>",
        "classification": "safe"
    },
    
    # Instructions about passwords (no actual credentials)
    {
        "classify_input": "Please enter your password to continue",
        "classification": "safe"
    },
    {
        "classify_input": "You need to provide valid credentials",
        "classification": "safe"
    },
    {
        "classify_input": "Password field is required",
        "classification": "safe"
    },
    {
        "classify_input": "Make sure to use a strong password",
        "classification": "safe"
    },
    {
        "classify_input": "Authentication is required to access this resource",
        "classification": "safe"
    },
    
    # Environment variable names (without values)
    {
        "classify_input": "Set the DATABASE_PASSWORD environment variable",
        "classification": "safe"
    },
    {
        "classify_input": "API_KEY should be configured in your environment",
        "classification": "safe"
    },
    
    # Documentation about security
    {
        "classify_input": "Store your API keys securely",
        "classification": "safe"
    },
    {
        "classify_input": "Never commit passwords to version control",
        "classification": "safe"
    },
    {
        "classify_input": "Use environment variables for sensitive data",
        "classification": "safe"
    },
    
    # Generic text without credentials
    {
        "classify_input": "Hello, how are you today?",
        "classification": "safe"
    },
    {
        "classify_input": "The system is running normally",
        "classification": "safe"
    },
    {
        "classify_input": "Processing completed successfully",
        "classification": "safe"
    },
    
    {
        "classify_input": "There might be some sensitive information here",
        "classification": "safe"
    },
    {
        "classify_input": "Check the config file for secrets",
        "classification": "safe"
    },
    {
        "classify_input": "The credentials are stored somewhere",
        "classification": "safe"
    },
    {
        "classify_input": "Contains potentially sensitive data",
        "classification": "safe"
    },
    {
        "classify_input": "Review security settings",
        "classification": "safe"
    },
    {
        "classify_input": "Password: [value not shown]",
        "classification": "safe"
    },
    {
        "classify_input": "Secret data exists but is not visible",
        "classification": "safe"
    },
{
        "classify_input": "My login is admin and my password is 123456",
        "classification": "unsafe"
    },
    {
        "classify_input": "API key: sk-1234567890abcdef",
        "classification": "unsafe"
    },
    {
        "classify_input": "Here's the database connection: username=root password=secret123",
        "classification": "unsafe"
    },
    {
        "classify_input": "JWT token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "classification": "unsafe"
    },
    {
        "classify_input": "AWS credentials: access_key=AKIAIOSFODNN7EXAMPLE secret=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "classification": "unsafe"
    },
    
    # Safe examples - redacted or no credentials
    {
        "classify_input": "My login is admin and my password is [REDACTED]",
        "classification": "safe"
    },
    {
        "classify_input": "API key: ***hidden***",
        "classification": "safe"
    },
    {
        "classify_input": "Please enter your password to continue",
        "classification": "safe"
    },
    {
        "classify_input": "The user needs to authenticate with their credentials",
        "classification": "safe"
    },
    {
        "classify_input": "Password field is required",
        "classification": "safe"
    },
    
    {
        "classify_input": "Something might be a secret but it's not clear",
        "classification": "safe"
    },
    {
        "classify_input": "The configuration contains sensitive data",
        "classification": "safe"
    }
]

# ---- end train-set -----

# ---- start test-set -----

examples_for_classification_test_set: List[Dict[str, str]] = [
    # Original test example
    {
        "classify_input": "Hello, here is my user 'cgint' and password: --omitted--",
        "classification": "safe"
    },
    
    # Additional test cases
    {
        "classify_input": "API secret: sk-live-1234567890abcdef",
        "classification": "unsafe"
    },
    {
        "classify_input": "Login with username=admin password=********",
        "classification": "safe"
    },
    {
        "classify_input": "The password might be compromised",
        "classification": "safe"
    },
    {
        "classify_input": "OAuth token: ya29.A0ARrdaM-example-token",
        "classification": "unsafe"
    },
    {
        "classify_input": "Please configure your API credentials",
        "classification": "safe"
    },
    {
        "classify_input": "Connection string contains sensitive info",
        "classification": "safe"
    },
    {
        "classify_input": "GitHub token: ghp_example123456789",
        "classification": "unsafe"
    },
    {
        "classify_input": "Remember to rotate your keys regularly",
        "classification": "safe"
    },
    {
        "classify_input": "The secret key is: [PROTECTED]",
        "classification": "safe"
    }
]

# ---- end test-set -----

text_prefix = "Hello sir, nice to hear from you again. I'm sending you the request of the issue i am having. "
text_postfix = "Thank you for your help. I'm looking forward to your response. "

def prepare_training_data(limit: int = 10000, randomize: bool = False) -> List[dspy.Example]:
    """Convert examples to DSPy format"""
    examples: List[dspy.Example] = []
    question_seen: Set[str] = set()
    
    # Add your existing examples
    combined_train_set = examples_for_classification_train_set + examples_for_classification_train_set_giant
    if randomize:
        random.shuffle(combined_train_set.copy())
    for i, ex in enumerate(combined_train_set):
        if i*2 >= limit:
            break
        if ex["classify_input"] in question_seen:
            continue
        question_seen.add(ex["classify_input"])
        examples.append(dspy.Example(
            classify_input=ex["classify_input"],
            classification=ex["classification"]
        ).with_inputs("classify_input"))
        examples.append(dspy.Example(
            classify_input=text_prefix + ex["classify_input"] + text_postfix,
            classification=ex["classification"]
        ).with_inputs("classify_input"))
    
    return examples

def prepare_test_data(limit: int = 10000, randomize: bool = False) -> List[dspy.Example]:
    """Convert test examples to DSPy format"""
    examples: List[dspy.Example] = []
    question_seen: Set[str] = set()
    
    # Add your existing examples
    combined_test_set = examples_for_classification_test_set + examples_for_classification_test_set_giant
    if randomize:
        random.shuffle(combined_test_set.copy())
    for i, ex in enumerate(combined_test_set):
        if i*2 >= limit:
            break
        if ex["classify_input"] in question_seen:
            continue
        question_seen.add(ex["classify_input"])
        examples.append(dspy.Example(
            classify_input=ex["classify_input"],
            classification=ex["classification"]
        ).with_inputs("classify_input"))
        examples.append(dspy.Example(
            classify_input=text_prefix + ex["classify_input"] + text_postfix,
            classification=ex["classification"]
        ).with_inputs("classify_input"))
    return examples

```

## File: `dspy_agent_classifier_credentials_passwords_optimized.py`
```
#!/usr/bin/env python3
# /// script
# dependencies = [
#     "dspy-ai",
#     "mlflow"
# ]
# requires-python = ">=3.11"
# ///

from typing import Any, Literal, Optional, Union, Dict
from datetime import datetime
import time
import dspy
from dspy.teleprompt.gepa.gepa import GEPAFeedbackMetric
from dspy.teleprompt.gepa.gepa_utils import ScoreWithFeedback
import mlflow
from dspy_agent_classifier_credentials_passwords_examples import (
    prepare_training_data,
    prepare_test_data
)
from dspy_agent_classifier_credentials_passwords import ClassifierCredentialsPasswords, classifier_lm, classifier_lm_model_name, classifier_lm_reasoning_effort
from dspy_constants import MODEL_NAME_GEMINI_2_5_FLASH

mlflow.set_experiment("dspy_agent_classifier_credentials_passwords_optimized")
mlflow.autolog()

# --- Metric for Optimization ---

def classification_accuracy(example: dspy.Example, pred: dspy.Prediction, trace=None) -> float:
    """
    Metric function for MIPROv2 optimization.
    Returns 1.0 for correct classification, 0.0 for incorrect.
    """
    return float(example.classification == pred.classification)



class ClassificationAccuracyWithFeedbackMetric(GEPAFeedbackMetric):
	def __call__(
		self,
		gold: dspy.Example,
		pred: dspy.Prediction,
		trace: Any = None,
		pred_name: Optional[str] = None,
		pred_trace: Any = None,
	) -> Union[float, ScoreWithFeedback]:
		answer_is_same = classification_accuracy(gold, pred)
		total = answer_is_same
		if pred_name is None:
			return total
		if not answer_is_same:
			feedback = "The classifier is not working as expected. Please check the classifier module."
		else:
			feedback = "The classifier is working as expected."
		return ScoreWithFeedback(score=total, feedback=feedback)


# --- Data Preparation ---

# --- MIPROv2 Optimization ---

def to_percent_int(input: Any) -> int:
    if isinstance(input, float):
        return int(input)
    else:
        raise ValueError(f"Cannot convert {input} to float. Type: {type(input)}")

def optimize_classifier(optimizer_type: Literal["MIPROv2", "GEPA"], trainer_lm: dspy.LM, auto: Literal["light", "medium", "heavy"], limit_trainset: int, limit_testset: int, randomize_sets: bool, reflection_minibatch_size: int):
    """
    Optimize the classifier using DSPy MIPROv2
    """
    
    print(f"🚀 Starting MIPROv2 optimization with parameters: optimizer_type={optimizer_type}, trainer_lm={trainer_lm.model}, auto={auto}")
    
    # Prepare data
    trainset = prepare_training_data(limit=limit_trainset, randomize=randomize_sets)
    testset = prepare_test_data(limit=limit_testset, randomize=randomize_sets)
    
    print(f"Training set size: {len(trainset)}")
    print(f"Test set size: {len(testset)}")
    
    # Test baseline performance
    print("\n📊 Baseline Performance:")
    baseline_score = dspy.Evaluate(
        devset=testset, 
        metric=classification_accuracy,
        num_threads=4,
        display_progress=True
    )(ClassifierCredentialsPasswords())
    print(f"Baseline accuracy: {to_percent_int(baseline_score.score)}%")
    
    # Initialize MIPROv2 optimizer
    # Using "light" for fast optimization, can try "medium" or "heavy" for better results
    print("\n🔧 Running MIPROv2 optimization...")
    print("This may take a few minutes...")
    
    if optimizer_type == "MIPROv2":
        optimizer = dspy.MIPROv2(
            metric=classification_accuracy,
            auto=auto,  # Options: "light", "medium", "heavy"
            num_threads=4,
            max_bootstrapped_demos=0,
            max_labeled_demos=0,
            prompt_model=trainer_lm
        )
    elif optimizer_type == "GEPA":
        optimizer = dspy.GEPA(
            metric=ClassificationAccuracyWithFeedbackMetric(),
            auto=auto,
            num_threads=4,
            track_stats=True,
            skip_perfect_score=True,
            add_format_failure_as_feedback=True,
            reflection_minibatch_size=reflection_minibatch_size,
            reflection_lm=trainer_lm
        )
    
    # Compile/optimize the classifier
    optimized_classifier = optimizer.compile(
        ClassifierCredentialsPasswords(),
        trainset=trainset,
        valset=testset
    )
    
    # Test optimized performance
    print("\n🎯 Optimized Performance:")
    optimized_score = dspy.Evaluate(
        devset=testset,
        metric=classification_accuracy,
        num_threads=4,
        display_progress=True
    )(optimized_classifier)
    
    baseline_score_int = to_percent_int(baseline_score.score)
    optimized_score_int = to_percent_int(optimized_score.score)
    print("\n📈 Results:")
    print(f"Baseline accuracy:  {baseline_score_int}%")
    print(f"Optimized accuracy: {optimized_score_int}%")

    save_path = f"optimized_credentials_classifier_{int(time.time())}_{baseline_score_int}_to_{optimized_score_int}.json"
    optimized_classifier.save(save_path)
    print(f"\n💾 Optimized classifier saved to: {save_path}")
    
    return optimized_classifier, save_path, baseline_score_int, optimized_score_int


def test_classifier_examples(classifier, examples_desc="", question_prefix="") -> Dict[str, str]:
    """Test the classifier with some example inputs"""
    print(f"\n🧪 Testing {examples_desc}:")
    
    test_inputs = [
        "My username is john and password is secret123",
        "API token: sk-abc123def456",
        "Please enter your password: [REDACTED]",
        "The user needs to provide valid credentials",
        "Database password: ***hidden***"
    ]
    
    results = {}
    for test_input in test_inputs:
        result = classifier(classify_input=test_input)
        results[test_input] = result.classification
        print(f"Input: {test_input}")
        print(f"Classification: {result.classification}")
        if hasattr(result, 'reasoning'):
            print(f"Reasoning: {result.reasoning}")
        print("-" * 50)
    return results


# --- Example Usage ---

def log_as_table(results: Dict[str, str], optimization_type: Literal["baseline", "optimized"]) -> None:
    """
    Log test results as a structured table to MLflow.
    
    Args:
        results: Dictionary mapping test inputs to classification results
        optimization_type: Type of model ("baseline" or "optimized")
    """
    # Parse the results dictionary to extract questions and answers
    table_data = {
        "test_number": [],
        "question": [],
        "answer": [],
        "optimization_type": []
    }
    
    for i, (question_with_prefix, answer) in enumerate(results.items(), 1):
        # Remove the model type prefix from the question
        if question_with_prefix.startswith(f"{optimization_type}_"):
            question = question_with_prefix[len(f"{optimization_type}_"):]
        else:
            question = question_with_prefix
            
        table_data["test_number"].append(i)
        table_data["question"].append(question)
        table_data["answer"].append(answer)
        table_data["optimization_type"].append(optimization_type)
    
    # Log the table to MLflow
    artifact_file = f"{optimization_type}_test_results.json"
    mlflow.log_table(data=table_data, artifact_file=artifact_file)
    print(f"✅ {optimization_type.title()} test results logged to MLflow as table: {artifact_file}")


if __name__ == "__main__":
    try:
        dspy.settings.configure(lm=classifier_lm, track_usage=True, provide_traceback=True)
        dspy.configure_cache(
            enable_disk_cache=False,
            enable_memory_cache=False,
            enable_litellm_cache=False
        )
        print(f"✅ DSPy configured to use {dspy.settings.lm.model}.")
    except Exception as e:
        print(f"❌ Error configuring DSPy: {e}")
        exit(1)
    
    formatter_date_now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    with mlflow.start_run(run_name=f"pwd_classifier_{formatter_date_now}"):
        
        # Optimize classifier with
        trainer_lm_model_name = MODEL_NAME_GEMINI_2_5_FLASH
        trainer_lm_reasoning_effort = "disable"
        optimizer_type = "GEPA" # "MIPROv2" # "GEPA"
        auto = "light"  # <-- We will use a light budget for this tutorial. However, we typically recommend using auto="heavy" for optimized performance!
        limit_trainset = 50
        limit_testset = 30
        randomize_sets = True
        reflection_minibatch_size = limit_testset # Used in GEPA only - when too low then it can loop on seemingly perfect proposed candidates

        mlflow.log_param("classifier_lm_model", classifier_lm_model_name)
        mlflow.log_param("classifier_lm_reasoning_effort", classifier_lm_reasoning_effort)
        mlflow.log_param("trainer_lm_model", trainer_lm_model_name)
        mlflow.log_param("trainer_lm_reasoning_effort", trainer_lm_reasoning_effort)
        mlflow.log_param("optimizer_type", optimizer_type)
        mlflow.log_param("auto", auto)
        mlflow.log_param("limit_trainset", limit_trainset)
        mlflow.log_param("limit_testset", limit_testset)
        mlflow.log_param("randomize_sets", randomize_sets)
        mlflow.log_param("reflection_minibatch_size", reflection_minibatch_size)

        # Test baseline classifier
        baseline_classifier = ClassifierCredentialsPasswords()
        baseline_results = test_classifier_examples(baseline_classifier, "Baseline Classifier")
        log_as_table(baseline_results, optimization_type="baseline")

        trainer_lm = dspy.LM(
            model=f'vertex_ai/{trainer_lm_model_name}',
            reasoning_effort=trainer_lm_reasoning_effort # other options are Literal["low", "medium", "high"]
            # thinking={"type": "enabled", "budget_tokens": 512}
        )

        optimizer_start_time_sec = time.time()
        optimized_classifier, save_path, baseline_score_int, optimized_score_int = optimize_classifier(optimizer_type, trainer_lm, auto, limit_trainset, limit_testset, randomize_sets, reflection_minibatch_size)
        optimizer_end_time_sec = time.time()
        optimizer_duration_sec = optimizer_end_time_sec - optimizer_start_time_sec
        mlflow.log_metric("optimizer_duration_seconds", optimizer_duration_sec)
        
        # Test optimized classifier
        optimized_results = test_classifier_examples(optimized_classifier, "Optimized Classifier")
        log_as_table(optimized_results, optimization_type="optimized")

        mlflow.log_metric("baseline_accuracy", baseline_score_int)
        mlflow.log_metric("optimized_accuracy", optimized_score_int)
    
    print(f"\n🎉 Optimization complete! Optimized model saved to: {save_path}")
    print(f"Baseline accuracy: {baseline_score_int}%")
    print(f"Optimized accuracy: {optimized_score_int}%")```

## File: `dspy_agent_classifier_credentials_passwords.py`
```
#!/usr/bin/env python3
# /// script
# dependencies = [
#     "dspy-ai",
#     "mlflow"
# ]
# requires-python = ">=3.11"
# ///

import dspy
import os
from typing import Literal

import mlflow
from dspy_constants import MODEL_NAME_GEMINI_2_5_FLASH_LITE
# mlflow.set_experiment("dspy_agent_classifier_credentials_passwords")
# mlflow.autolog()


# --- Main DSPy Agent ---

class ClassifierCredentialsPasswordsSignature(dspy.Signature):
    """Classify text to detect if it contains exposed credentials or passwords."""
    classify_input: str = dspy.InputField(
        desc="Text input to analyze for potential credential or password exposure"
    )
    classification: Literal["safe", "unsafe"] = dspy.OutputField(
        desc="Classification result: 'unsafe' if credentials/passwords are exposed, 'safe' if no credentials/passwords or properly protected/redacted"
    )

# --- Example Usage ---
# Make sure that VERTEXAI_PROJECT=smec-whoop-dev and VERTEXAI_LOCATION=europe-west1 are set as environment variables
if not os.getenv("VERTEXAI_PROJECT") or not os.getenv("VERTEXAI_LOCATION"):
    raise ValueError("VERTEXAI_PROJECT and VERTEXAI_LOCATION must be set as environment variables")

classifier_lm_model_name = MODEL_NAME_GEMINI_2_5_FLASH_LITE
classifier_lm_reasoning_effort = "disable"
classifier_lm = dspy.LM(
    model='ollama/gemma3:270m',
    # model=f'vertex_ai/{classifier_lm_model_name}',
    # reasoning_effort=classifier_lm_reasoning_effort # other options are Literal["low", "medium", "high"]
    # thinking={"type": "enabled", "budget_tokens": 512}
)

class ClassifierCredentialsPasswords(dspy.Module):
    def __init__(self, lm: dspy.LM = classifier_lm):
        super().__init__()
        self.classifier = dspy.Predict(ClassifierCredentialsPasswordsSignature)
        self.classifier_lm = lm

    def forward(self, classify_input: str) -> dspy.Prediction:
        with dspy.context(lm=self.classifier_lm, track_usage=True):
            return self.classifier(classify_input=classify_input)


if __name__ == "__main__":
    try:
        dspy.settings.configure(
            lm=classifier_lm, track_usage=True
        )
        dspy.configure_cache(
            enable_disk_cache=False,
            enable_memory_cache=False,
            enable_litellm_cache=False
        )
        print(f"DSPy configured to use {dspy.settings.lm.model}.")
    except Exception as e:
        print(f"Error configuring DSPy: {e}")
        exit(1)


    with mlflow.start_run():
        classifier = ClassifierCredentialsPasswords()
        input_text = "My username is john and password is secret123"
        result = classifier(classify_input=input_text)
        print(f"Input text: {input_text}")
        print(f"Classification: {result.classification}")
        print(result)```

## File: `dspy_agent_expert_ai.py`
```
import dspy
from typing import List, Any
from pydantic import BaseModel

# --- Response Model ---

class QuestionAnswerResponse(BaseModel):
    """Response object containing question, history, metadata, and final answer."""
    question: str
    history: dict[str, Any]  # Will contain dspy.History serialized data
    tracked_usage_metadata: dict[str, Any]
    final_answer: str

# --- Main DSPy Agent ---

class AgentCodingAssistantSignature(dspy.Signature):
    """
    You are an Agent Coding Assistant AI. Answer the user's question by retrieving information from the internal knowledge base or web search.

    IMPORTANT: Use the tools in this STRICT priority order. Only proceed to the next tool if the previous tool's response is insufficient to answer the user's question:

    1. FIRST: For simple questions that don't require specialized knowledge or the information to answer the question is already in the history,
       you may answer directly without using tools.

    2. SECOND: Use InternalKnowledgeAgent from chat history if it was already requested by search term once during the conversation!
       - Do not fetch the internal knowledge base with the very same search term again within the same conversation.

    3. THIRD: Use InternalKnowledgeAgent - Retrieves information from the internal knowledge base.
       - If this provides a complete answer, use it and do NOT call other tools.
       - Only proceed to step 4 if the internal knowledge is insufficient or unavailable.

    4. FOURTH: If needed, use WebSearchAgent - Retrieves information from web search with native Google Search grounding.
       - Only use this if InternalKnowledgeAgent didn't provide sufficient information.
       - In case the user wants you to specifically search within our internal knowledge base, then do not use the WebSearchAgent.

    """
    # NOTE: If the user asks about conversation history and the history field contains previous messages, provide a summary based on that information. Do NOT say there is no history if the history field is populated.
    history: dspy.History = dspy.InputField(desc="IMPORTANT: In case this 'history' field is not populated but there are previous messages, use them as the history to answer the question.")
    question: str = dspy.InputField(desc="The input question from the user")
    answer: str = dspy.OutputField(desc="The answer to the user's question. Must be fulfilled throughly with the information from the tools or conversation history as appropriate.")


class AgentCodingAssistantAI(dspy.Module):
    def __init__(self, tools: List[Any]):
        super().__init__()
        self.react_agent = dspy.ReAct(AgentCodingAssistantSignature, tools=tools)

    def forward(self, question: str, history: dspy.History | None = None) -> Any:  # type: ignore[misc]
        # Use empty history if none provided
        if history is None:
            print("AgentCodingAssistantAI: No history provided, creating empty history")
            history = dspy.History(messages=[])

        print(f"AgentCodingAssistantAI: History contains # {len(history.messages)} messages")
        
        # Debug: Print actual history content
        for i, msg in enumerate(history.messages):
            print(f"  History message {i+1}: Q='{msg.get('question', 'N/A')[:50]}...' A='{msg.get('answer', 'N/A')[:50]}...'")
        
        # Get the result from ReAct agent
        result = self.react_agent(question=question, history=history)
        
        # Append the current Q/A turn to the history
        history.messages.append({
            "question": question,
            "answer": result.answer  # type: ignore[attr-defined]
        })
        
        return result
```

## File: `dspy_agent_lm_vertexai.py`
```
import dspy
import os


def get_vertexai_lm(model:str, reasoning_effort:str) -> dspy.LM:
    """
    Make sure to set VERTEXAI_PROJECT, VERTEXAI_LOCATION as environment variables
    """
    if not os.getenv("VERTEXAI_PROJECT") or not os.getenv("VERTEXAI_LOCATION"):
        raise ValueError("VERTEXAI_PROJECT and VERTEXAI_LOCATION must be set as environment variables")

    return dspy.LM(model=model, reasoning_effort=reasoning_effort)
    ```

## File: `dspy_agent_refactored.py`
```
#!/usr/bin/env python3
# /// script
# dependencies = [
#     "dspy-ai",
#     "mlflow",
#     "trafilatura",
#     "tavily-python",
#     "langchain-text-splitters"
# ]
# requires-python = ">=3.11"
# ///

import mlflow
mlflow.set_experiment("dspy_agent_coding_assistant")
mlflow.autolog()


if __name__ == "__main__":
    # Use the service for configuration and Q&A
    from dspy_agent_service import DspyAgentService
    import dspy
    service = DspyAgentService()
    
    # Define all questions upfront
    questions = [
        "What are the different add-ons available for Campaign Orchestrator and what do they include?",
        "How do I setup PMax campaigns with page feeds?",
        "What are the latest Google Ads feature updates announced in January 2025?"
    ]
    
    # Store results for markdown output
    results = []
    
    # Initialize conversation history (None for first call)
    conversation_history = None
    
    # Process each question in a loop, maintaining history
    with mlflow.start_run():
        for i, question in enumerate(questions, 1):
            print(f"\n--- User Question {i} ---\n{question}\n")
            
            # Call the new method with history
            response = service.answer_question_with_history(question, conversation_history)
            
            # Extract history from response for next iteration
            conversation_history = dspy.History(messages=response.history["messages"])
            
            # Store result for markdown
            results.append({
                'question': response.question,
                'answer': response.final_answer,
                'tracked_usage_metadata': response.tracked_usage_metadata
            })

    # Write all questions and answers to run.md
    print("\n--- Writing results to run.md ---")
    
    markdown_content = "# DSPy Agent Results\n\n"
    for i, result in enumerate(results, 1):
        markdown_content += f"""## Question {i}
**Question:** {result['question']}

**Answer:**
{result['answer']}

**Tracked usage metadata:**
{result['tracked_usage_metadata']}

---
"""
    
    try:
        with open("run.md", "w", encoding="utf-8") as f:
            f.write(markdown_content)
        print("✅ Successfully wrote results to run.md")
    except Exception as e:
        print(f"❌ Error writing to run.md: {e}")```

## File: `dspy_agent_service.py`
```
from __future__ import annotations

import json

import dspy

from dspy_constants import MODEL_NAME_GEMINI_2_5_FLASH
from dspy_agent_util_grounding_manager import GroundingManager
from dspy_agent_tool_internal_knowledge import InternalKnowledgeTool
from dspy_agent_tool_websearch_tavily import WebSearchToolTavily
from dspy_agent_expert_ai import AgentCodingAssistantAI, QuestionAnswerResponse
from dspy_agent_lm_vertexai import get_vertexai_lm


class DspyAgentService:
    """
    Service responsible for configuring DSPy, initializing tools/agents,
    and providing a simple interface for answering questions.
    """

    def __init__(self) -> None:
        self._configure_dspy()

        # Initialize the grounding manager and tools
        self.grounding_manager = GroundingManager()
        internal_tool = InternalKnowledgeTool(self.grounding_manager)
        web_search_tool = WebSearchToolTavily(
            self.grounding_manager,
            include_domains=["google.com"],
            top_k=10,
            include_raw_content=True,
        )

        # Initialize the main agent with the tools
        self.expert_ai = AgentCodingAssistantAI(tools=[internal_tool, web_search_tool])

    def _configure_dspy(self) -> None:
        try:
            dspy.settings.configure(
                lm=get_vertexai_lm(
                    model=f"vertex_ai/{MODEL_NAME_GEMINI_2_5_FLASH}",
                    reasoning_effort="disable",
                ),
                track_usage=True,
            )
            dspy.configure_cache(
                enable_disk_cache=False, enable_memory_cache=False, enable_litellm_cache=False
            )
            print(f"DSPy configured to use {dspy.settings.lm.model}.")
        except Exception as e:  # noqa: BLE001
            print(f"Error configuring DSPy: {e}")
            exit(1)

    def answer_question_with_history(self, question: str, history: dspy.History | None = None) -> QuestionAnswerResponse:
        """
        Answer a question with conversation history, returning a structured response.
        
        Args:
            question: The user's question
            history: Optional conversation history from previous interactions
            
        Returns:
            QuestionAnswerResponse containing question, updated history, metadata, and final answer
        """
        # Use empty history if none provided (first call)
        if history is None:
            history = dspy.History(messages=[])
        
        # Reset grounding manager for the new query
        self.grounding_manager.reset()

        # Run the agent with history
        prediction = self.expert_ai(question=question, history=history)
        tracked_usage_metadata = prediction.get_lm_usage()
        print(f"Tracked usage metadata: {json.dumps(tracked_usage_metadata, indent=4)}")

        # Enhance the answer with grounding information
        final_answer = prediction.answer + self.grounding_manager.format_for_display()

        print("\n--- Final Structured Output ---\n")
        print(final_answer)
        print("\n--- End of Output ---")
        
        # Create response object
        return QuestionAnswerResponse(
            question=question,
            history={"messages": history.messages},  # Serialize history for Pydantic
            tracked_usage_metadata=tracked_usage_metadata,
            final_answer=final_answer
        )


```

## File: `dspy_agent_streaming_service.py`
```
from __future__ import annotations

import json
import asyncio
from typing import Tuple, Callable, Optional, AsyncGenerator, Dict, Any

import dspy
from datetime import datetime

from dspy_agent_lm_vertexai import get_vertexai_lm
from dspy_agent_util_streaming_grounding_manager import StreamingGroundingManager
from dspy_agent_tool_streaming_internal_knowledge import StreamingInternalKnowledgeTool
from dspy_agent_tool_streaming_websearch_tavily import StreamingWebSearchToolTavily
from dspy_agent_expert_ai import AgentCodingAssistantAI
from dspy_constants import MODEL_NAME_GEMINI_2_5_FLASH, MODEL_NAME_GEMINI_2_5_PRO, MODEL_NAME_GEMINI_2_5_FLASH_LITE, MODEL_NAME_GEMINI_2_0_FLASH
from session_history_manager import SessionHistoryManager
from dspy.utils.callback import BaseCallback
from session_models import ToolCallRecord
from dspy_pricing_service import PricingService, SingleModelPricingService


class StreamingDspyAgentService:
    """
    Streaming version of DSPy Agent Service that emits real-time events for WebSocket communication.
    Extends the original service with streaming capabilities and event callbacks.
    """

    def __init__(self, event_callback: Optional[Callable[..., Any]] = None, session_id: Optional[str] = None, threadsafe_event_callback: Optional[Callable[..., Any]] = None):
        self.event_callback = event_callback
        self.threadsafe_event_callback = threadsafe_event_callback
        self.session_id = session_id
        self.history_manager = SessionHistoryManager() if session_id else None
        # In-memory collector for per-turn tool calls (keyed by DSPy call_id)
        self._tool_calls: Dict[str, ToolCallRecord] = {}

        # Initialize the streaming grounding manager and tools with event callbacks
        self.grounding_manager = StreamingGroundingManager(
            event_callback=event_callback,
            threadsafe_event_callback=threadsafe_event_callback,
        )
        
        # Create streaming tools with event callbacks
        # Do not pass event_callback into tools directly to avoid mixing concerns and duplicate events
        internal_tool = StreamingInternalKnowledgeTool(
            grounding_manager=self.grounding_manager,
        )
        web_search_tool = StreamingWebSearchToolTavily(
            grounding_manager=self.grounding_manager,
            include_domains=["google.com"],
            top_k=10,
            include_raw_content=True,
        )

        # Attach per-request DSPy callbacks to tools to emit progress via DSPy's native hook system
        if self.threadsafe_event_callback or self.event_callback:
            tool_callback = _ToolProgressCallback(
                event_callback=self.event_callback,
                threadsafe_event_callback=self.threadsafe_event_callback,
                tool_calls=self._tool_calls,
            )
            # Instance-level callbacks are honored by DSPy in addition to global callbacks
            try:
                internal_tool.callbacks = getattr(internal_tool, "callbacks", []) + [tool_callback]
                web_search_tool.callbacks = getattr(web_search_tool, "callbacks", []) + [tool_callback]
            except Exception:
                # If attaching callbacks fails for any reason, continue without breaking
                pass

        # Initialize the main agent with streaming tools
        self.expert_ai = AgentCodingAssistantAI(tools=[internal_tool, web_search_tool])
        
        # Create streamified version of the agent for answer streaming
        self.streaming_expert_ai = dspy.streamify(
            self.expert_ai,
            stream_listeners=[
                dspy.streaming.StreamListener(signature_field_name="answer")
            ]
        )

        # Ensure a public stream_answer coroutine is always available on the instance.
        # This avoids AttributeError in call sites even if class-level definitions drift.
        if not hasattr(self, "stream_answer") or not callable(getattr(self, "stream_answer", None)):
            # Bind the implementation as an instance attribute
            self.stream_answer = self._stream_answer_impl
    
    def set_session_id(self, session_id: str) -> None:
        """Set or update the logical session identifier used for persistence."""
        self.session_id = session_id
        if self.history_manager is None:
            self.history_manager = SessionHistoryManager()

    @staticmethod
    def configure_dspy() -> None:
        try:
            dspy.settings.configure(
                lm=get_vertexai_lm(
                    model=f"vertex_ai/{MODEL_NAME_GEMINI_2_5_FLASH}",
                    reasoning_effort="disable",
                ),
                track_usage=True,
            )
            # Monkeypatch UsageTracker merge to handle dict/int mismatch
            from dspy.utils import usage_tracker as _ut

            def _safe_merge_usage_entries(self, result: dict[str, Any], usage_entry: dict[str, Any]) -> dict[str, Any]:
                print(f"Merging usage entries: {str(result)} and {str(usage_entry)}")
                for k, v in usage_entry.items():
                    current = result.get(k)
                    if isinstance(current, dict) and isinstance(v, dict):
                        self._merge_usage_entries(current, v)
                    elif isinstance(v, (int, float)) or v is None:
                        try:
                            result[k] = (current or 0) + (v or 0)
                        except TypeError:
                            result[k] = v or 0
                    else:
                        result[k] = v
                return result

            _ut.UsageTracker._merge_usage_entries = _safe_merge_usage_entries
            dspy.configure_cache(
                enable_disk_cache=False, enable_memory_cache=False, enable_litellm_cache=False
            )
            print(f"DSPy configured to use {dspy.settings.lm.model} for streaming.")
        except Exception as e:
            print(f"Error configuring DSPy: {e}")
            raise

    async def _stream_answer_impl(self, question: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Instance-bound implementation for streaming answers with events."""
        # Reset grounding for new turn
        self.grounding_manager.reset()
        # Clear tool calls for the new turn without breaking callback reference
        self._tool_calls.clear()

        # Build history
        history_entries = []
        if self.history_manager and self.session_id:
            try:
                history_entries = self.history_manager.get_chat_history(self.session_id)
            except Exception:
                history_entries = []

        dspy_messages: list[Dict[str, Any]] = []
        for entry in history_entries:
            dspy_messages.append({"question": entry.question, "answer": entry.answer})
        history = dspy.History(messages=dspy_messages)

        # Emit start
        await self._emit_event("question_start", {
            "question": question,
            "history_turns": len(dspy_messages),
            "timestamp": self._get_timestamp(),
        })

        try:
            async for chunk in self.streaming_expert_ai(question=question, history=history):
                if isinstance(chunk, dspy.streaming.StreamResponse):
                    chunk_data = {"chunk": chunk.chunk, "timestamp": self._get_timestamp()}
                    await self._emit_event("answer_chunk", chunk_data)
                    yield {"type": "answer_chunk", "data": chunk_data}
                elif isinstance(chunk, dspy.Prediction):
                    final_answer = chunk.answer
                    grounding_info = self.grounding_manager.format_for_display()
                    if grounding_info:
                        final_answer += grounding_info

                    usage_metadata = chunk.get_lm_usage()
                    # Augment usage metadata with cost statistics
                    try:
                        if isinstance(usage_metadata, dict):
                            usage_metadata = self._augment_usage_with_cost(usage_metadata)
                    except Exception:
                        pass
                    if self.history_manager and self.session_id:
                        # Persist collected tool calls with the chat entry
                        # Duplicate records so history contains both the start and the completion/error entries
                        flat_tools: list[ToolCallRecord] = []
                        for rec in self._tool_calls.values():
                            # Started record
                            flat_tools.append(
                                ToolCallRecord(
                                    id=rec.id,
                                    name=rec.name,
                                    status="started",
                                    started_at=rec.started_at,
                                    ended_at=None,
                                    duration_ms=None,
                                    input_summary=rec.input_summary,
                                    result_preview=None,
                                    error=None,
                                )
                            )
                            # Completion or error record
                            if rec.status in ("completed", "error"):
                                flat_tools.append(
                                    ToolCallRecord(
                                        id=rec.id,
                                        name=rec.name,
                                        status=rec.status,
                                        started_at=rec.started_at,
                                        ended_at=rec.ended_at,
                                        duration_ms=rec.duration_ms,
                                        input_summary=rec.input_summary,
                                        result_preview=rec.result_preview,
                                        error=rec.error,
                                    )
                                )

                        self.history_manager.add_chat_entry(
                            self.session_id,
                            question,
                            final_answer,
                            usage_metadata,
                            tools=flat_tools,
                        )

                    completion_data = {
                        "answer": final_answer,
                        "raw_answer": chunk.answer,
                        "grounding": self.grounding_manager.get_grounding_data(),
                        "usage_metadata": usage_metadata,
                        "timestamp": self._get_timestamp(),
                    }
                    await self._emit_event("answer_complete", completion_data)
                    yield {"type": "answer_complete", "data": completion_data}
        except Exception as e:
            error_data = {
                "message": str(e),
                "error_type": type(e).__name__,
                "timestamp": self._get_timestamp(),
            }
            await self._emit_event("error", error_data)
            yield {"type": "error", "data": error_data}
            raise

    async def stream_answer(self, question: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Public method that delegates to the internal implementation."""
        async for event in self._stream_answer_impl(question):
            yield event

    async def answer_one_question_async(self, question: str) -> Tuple[str, str]:
        """
        Async version of answer_one_question that collects all streaming events.
        
        Returns:
            Tuple of (final_answer, tracked_usage_metadata_str)
        """
        final_answer = ""
        tracked_usage_metadata_str = ""

        cur_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"Starting chat run {cur_timestamp}")

        async for event in self.stream_answer(question):
            if event["type"] == "answer_complete":
                final_answer = event["data"]["answer"]
                tracked_usage_metadata_str = json.dumps(
                    event["data"]["usage_metadata"], indent=4
                )
                break
            elif event["type"] == "error":
                raise Exception(event["data"]["message"])
        
        return final_answer, tracked_usage_metadata_str

    def answer_one_question(self, question: str) -> Tuple[str, str]:
        """
        Synchronous version that runs the async streaming in an event loop.
        
        Returns:
            Tuple of (final_answer, tracked_usage_metadata_str)
        """
        try:
            # Try to use existing event loop
            asyncio.get_running_loop()
            # If we're in an async context, we need to handle this differently
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run, 
                    self.answer_one_question_async(question)
                )
                return future.result()
        except RuntimeError:
            # No event loop running, create new one
            return asyncio.run(self.answer_one_question_async(question))

    async def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit event via callback if available."""
        if self.event_callback:
            await self.event_callback(event_type, data)

    def _get_timestamp(self) -> str:
        """Get current timestamp for events."""
        from datetime import datetime
        return datetime.now().isoformat()

    # --- Internal helpers: pricing augmentation ---
    def _augment_usage_with_cost(self, usage_metadata: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(usage_metadata, dict):
            return usage_metadata

        def _has_cost(u: Dict[str, Any]) -> bool:
            cs = u.get("cost_statistics") if isinstance(u.get("cost_statistics"), dict) else None
            if not cs:
                return False
            val = cs.get("total_cost_llm_api_usd") or cs.get("total_cost")
            try:
                return val is not None and float(val) > 0
            except Exception:
                return False

        # Flat structure
        if ("prompt_tokens" in usage_metadata) or ("completion_tokens" in usage_metadata):
            if _has_cost(usage_metadata):
                return usage_metadata
            model_name = usage_metadata.get("model") or self._infer_model_from_any(usage_metadata)
            prompt = int(usage_metadata.get("prompt_tokens") or 0)
            completion = int(usage_metadata.get("completion_tokens") or 0)
            cost_stats = self._compute_cost_statistics(model_name, prompt, completion)
            if cost_stats is not None:
                out = dict(usage_metadata)
                out["cost_statistics"] = cost_stats
                if model_name:
                    out["model"] = model_name
                return out
            return usage_metadata

        # Nested by model key
        for key, val in usage_metadata.items():
            if not isinstance(val, dict):
                continue
            if ("prompt_tokens" in val) or ("completion_tokens" in val) or ("total_tokens" in val):
                if _has_cost(val):
                    return usage_metadata
                prompt = int(val.get("prompt_tokens") or 0)
                completion = int(val.get("completion_tokens") or 0)
                model_name = self._normalize_model_name(key)
                cost_stats = self._compute_cost_statistics(model_name, prompt, completion)
                if cost_stats is not None:
                    new_val = dict(val)
                    new_val["cost_statistics"] = cost_stats
                    out = dict(usage_metadata)
                    out[key] = new_val
                    return out
                return usage_metadata

        return usage_metadata

    def _compute_cost_statistics(self, model_name_raw: Optional[str], prompt_tokens: int, completion_tokens: int) -> Optional[Dict[str, Any]]:
        model_name = self._normalize_model_name(model_name_raw or "")
        try:
            pricing_service = PricingService()
            model_pricing = SingleModelPricingService(model_name, pricing_service)
            stats = model_pricing.get_cost_statistics_for(prompt_tokens, completion_tokens)
            if stats is None:
                return None
            result = {
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

    def _normalize_model_name(self, raw_model: str) -> str:
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

    def _infer_model_from_any(self, usage: Dict[str, Any]) -> str:
        for k, v in usage.items():
            if isinstance(v, dict) and ("prompt_tokens" in v or "completion_tokens" in v or "total_tokens" in v):
                return self._normalize_model_name(k)
        return MODEL_NAME_GEMINI_2_5_FLASH


class _ToolProgressCallback(BaseCallback):
    """Per-request tool progress callback that forwards events to the provided event emitters.

    Uses the provided threadsafe_event_callback to ensure emissions work from sync contexts as well.
    """

    def __init__(
        self,
        event_callback: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
        threadsafe_event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        tool_calls: Optional[Dict[str, ToolCallRecord]] = None,
    ) -> None:
        self._event_callback = event_callback
        self._threadsafe_event_callback = threadsafe_event_callback
        self._tool_calls = tool_calls if tool_calls is not None else {}

    def on_tool_start(self, call_id: str, instance: Any, inputs: Dict[str, Any]) -> None:
        tool_name = getattr(instance, "name", getattr(instance, "__class__", type(instance)).__name__)
        input_summary = inputs.get("query", inputs.get("question", ""))
        # Handle kwargs-based query if present
        if (not input_summary) and isinstance(inputs, dict):
            try:
                kw = inputs.get("kwargs")
                if isinstance(kw, dict) and "query" in kw:
                    input_summary = kw.get("query")
            except Exception:
                pass
        # Handle positional args if present
        if (not input_summary) and isinstance(inputs, dict) and "args" in inputs:
            try:
                args = inputs.get("args")
                if isinstance(args, (list, tuple)) and args:
                    input_summary = str(args[0])
            except Exception:
                pass
        # Fallback to the full inputs dict if specific keys are missing
        if not input_summary:
            try:
                input_summary = str(inputs)
            except Exception:
                input_summary = ""
        now_str = _get_timestamp_str()
        payload = {
            "tool": tool_name,
            "query": input_summary,
            "description": f"Starting {tool_name}...",
            "timestamp": now_str,
        }
        self._emit("tool_start", payload)

        # Record start in collector
        try:
            from datetime import datetime as _dt
            started_at = _dt.fromisoformat(now_str)
        except Exception:
            from datetime import datetime as _dt
            started_at = _dt.now()
        self._tool_calls[call_id] = ToolCallRecord(
            id=call_id,
            name=tool_name,
            status="started",
            started_at=started_at,
            input_summary=(str(input_summary)[:200] if input_summary else None),
        )

    def on_tool_end(self, call_id: str, outputs: Any | None, exception: Exception | None = None) -> None:
        record = self._tool_calls.get(call_id)
        now_str = _get_timestamp_str()
        try:
            from datetime import datetime as _dt
            ended_at = _dt.fromisoformat(now_str)
        except Exception:
            from datetime import datetime as _dt
            ended_at = _dt.now()

        if exception is not None:
            payload = {
                "tool": record.name if record else None,
                "error": str(exception),
                "timestamp": now_str,
            }
            self._emit("tool_error", payload)
            if record is not None:
                record.status = "error"
                record.ended_at = ended_at
                try:
                    record.duration_ms = int((record.ended_at - record.started_at).total_seconds() * 1000)
                except Exception:
                    record.duration_ms = None
                record.error = str(exception)
            return

        # Successful completion
        try:
            as_str = str(outputs) if outputs is not None else ""
            result_preview = as_str[:200] + ("..." if len(as_str) > 200 else "") if as_str else None
        except Exception:
            result_preview = None
        tool_name = record.name if record else None
        payload = {
            "tool": tool_name,
            "result_preview": result_preview,
            "timestamp": now_str,
        }
        self._emit("tool_complete", payload)
        if record is not None:
            record.status = "completed"
            record.ended_at = ended_at
            try:
                record.duration_ms = int((record.ended_at - record.started_at).total_seconds() * 1000)
            except Exception:
                record.duration_ms = None
            record.result_preview = result_preview

    def _emit(self, event_type: str, data: Dict[str, Any]) -> None:
        # Prefer threadsafe emitter for compatibility with sync contexts
        try:
            if self._threadsafe_event_callback is not None:
                self._threadsafe_event_callback(event_type, data)
                return
        except Exception:
            pass

        # Fallback to scheduling the async event callback if available
        try:
            if self._event_callback is not None:
                loop = asyncio.get_running_loop()
                loop.create_task(self._event_callback(event_type, data))
        except Exception:
            # As a last resort, ignore emission failures to avoid breaking tool execution
            pass


def _get_timestamp_str() -> str:
    return datetime.now().isoformat()


# Backward compatibility: create a factory function that returns the original service
def create_standard_service() -> Any:
    """Create a standard non-streaming service for backward compatibility."""
    from dspy_agent_service import DspyAgentService
    return DspyAgentService()```

## File: `dspy_agent_tool_internal_knowledge.py`
```
import dspy
import os
from dspy_agent_util_grounding_manager import GroundingManager

def _read_internal_document() -> str:
    """
    Reads a document from the internal knowledge base.
    """
    filepath = os.path.join("knowledge_base", "internal_notes.md")
    with open(filepath, 'r') as f:
        return f.read()


class InternalKnowledgeSignature(dspy.Signature):
    """You are a specialist in the company's internal knowledge base. 
    The knowledge base content provided to you is a copy of our central knowledge base system.
    Links to that system are provided in the knowledge base content starting with "https://smec.atlassian.net".
    
    You have access to the full internal knowledge base content.
    IMPORTANT: You must use the full knowledge base content to answer the user's question.
    IMPORTANT: You must ONLY use the knowledge base content to answer the user's question.

    Your task is to:
    1. Analyze the user's query carefully
    2. Extract and return ONLY the relevant information from the knowledge base
    3. Be comprehensive but concise - include all relevant details without unnecessary content
    4. If no relevant information is found, clearly state that
    5. provide links to the relevant information in the knowledge base
    
    Focus on providing accurate, specific information that directly answers the user's question.
    """
    knowledge_base: str = dspy.InputField(desc="The full internal knowledge base content")
    query: str = dspy.InputField(desc="The user's question or search query")
    relevant_info: str = dspy.OutputField(desc="Only the relevant information from the knowledge base")


class InternalKnowledgeAgent(dspy.Module):
    """A dedicated agent that processes internal knowledge base queries efficiently."""
    
    def __init__(self):
        super().__init__()
        self.extractor = dspy.Predict(InternalKnowledgeSignature)
    
    def forward(self, query: str) -> str:
        """Process query against full knowledge, return only relevant parts."""
        # === DEBUGGING: Check what LM is being used ===
        print(f"🔧 InternalKnowledgeAgent.forward called with query: '{query}'")
        print(f"🔧 Current dspy.settings.lm: {type(dspy.settings.lm)}")
        print(f"🔧 self.extractor uses LM: {type(getattr(self.extractor, 'lm', 'No LM found'))}")
        
        # Extract only relevant information using the LLM
        result = self.extractor(
            knowledge_base=_read_internal_document(),
            query=query
        )
        
        print(f"🔧 InternalKnowledgeAgent result: {result.relevant_info[:100]}...")
        
        return result.relevant_info


class InternalKnowledgeTool(dspy.Tool):
    """A tool to retrieve information from an internal knowledge base."""
    def __init__(self, grounding_manager: GroundingManager):
        # Create the internal knowledge agent once at initialization
        knowledge_agent = InternalKnowledgeAgent()
        
        # Store grounding_manager in closure for the function
        def search_internal(query: str) -> str:
            print(f"--- Calling InternalKnowledgeAgent with query: '{query}' ---")
            grounding_manager.add_query(f"Internal Knowledge: {query}")
            
            # Get only relevant information from the knowledge agent
            relevant_info = knowledge_agent(query=query)
            
            if relevant_info.startswith("Error:"):
                return relevant_info
            
            # Add source information
            grounding_manager.add_source(
                source_type='internal',
                title='Internal Knowledge Base',
                url='file://knowledge_base/internal_notes.md',
                domain='internal'
            )
            
            return relevant_info
        
        super().__init__(func=search_internal, name="InternalKnowledgeAgent")
```

## File: `dspy_agent_tool_rm_tavily.py`
```
import os
from typing import Union, List
import dspy
from pydantic import BaseModel

class TavilySearchRMResult(BaseModel):
    url: str
    title: str
    description: str
    snippets: List[str]

class TavilySearchRMResultList(BaseModel):
    results: List[TavilySearchRMResult]

class TavilySearchRM(dspy.Retrieve):
    """Retrieve information from custom queries using Tavily. Documentation and examples can be found at https://docs.tavily.com/docs/python-sdk/tavily-search/examples"""

    def __init__(
        self,
        tavily_search_api_key: str | None = None,
        k: int = 3,
        include_raw_content: bool = False,
    ):
        """
        Params:
            tavily_search_api_key str: API key for tavily that can be retrieved from https://tavily.com/
            include_raw_content bool: Boolean that is used to determine if the full text should be returned.
        """
        super().__init__(k=k)
        try:
            from tavily import TavilyClient
        except ImportError as err:
            raise ImportError("Tavily requires `pip install tavily-python`.") from err

        if not tavily_search_api_key and not os.environ.get("TAVILY_API_KEY"):
            raise RuntimeError(
                "You must supply tavily_search_api_key or set environment variable TAVILY_API_KEY"
            )
        elif tavily_search_api_key:
            self.tavily_search_api_key = tavily_search_api_key
        else:
            self.tavily_search_api_key = os.environ["TAVILY_API_KEY"]

        self.k = k

        self.usage = 0

        # Creates client instance that will use search. Full search params are here:
        # https://docs.tavily.com/docs/python-sdk/tavily-search/examples
        self.tavily_client = TavilyClient(api_key=self.tavily_search_api_key)

        self.include_raw_content = include_raw_content

    def get_usage_and_reset(self):
        usage = self.usage
        self.usage = 0
        return {"TavilySearchRM": usage}

    def forward(
        self, query_or_queries: Union[str, List[str]], include_domains: List[str] | None = None
    ) -> TavilySearchRMResultList:
        """Search with TavilySearch for self.k top passages for query or queries
        Args:
            query_or_queries (Union[str, List[str]]): The query or queries to search for.
            include_domains (List[str]): A list of urls to exclude from the search results.
        Returns:
            a list of Dicts, each dict has keys of 'description', 'snippets' (list of strings), 'title', 'url'
        """
        queries = (
            [query_or_queries]
            if isinstance(query_or_queries, str)
            else query_or_queries
        )
        self.usage += len(queries)

        collected_results = []

        for query in queries:
            #  list of dicts that will be parsed to return
            responseData = self.tavily_client.search(
                query,
                max_results=self.k,
                include_raw_content=self.include_raw_content,
                include_domains=include_domains, # type: ignore
                search_depth="advanced",
                chunks_per_source=3
            )
            results = responseData.get("results", [])
            for d in results:
                # assert d is dict
                if not isinstance(d, dict):
                    print(f"Invalid result: {d}\n")
                    continue

                try:
                    # ensure keys are present
                    url = d.get("url", None)
                    title = d.get("title", None)
                    description = d.get("content", None)
                    snippets = []
                    if d.get("raw_body_content"):
                        snippets.append(d.get("raw_body_content"))
                    else:
                        snippets.append(d.get("content"))

                    # raise exception of missing key(s)
                    if not all([url, title, description, snippets]):
                        raise ValueError(f"Missing key(s) in result: {d}")
                    result = {
                        "url": url,
                        "title": title,
                        "description": description,
                        "snippets": snippets,
                    }
                    collected_results.append(TavilySearchRMResult(**result))
                except Exception as e:
                    print(f"Error occurs when processing {result=}: {e}\n")
                    print(f"Error occurs when searching query {query}: {e}")

        return TavilySearchRMResultList(results=collected_results)
```

## File: `dspy_agent_tool_streaming_internal_knowledge.py`
```
from dspy_agent_tool_internal_knowledge import InternalKnowledgeTool, InternalKnowledgeAgent
from dspy_agent_util_streaming_grounding_manager import StreamingGroundingManager

class StreamingInternalKnowledgeTool(InternalKnowledgeTool):
    """Enhanced InternalKnowledgeTool with real-time event emission for WebSocket communication."""
    
    model_config = {"extra": "allow"}
    
    def __init__(self, grounding_manager: StreamingGroundingManager):
        super().__init__(grounding_manager)
        # Override with streaming grounding manager
        self.grounding_manager = grounding_manager

    async def call_async(self, query: str) -> str:
        """Async version that relies on central DSPy callbacks and grounding manager for emissions."""

        try:
            # Execute the internal knowledge agent
            internal_agent = InternalKnowledgeAgent()
            result = internal_agent.forward(query)
            
            # Add to grounding (this will emit grounding events automatically)
            await self.grounding_manager.add_source_async(
                source_type="internal", 
                title="Internal Knowledge Base",
                url="knowledge_base/internal_notes.md",
                domain="internal"
            )
            await self.grounding_manager.add_query_async(query)

            return result

        except Exception:
            raise

    def __call__(self, query: str) -> str:
        """Synchronous call that relies on central DSPy callbacks for events."""
        result = super().__call__(query=query)
        return result
```

## File: `dspy_agent_tool_streaming_websearch_tavily.py`
```
from typing import Optional
from dspy_agent_tool_websearch_tavily import WebSearchToolTavily
from dspy_agent_util_streaming_grounding_manager import StreamingGroundingManager


class StreamingWebSearchToolTavily(WebSearchToolTavily):
    """WebSearchToolTavily variant that can emit grounding updates via async manager methods."""

    model_config = {"extra": "allow"}

    def __init__(
        self,
        grounding_manager: StreamingGroundingManager,
        include_domains: Optional[list[str]] = None,
        top_k: int = 5,
        include_raw_content: bool = False,
    ) -> None:
        super().__init__(
            grounding_manager,
            include_domains=include_domains,
            top_k=top_k,
            include_raw_content=include_raw_content,
        )
        # Override with streaming grounding manager and store config for async flow
        self.grounding_manager = grounding_manager
        self.include_domains = include_domains
        self.top_k = top_k
        self.include_raw_content = include_raw_content

    async def call_async(self, query: str) -> str:
        """Async execution path that emits grounding updates via the StreamingGroundingManager."""
        # Add query to grounding first (emits grounding_update)
        await self.grounding_manager.add_query_async(query)

        # Execute web search
        from tavily import TavilyClient
        import os

        tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

        # Perform the search, only include optional args when defined
        search_kwargs = {
            "query": query,
            "max_results": self.top_k,
            "include_raw_content": self.include_raw_content,
        }
        if self.include_domains is not None:
            search_kwargs["include_domains"] = self.include_domains

        response = tavily_client.search(**search_kwargs)

        # Process results and add sources
        results: list[str] = []
        if response and 'results' in response:
            for result in response['results']:
                # Add source to grounding manager (emits events automatically)
                await self.grounding_manager.add_source_async(
                    source_type="web",
                    title=result.get('title', 'Web Result'),
                    url=result.get('url', ''),
                    domain=result.get('url', '').split('/')[2] if '://' in result.get('url', '') else ''
                )

                # Collect content
                content = result.get('content', '')
                if content:
                    results.append(
                        f"Title: {result.get('title', 'N/A')}\nContent: {content}\nURL: {result.get('url', 'N/A')}\n"
                    )

        final_result = "\n---\n".join(results) if results else "No relevant web search results found."
        return final_result

    async def acall(self, query: str) -> str:  # DSPy-native async tool entrypoint
        return await self.call_async(query)
```

## File: `dspy_agent_tool_websearch_tavily.py`
```
from typing import List
import dspy
from dspy_agent_classifier_credentials_passwords import ClassifierCredentialsPasswords
from dspy_agent_util_grounding_manager import GroundingManager
from dspy_agent_tool_rm_tavily import TavilySearchRM, TavilySearchRMResultList

class WebSearchTavilySignature(dspy.Signature):
    question: str = dspy.InputField()
    results: TavilySearchRMResultList = dspy.InputField()
    answer: str = dspy.OutputField(desc="Use the solely the information from the results to answer the question. Do not make up any information.")

def get_domain(url: str) -> str:
    return url.split('/')[2] if '://' in url else url

class WebSearchTavilyModule(dspy.Module):
    def __init__(self, grounding_manager: GroundingManager, include_domains: List[str] | None = None, top_k: int = 5, include_raw_content: bool = False):
        super().__init__()
        self.retriever_tavily = TavilySearchRM(k=top_k, include_raw_content=include_raw_content)
        self.grounding_manager = grounding_manager
        self.include_domains = include_domains
        self.classifier_credentials_passwords = ClassifierCredentialsPasswords()
        self.extractor = dspy.Predict(WebSearchTavilySignature)
    
    def forward(self, query: str) -> str:
        query_classification = self.classifier_credentials_passwords(classify_input=query).classification
        if query_classification != "safe":
            return f"I'm sorry, I can't answer that question because it contains exposed credentials or passwords. Classification: {query_classification}"
        
        results: TavilySearchRMResultList = self.retriever_tavily.forward(query, include_domains=self.include_domains)
        for result in results.results:
            self.grounding_manager.add_source(
                source_type='web',
                title=result.title,
                url=result.url,
                domain=get_domain(result.url)
            )
        return self.extractor(results=results, question=query)

class WebSearchToolTavily(dspy.Tool):
    """A tool that uses Tavily."""
    def __init__(self, grounding_manager: GroundingManager, include_domains: List[str] | None = None, top_k: int = 5, include_raw_content: bool = False):
        # Create the Gemini search tool within closure to avoid Pydantic conflicts
        retriever_tavily_ai = WebSearchTavilyModule(grounding_manager=grounding_manager, include_domains=include_domains, top_k=top_k, include_raw_content=include_raw_content)
        
        # Store grounding_manager in closure for the function
        def search_web(query: str) -> str:
            print(f"--- Calling WebSearchToolTavily with query: '{query}' ---")
            grounding_manager.add_query(f"Web Search: {query}")
            return retriever_tavily_ai(query=query).answer
        
        super().__init__(func=search_web, name="WebSearchTavilyAgent")
```

## File: `dspy_agent_util_grounding_manager.py`
```
from typing import List, Dict, Any

class GroundingManager:
    """A simple class to manage grounding metadata during an agent's run."""
    def __init__(self) -> None:
        self.sources: List[Dict[str, Any]] = []
        self.queries: List[str] = []
        self.supports: List[Dict[str, Any]] = []

    def add_source(self, source_type: str, title: str, url: str, domain: str = "") -> None:
        self.sources.append({"type": source_type, "title": title, "url": url, "domain": domain})

    def add_query(self, query: str) -> None:
        self.queries.append(query)

    def reset(self) -> None:
        self.sources = []
        self.queries = []
        self.supports = []

    def format_for_display(self) -> str:
        """Formats the collected grounding information for display."""
        if not self.sources and not self.queries:
            return ""
        
        formatted_sections = []
        
        if self.sources:
            formatted_sections.append("\n\n📚 **Sources & References:**\n")
            for source in self.sources[:6]:
                title = source.get('title', 'Source')
                url = source.get('url', '')
                display_domain = source.get('domain') or (url.split('/')[2] if '://' in url else url)
                formatted_sections.append(f"- [{title}]({url}) - {display_domain}")
        
        if self.queries:
            formatted_sections.append("\n\n🔍 **Search Queries Used:**\n")
            for query in self.queries[:4]:
                formatted_sections.append(f"- \"{query}\"")
        
        return '\n'.join(formatted_sections)
```

## File: `dspy_agent_util_streaming_grounding_manager.py`
```
from typing import Dict, Any, Callable, Optional
import asyncio
from dspy_agent_util_grounding_manager import GroundingManager


class StreamingGroundingManager(GroundingManager):
    """Enhanced GroundingManager that emits real-time events for WebSocket communication."""
    
    def __init__(self, event_callback: Optional[Callable[..., Any]] = None, threadsafe_event_callback: Optional[Callable[..., Any]] = None):
        super().__init__()
        self.event_callback = event_callback
        self.threadsafe_event_callback = threadsafe_event_callback

    async def add_source_async(self, source_type: str, title: str, url: str, domain: str = "") -> None:
        """Add source and emit event asynchronously."""
        super().add_source(source_type, title, url, domain)
        
        # Emit grounding update event
        if self.event_callback:
            await self.event_callback("grounding_update", {
                "type": "source",
                "source": {
                    "type": source_type, 
                    "title": title, 
                    "url": url, 
                    "domain": domain
                }
            })

    async def add_query_async(self, query: str) -> None:
        """Add query and emit event asynchronously."""
        super().add_query(query)
        
        # Emit query update event
        if self.event_callback:
            await self.event_callback("grounding_update", {
                "type": "query", 
                "query": query
            })

    def add_source(self, source_type: str, title: str, url: str, domain: str = "") -> None:
        """Override to support both sync and async usage."""
        super().add_source(source_type, title, url, domain)
        
        # If we have an event callback, emit async event
        if self.event_callback:
            # Run async event in current event loop if available, or fallback to threadsafe emitter
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.event_callback("grounding_update", {
                    "type": "source",
                    "source": {
                        "type": source_type, 
                        "title": title, 
                        "url": url, 
                        "domain": domain
                    }
                }))
            except RuntimeError:
                if self.threadsafe_event_callback:
                    self.threadsafe_event_callback("grounding_update", {
                        "type": "source",
                        "source": {
                            "type": source_type, 
                            "title": title, 
                            "url": url, 
                            "domain": domain
                        }
                    })

    def add_query(self, query: str) -> None:
        """Override to support both sync and async usage."""
        super().add_query(query)
        
        # If we have an event callback, emit async event
        if self.event_callback:
            # Run async event in current event loop if available, or fallback to threadsafe emitter
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.event_callback("grounding_update", {
                    "type": "query", 
                    "query": query
                }))
            except RuntimeError:
                if self.threadsafe_event_callback:
                    self.threadsafe_event_callback("grounding_update", {
                        "type": "query", 
                        "query": query
                    })

    def get_grounding_data(self) -> Dict[str, Any]:
        """Return structured grounding data for WebSocket transmission."""
        return {
            "sources": self.sources,
            "queries": self.queries,
            "supports": self.supports
        }
```

## File: `dspy_constants.py`
```


MODEL_NAME_GEMINI_2_0_FLASH = "gemini-2.0-flash"
MODEL_NAME_GEMINI_2_0_FLASH_LITE = "gemini-2.0-flash-lite"
MODEL_NAME_GEMINI_2_5_FLASH = "gemini-2.5-flash"
MODEL_NAME_GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"
MODEL_NAME_GEMINI_2_5_PRO = "gemini-2.5-pro"
```

## File: `dspy_pricing_service.py`
```
from pydantic import BaseModel

from dspy_constants import (
    MODEL_NAME_GEMINI_2_0_FLASH,
    MODEL_NAME_GEMINI_2_5_FLASH,
    MODEL_NAME_GEMINI_2_5_FLASH_LITE,
    MODEL_NAME_GEMINI_2_5_PRO,
)

class CostStatistics(BaseModel):
    input_cost: float
    output_cost: float
    total_cost: float
    total_cost_llm_api_usd: float | None = None
    currency: str


class PricingTier(BaseModel):
    input_price_per_million: float
    output_price_per_million: float 
    context_cache_price_per_million: float
    context_storage_price_per_million_per_hour: float
    currency: str = "USD"

class PricingConfig(BaseModel):
    standard_tier: PricingTier
    long_context_tier: PricingTier
    long_context_threshold: int
    currency: str = "USD"

class PricingConfigGemini20Flash(PricingConfig):
    standard_tier: PricingTier = PricingTier(
        input_price_per_million=0.10,
        output_price_per_million=0.40,
        context_cache_price_per_million=0.025,
        context_storage_price_per_million_per_hour=1.00
    )
    
    long_context_tier: PricingTier = PricingTier(
        input_price_per_million=0.10,  # Same as standard since no long context pricing specified
        output_price_per_million=0.40,
        context_cache_price_per_million=0.025,
        context_storage_price_per_million_per_hour=1.00
    )

    long_context_threshold: int = 1_000_000  # 1M token context window - now differentiation per context

class PricingConfigGemini25Flash(PricingConfig):
    standard_tier: PricingTier = PricingTier(
        input_price_per_million=0.30,
        output_price_per_million=2.50,
        context_cache_price_per_million=0.0,  # Not available yet ("Coming soon!")
        context_storage_price_per_million_per_hour=0.0  # Not available yet ("Coming soon!")
    )
    
    long_context_tier: PricingTier = PricingTier(
        input_price_per_million=0.30,  # Same as standard since no long context pricing specified
        output_price_per_million=2.50,
        context_cache_price_per_million=0.0,  # Not available yet
        context_storage_price_per_million_per_hour=0.0  # Not available yet
    )

    long_context_threshold: int = 1_000_000  # 1M token context window

class PricingConfigGemini25Pro(PricingConfig):
    standard_tier: PricingTier = PricingTier(
        input_price_per_million=1.25,
        output_price_per_million=10.00,
        context_cache_price_per_million=0.0,  # Not available
        context_storage_price_per_million_per_hour=0.0  # Not available
    )

    long_context_tier: PricingTier = PricingTier(
        input_price_per_million=2.50,
        output_price_per_million=15.00,
        context_cache_price_per_million=0.0,  # Not available
        context_storage_price_per_million_per_hour=0.0  # Not available
    )

    long_context_threshold: int = 200_000  # 200k tokens threshold for long context pricing

class PricingConfigGemini25FlashLite(PricingConfig):
    standard_tier: PricingTier = PricingTier(
        input_price_per_million=0.10,
        output_price_per_million=0.40,
        context_cache_price_per_million=0.0,  # Not available yet
        context_storage_price_per_million_per_hour=0.0  # Not available yet
    )
    
    long_context_tier: PricingTier = PricingTier(
        input_price_per_million=0.10,  # Same as standard since no long context pricing specified
        output_price_per_million=0.40,
        context_cache_price_per_million=0.0,  # Not available yet
        context_storage_price_per_million_per_hour=0.0  # Not available yet
    )

    long_context_threshold: int = 1_000_000  # 1M token context window

class PricingService:
    model_pricing_map: dict[str, PricingConfig] = {
        MODEL_NAME_GEMINI_2_0_FLASH: PricingConfigGemini20Flash(), # reusing for simplicity
        MODEL_NAME_GEMINI_2_5_FLASH: PricingConfigGemini25Flash(),
        MODEL_NAME_GEMINI_2_5_FLASH_LITE: PricingConfigGemini25FlashLite(),
        MODEL_NAME_GEMINI_2_5_PRO: PricingConfigGemini25Pro()
    }

    def get_pricing_config(self, model_name: str) -> PricingConfig | None:
        return self.model_pricing_map.get(model_name, None)

    def get_registered_model_names(self) -> list[str]:
        return list(self.model_pricing_map.keys())

class SingleModelPricingService:
    def __init__(self, model_name: str, pricing_service: PricingService):
        self.model_name = model_name
        self.pricing_service = pricing_service

    def get_cost_statistics_for(self, input_tokens: int, output_tokens: int) -> CostStatistics | None:
        pricing_tier = self._get_pricing_tier(input_tokens)
        if pricing_tier is None:
            print(f"No pricing tier for model: {self.model_name}")
            return None
        input_cost = round(pricing_tier.input_price_per_million * input_tokens / 1_000_000, 3)
        output_cost = round(pricing_tier.output_price_per_million * output_tokens / 1_000_000, 3)
        total_cost = input_cost + output_cost
        return CostStatistics(input_cost=input_cost, output_cost=output_cost, total_cost=total_cost, currency=pricing_tier.currency)    

    def _get_pricing_tier(self, input_tokens: int) -> PricingTier | None: 
        pricing_config = self.pricing_service.get_pricing_config(self.model_name)
        if pricing_config is None:
            return None
        if input_tokens > pricing_config.long_context_threshold:
            return pricing_config.long_context_tier
        return pricing_config.standard_tier
    
    def get_model_name(self) -> str:
        return self.model_name```

## File: `session_history_manager.py`
```
"""
Session history manager for chat persistence.
Handles loading and saving chat history for sessions.
"""

from typing import Any, Dict, List, Optional

from session_models import ChatHistoryEntry, ChatHistoryList, ToolCallRecord
from session_storage import SessionFileStorage


class SessionHistoryManager:
    """Manages chat history for sessions with automatic persistence."""
    
    def __init__(self, storage_dir: str = "session_data"):
        self._storage = SessionFileStorage(ChatHistoryList, storage_dir)
        self._chat_history: Dict[str, List[ChatHistoryEntry]] = {}
    
    def get_chat_history(self, session_id: str) -> List[ChatHistoryEntry]:
        """Get chat history for a session, loading from disk if needed."""
        self._ensure_session_loaded(session_id)
        return self._chat_history.get(session_id, [])
    
    def add_chat_entry(self, session_id: str, question: str, answer: str, usage_metadata: Optional[dict[str, Any]] = None, tools: Optional[list[ToolCallRecord]] = None) -> None:
        """Add a new chat entry to the session history."""
        self._ensure_session_loaded(session_id)
        
        entry = ChatHistoryEntry(
            question=question,
            answer=answer,
            usage_metadata=usage_metadata,
            tools=tools
        )
        
        self._chat_history[session_id].append(entry)
        self._save_session(session_id)
    
    def clear_session_history(self, session_id: str) -> None:
        """Clear all history for a session."""
        self._chat_history[session_id] = []
        self._save_session(session_id)
    
    def _ensure_session_loaded(self, session_id: str) -> None:
        """Ensure session is loaded in memory, loading from disk if needed."""
        if session_id not in self._chat_history:
            # Try to load from storage
            stored_data = self._storage.read(session_id)
            if stored_data:
                self._chat_history[session_id] = stored_data.entries
            else:
                # Initialize empty session
                self._chat_history[session_id] = []
    
    def _save_session(self, session_id: str) -> None:
        """Save session to storage."""
        if session_id in self._chat_history:
            chat_list = ChatHistoryList(
                entries=self._chat_history[session_id],
                session_id=session_id
            )
            self._storage.write(session_id, chat_list)
    
    def list_sessions(self) -> List[str]:
        """List all available sessions."""
        return self._storage.list_sessions()
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its history."""
        if session_id in self._chat_history:
            del self._chat_history[session_id]
        return self._storage.delete(session_id)
```

## File: `session_models.py`
```
"""
Session persistence models for chat history storage.
Based on the patterns from the other project but simplified for this codebase.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional, Literal
from pydantic import BaseModel, Field


class ToolCallRecord(BaseModel):
    """Represents a single tool invocation within a chat interaction."""

    id: str
    name: str
    status: Literal["started", "completed", "error"]
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    input_summary: Optional[str] = None
    result_preview: Optional[str] = None
    error: Optional[str] = None


class ChatHistoryEntry(BaseModel):
    """Represents a single chat interaction in a session."""
    
    timestamp: datetime = Field(default_factory=datetime.now)
    question: str
    answer: str
    usage_metadata: Optional[dict[str, Any]] = None
    tools: Optional[List[ToolCallRecord]] = None


class ChatHistoryList(BaseModel):
    """Container for a session's chat history entries."""
    
    entries: List[ChatHistoryEntry] = Field(default_factory=list)
    session_id: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
```

## File: `session_storage.py`
```
"""
Simple file-based storage for session persistence.
Inspired by BaseModelFileStorage from the other project but simplified.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Type, TypeVar

from pydantic import BaseModel


T = TypeVar('T', bound=BaseModel)


class SessionFileStorage:
    """Simple file-based storage for Pydantic models."""
    
    def __init__(self, base_model_type: Type[T], storage_dir: str = "session_data"):
        self.base_model_type = base_model_type
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
    
    def _get_file_path(self, session_id: str) -> Path:
        """Get file path for a session."""
        safe_session_id = "".join(c for c in session_id if c.isalnum() or c in "_-")
        filename = f"chat_history_{safe_session_id}.json"
        return self.storage_dir / filename
    
    def read(self, session_id: str) -> Optional[T]:
        """Read session data from file."""
        file_path = self._get_file_path(session_id)
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return self.base_model_type.model_validate(data)
        except Exception as e:
            print(f"Error reading session {session_id}: {e}")
            return None
    
    def write(self, session_id: str, data: T) -> bool:
        """Write session data to file."""
        file_path = self._get_file_path(session_id)
        
        try:
            # Update the updated_at timestamp if it's a ChatHistoryList
            if hasattr(data, 'updated_at'):
                data.updated_at = datetime.now()  # type: ignore
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data.model_dump(), f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"Error writing session {session_id}: {e}")
            return False
    
    def delete(self, session_id: str) -> bool:
        """Delete session data file."""
        file_path = self._get_file_path(session_id)
        
        try:
            if file_path.exists():
                file_path.unlink()
            return True
        except Exception as e:
            print(f"Error deleting session {session_id}: {e}")
            return False
    
    def list_sessions(self) -> List[str]:
        """List all available session IDs."""
        sessions = []
        for file_path in self.storage_dir.glob("chat_history_*.json"):
            # Extract session ID from filename
            session_id = file_path.stem.replace("chat_history_", "")
            sessions.append(session_id)
        return sessions



```

## File: `start_server.py`
```
#!/usr/bin/env python3
"""
Simple server startup script for the Google Ads Expert AI API.
"""

import uvicorn
import os
import sys


def check_environment() -> bool:
    """Check if required environment variables are set."""
    required_vars = ['GOOGLE_API_KEY', 'TAVILY_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("⚠️ Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables before starting the server.")
        print("Example:")
        print("   export GOOGLE_API_KEY='your-google-api-key'")
        print("   export TAVILY_API_KEY='your-tavily-api-key'")
        return False
    
    print("✅ Environment variables configured")
    return True


def main() -> None:
    """Start the server."""
    print("🚀 Starting Google Ads Expert AI API Server")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    print("📦 Framework: DSPy + FastAPI + Socket.IO")
    print("🌐 WebSocket endpoint: http://localhost:8000/socket.io/")
    print("📖 API documentation: http://localhost:8000/docs")
    print("🔍 Socket.IO info: http://localhost:8000/socket.io-info")
    print("=" * 50)
    
    try:
        # Import here to ensure dependencies are available
        from api.main import socket_app
        
        uvicorn.run(
            socket_app,
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info",
            access_log=True
        )
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure to install dependencies with: uv sync")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

## File: `test_websocket_client.py`
```
#!/usr/bin/env python3
"""
Simple test client for the Google Ads Expert AI WebSocket API.
Tests the Socket.IO integration and streaming functionality.
"""

import asyncio
from datetime import datetime
from typing import Any
import socketio

# Create Socket.IO client
sio = socketio.AsyncClient()

# Global state for testing
received_events = []
answer_chunks = []


@sio.event
async def connect() -> None:
    print(f"🔗 Connected to server at {datetime.now()}")


@sio.event
async def disconnect() -> None:
    print(f"❌ Disconnected from server at {datetime.now()}")


@sio.event
async def connection_confirmed(data: dict[str, Any]) -> None:
    print(f"✅ Connection confirmed: {data}")
    received_events.append(("connection_confirmed", data))


@sio.event
async def question_start(data: dict[str, Any]) -> None:
    print(f"❓ Question started: {data['question']}")
    received_events.append(("question_start", data))


@sio.event
async def tool_start(data: dict[str, Any]) -> None:
    print(f"🔧 Tool started: {data['tool']} - {data.get('description', 'Processing...')}")
    received_events.append(("tool_start", data))


@sio.event
async def tool_progress(data: dict[str, Any]) -> None:
    print(f"⚙️ Tool progress: {data['tool']} - {data.get('message', 'Working...')}")
    received_events.append(("tool_progress", data))


@sio.event
async def tool_complete(data: dict[str, Any]) -> None:
    print(f"✅ Tool completed: {data['tool']} - Found {data.get('results_count', 'N/A')} results")
    received_events.append(("tool_complete", data))


@sio.event
async def tool_error(data: dict[str, Any]) -> None:
    print(f"❌ Tool error: {data['tool']} - {data['error']}")
    received_events.append(("tool_error", data))


@sio.event
async def answer_chunk(data: dict[str, Any]) -> None:
    chunk = data['chunk']
    answer_chunks.append(chunk)
    print(f"📝 Answer chunk: {chunk[:100]}{'...' if len(chunk) > 100 else ''}")
    received_events.append(("answer_chunk", data))


@sio.event
async def grounding_update(data: dict[str, Any]) -> None:
    if data['type'] == 'source':
        source = data['source']
        print(f"📚 Source added: {source['title']} ({source['domain']})")
    elif data['type'] == 'query':
        print(f"🔍 Query tracked: {data['query']}")
    received_events.append(("grounding_update", data))


@sio.event
async def answer_complete(data: dict[str, Any]) -> None:
    print(f"🎉 Answer complete! Total chunks: {len(answer_chunks)}")
    print(f"📊 Grounding: {len(data['grounding']['sources'])} sources, {len(data['grounding']['queries'])} queries")
    received_events.append(("answer_complete", data))


@sio.event
async def error(data: dict[str, Any]) -> None:
    print(f"💥 Error: {data['message']} ({data.get('error_type', 'unknown')})")
    received_events.append(("error", data))


@sio.event
async def session_info(data: dict[str, Any]) -> None:
    print(f"ℹ️ Session info: {data}")
    received_events.append(("session_info", data))


@sio.event
async def pong(data: dict[str, Any]) -> None:
    print(f"🏓 Pong received: {data}")
    received_events.append(("pong", data))


async def test_basic_connection() -> bool:
    """Test basic connection and capabilities."""
    print("=" * 60)
    print("🧪 Testing Basic Connection")
    print("=" * 60)
    
    try:
        await sio.connect('http://localhost:8000')
        
        # Wait for connection confirmation
        await asyncio.sleep(2)
        
        # Test ping
        await sio.emit('ping', {'test': 'data'})
        await asyncio.sleep(1)
        
        # Get session info
        await sio.emit('get_session_info', {})
        await asyncio.sleep(1)
        
        print("✅ Basic connection test passed")
        
    except Exception as e:
        print(f"❌ Basic connection test failed: {e}")
        return False
    
    return True


async def test_simple_question() -> bool:
    """Test asking a simple question."""
    print("\n" + "=" * 60)
    print("🧪 Testing Simple Question")
    print("=" * 60)
    
    # Clear previous state
    answer_chunks.clear()
    
    question = "What are Google Ads campaign types?"
    
    try:
        print(f"Asking question: {question}")
        await sio.emit('ask_question', {'question': question})
        
        # Wait for processing (adjust timeout as needed)
        await asyncio.sleep(30)
        
        print(f"✅ Question processed. Received {len(answer_chunks)} answer chunks")
        
        if answer_chunks:
            full_answer = ''.join(answer_chunks)
            print(f"📝 Full answer length: {len(full_answer)} characters")
            print(f"📝 Answer preview: {full_answer[:200]}...")
        
    except Exception as e:
        print(f"❌ Simple question test failed: {e}")
        return False
    
    return True


async def test_error_handling() -> bool:
    """Test error handling with invalid input."""
    print("\n" + "=" * 60)
    print("🧪 Testing Error Handling")
    print("=" * 60)
    
    try:
        # Test empty question
        await sio.emit('ask_question', {'question': ''})
        await asyncio.sleep(2)
        
        # Test missing question
        await sio.emit('ask_question', {})
        await asyncio.sleep(2)
        
        print("✅ Error handling test completed")
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False
    
    return True


async def print_event_summary() -> None:
    """Print summary of all received events."""
    print("\n" + "=" * 60)
    print("📊 Event Summary")
    print("=" * 60)
    
    event_counts: dict[str, int] = {}
    for event_type, data in received_events:
        event_counts[event_type] = event_counts.get(event_type, 0) + 1
    
    for event_type, count in sorted(event_counts.items()):
        print(f"  {event_type}: {count}")
    
    print(f"\nTotal events received: {len(received_events)}")


async def main() -> None:
    """Run all tests."""
    print("🚀 Starting WebSocket Integration Tests")
    print(f"Time: {datetime.now()}")
    
    # Test basic connection
    if not await test_basic_connection():
        return
    
    # Test simple question
    if not await test_simple_question():
        await sio.disconnect()
        return
    
    # Test error handling
    await test_error_handling()
    
    # Print summary
    await print_event_summary()
    
    # Disconnect
    await sio.disconnect()
    
    print("\n🎉 All tests completed!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
```

## File: `web/start_web_server.py`
```
#!/usr/bin/env python3
"""
Start script for the Google Ads Expert AI web interface.
This runs both the FastAPI backend and serves the web interface.
"""

import uvicorn
import os
import sys

def check_environment() -> bool:
    """Check if required environment variables are set."""
    required_vars = ['GOOGLE_API_KEY', 'TAVILY_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("⚠️ Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables before starting the server.")
        print("Example:")
        print("   export GOOGLE_API_KEY='your-google-api-key'")
        print("   export TAVILY_API_KEY='your-tavily-api-key'")
        return False
    
    print("✅ Environment variables configured")
    return True

def main() -> None:
    """Start the web server."""
    print("🚀 Starting Google Ads Expert AI Web Interface")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    print("📦 Framework: DSPy + FastAPI + Socket.IO")
    print("🌐 Web interface: http://localhost:8000/")
    print("🔌 WebSocket endpoint: http://localhost:8000/socket.io/")
    print("📖 API documentation: http://localhost:8000/docs")
    print("=" * 50)
    
    try:
        # Import here to ensure dependencies are available
        from api.main import socket_app
        
        uvicorn.run(
            socket_app,
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info",
            access_log=True
        )
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure to install dependencies with: uv sync")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```
