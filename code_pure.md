# Directory Structure
_Includes files where the actual content might be omitted. This way the LLM can still use the file structure to understand the project._
```
.
├── api
│   ├── __init__.py
│   ├── main.py
│   ├── routes
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   └── health.py
│   └── websocket_manager.py
├── chat_history_converter.py
├── cli_gather_info.py
├── dspy_agent_classifier_credentials_passwords.py
├── dspy_agent_classifier_credentials_passwords_examples.py
├── dspy_agent_classifier_credentials_passwords_optimized.py
├── dspy_agent_expert_ai.py
├── dspy_agent_lm_vertexai.py
├── dspy_agent_streaming_service.py
├── dspy_agent_tool_cgiant.py
├── dspy_agent_tool_code_term_search.py
├── dspy_agent_tool_gemini.py
├── dspy_agent_tool_internal_knowledge.py
├── dspy_agent_tool_lc_filesystem.py
├── dspy_agent_tool_restricted_shell.py
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
    ├── app.js
    ├── index.html
    └── start_web_server.py
```

# File Contents

## File: `api/__init__.py`
```
# API package for Agent Coding Assistant
```

## File: `api/main.py`
```
from fastapi import FastAPI, Request, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Tuple, Any
import uvicorn
import os
import glob

from api.websocket_manager import AgentWebSocketManager
from api.routes import health, agent
from dspy_agent_streaming_service import StreamingDspyAgentService

import mlflow
mlflow.set_experiment("dspy_agent_coding_assistant_api_main")
mlflow.autolog()

# Create FastAPI application
app = FastAPI(
    title="Agent Coding Assistant API",
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
        reload_includes=["*.py"],
        log_level="info"
    )
```

## File: `api/routes/__init__.py`
```
# API routes package
```

## File: `api/routes/agent.py`
```
from fastapi import APIRouter
from typing import Any


router = APIRouter()


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
            },
            {
                "name": "read_file",
                "description": "Read contents of files on the filesystem"
            },
            {
                "name": "list_directory",
                "description": "List contents of directories on the filesystem"
            },
            {
                "name": "write_file",
                "description": "Write or append content to files on the filesystem"
            },
            {
                "name": "restricted_shell",
                "description": "Execute safe shell commands with restrictions"
            },
            {
                "name": "giant_ask_codebase",
                "description": "Search and analyze codebase using Codegiant"
            },
            {
                "name": "giant_review_git_diff",
                "description": "Review code changes using Codegiant"
            }
        ],
        "endpoints": {
            "http": {
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
        "service": "Agent Coding Assistant",
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
        "service": "Agent Coding Assistant",
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
                'message': 'Connected to Agent Coding Assistant',
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
    main() 
```

## File: `cli_gather_info.py`
```
#!/usr/bin/env python3
"""
CLI tool to gather information using code search, web search, and codebase analysis.

This script uses a ReAct agent to intelligently gather information from:
1. CodeTermSearch - Search for terms/patterns in the codebase
2. WebSearchTavilyAgent - Search the web for up-to-date information
3. GiantAskCodebase - Semantic Q&A over the entire codebase

Usage:
    uv run python cli_gather_info.py "How is pricing calculated in the service?"
    uv run python cli_gather_info.py "Explain Gemini cost logic" --verbose
"""

import argparse
import os
import sys

import dspy
from dspy_agent_lm_vertexai import get_vertexai_lm
from dspy_agent_tool_code_term_search import CodeTermSearchTool
from dspy_agent_tool_websearch_tavily import WebSearchToolTavily
from dspy_agent_tool_cgiant import GiantAskCodebaseTool
from dspy_agent_util_grounding_manager import GroundingManager
from dspy_constants import MODEL_NAME_GEMINI_2_5_FLASH


class GatherInfoSignature(dspy.Signature):
    """Signature for gathering information using available tools."""

    context: str = dspy.InputField(desc="The context that describes the environment this question is being asked in")
    question: str = dspy.InputField(desc="The question to gather information about")
    answer: str = dspy.OutputField(desc="The comprehensive answer based on gathered information")


def configure_dspy() -> None:
    """Configure DSPy with Gemini 2.5 Flash model."""
    try:
        # Check for required Vertex AI credentials
        if not os.getenv("VERTEXAI_PROJECT"):
            project = os.getenv("GOOGLE_CLOUD_PROJECT")
            if not project:
                print("❌ VERTEXAI_PROJECT environment variable not set")
                print("   Set it with: export VERTEXAI_PROJECT=your-project-id")
                print("   Or use: export GOOGLE_CLOUD_PROJECT=your-project-id")
                sys.exit(1)
            os.environ["VERTEXAI_PROJECT"] = project

        if not os.getenv("VERTEXAI_LOCATION"):
            location = os.getenv("GOOGLE_CLOUD_LOCATION") or "us-central1"
            os.environ["VERTEXAI_LOCATION"] = location

        # Configure DSPy
        dspy.settings.configure(
            lm=get_vertexai_lm(
                model=f"vertex_ai/{MODEL_NAME_GEMINI_2_5_FLASH}",
                reasoning_effort="disable",
            ),
            track_usage=True,
        )

        # Disable caching for fresh results
        dspy.configure_cache(
            enable_disk_cache=False,
            enable_memory_cache=False,
            enable_litellm_cache=False
        )

        print(f"✅ DSPy configured with {dspy.settings.lm.model}")
    except Exception as e:
        print(f"❌ Error configuring DSPy: {e}")
        print("   Make sure you have:")
        print("   - Valid VertexAI credentials")
        print("   - GOOGLE_APPLICATION_CREDENTIALS set (if using service account)")
        sys.exit(1)


def create_tools(grounding_manager: GroundingManager):
    """Create the information gathering tools."""
    tools = []

    # Create code search tool (always available)
    code_search_tool = CodeTermSearchTool(grounding_manager=grounding_manager)
    tools.append(code_search_tool)
    print("✅ Code search tool ready")

    # Create web search tool (requires Tavily API key)
    web_search_tool = WebSearchToolTavily(
        grounding_manager=grounding_manager,
        top_k=10,
        include_raw_content=True
    )
    tools.append(web_search_tool)
    print("✅ Web search tool ready")

    # Create GiantAskCodebase tool (requires codegiant.sh)
    giant_ask_tool = GiantAskCodebaseTool(grounding_manager=grounding_manager)
    tools.append(giant_ask_tool)
    print("✅ Codebase analysis tool ready")

    return tools


def create_react_agent(tools):
    """Create a ReAct agent with the information gathering tools."""
    return dspy.ReAct(GatherInfoSignature, tools=tools)


def print_grounding_info(grounding_manager: GroundingManager, verbose: bool = False):
    """Print grounding information from all tools."""

    if grounding_manager.queries and verbose:
        print("\n🔍 **Queries Made:**")
        for query in grounding_manager.queries[:5]:  # Limit to avoid clutter
            print(f"  - {query}")

    if grounding_manager.sources and verbose:
        print("\n📚 **Sources Used:**")
        for source in grounding_manager.sources[:8]:  # Limit to avoid clutter
            title = source.get('title', 'Unknown')
            domain = source.get('domain', 'N/A')
            print(f"  - {title} ({domain})")


def main():
    """Main CLI entry point."""
    try:
        parser = argparse.ArgumentParser(
            description="Gather information using code search, web search, and codebase analysis",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  uv run python cli_gather_info.py "How is pricing calculated in the service?"
  uv run python cli_gather_info.py "Explain Gemini cost logic" --verbose
  uv run python cli_gather_info.py "What are the main components?" --session-id abc123
            """
        )

        parser.add_argument(
            "question",
            help="The question to gather information about"
        )

        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Show detailed information including tool calls and sources"
        )

        parser.add_argument(
            "--session-id",
            help="Optional session identifier for tracking"
        )

        args = parser.parse_args()

        # Configure DSPy
        configure_dspy()

        # Create tools and grounding managers
        grounding_manager = GroundingManager()
        tools = create_tools(grounding_manager=grounding_manager)

        # Create ReAct agent
        react_agent = create_react_agent(tools)

        print(f"🤖 Gathering information for: {args.question}")
        print("=" * 60)

        # Add README.md as context if it exists
        readme_content = ""
        readme_path = "README.md"
        if os.path.exists(readme_path):
            try:
                with open(readme_path, 'r', encoding='utf-8') as f:
                    readme_content = f.read()
                print("📖 Adding README.md as context...")
            except Exception as e:
                print(f"⚠️  Could not read README.md: {e}")
        

        # Run the agent
        result = react_agent(question=args.question, context=readme_content)

        # Print the answer
        print("\n💡 **Answer:**")
        print(result.answer)

        # Print grounding information if verbose
        if args.verbose:
            print_grounding_info(grounding_manager, verbose=True)

        print("\n✅ Information gathering completed successfully")

    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during information gathering: {e}")
        print("\nTroubleshooting tips:")
        print("• Make sure all required API keys are set")
        print("• Check that codegiant.sh is installed and in PATH")
        print("• Verify VertexAI credentials are valid")
        print("• Try running with --verbose for more details")

        # Print full traceback in verbose mode
        if len(sys.argv) > 1 and ("--verbose" in sys.argv or "-v" in sys.argv):
            import traceback
            print("\nFull error traceback:")
            traceback.print_exc()

        sys.exit(1)


if __name__ == "__main__":
    main()
```

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
    model=f'vertex_ai/{classifier_lm_model_name}',
    reasoning_effort=classifier_lm_reasoning_effort # other options are Literal["low", "medium", "high"]
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
        print(result)
```

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
    print(f"Optimized accuracy: {optimized_score_int}%")
```

## File: `dspy_agent_expert_ai.py`
```
import dspy
from typing import Any
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
    # Who you are 
    You are an Agent Coding Assistant AI.
    You can answer questions, search for information, AND perform coding tasks by reading files, browsing directories, and executing safe commands.

    # About the conversation history
    When an answer to a request can be derived from the conversation history, do not use tools to answer the question.
    The user will sometimes ask clarifying questions. Answer these questions as best as you can from the conversation history.
    The user will sometimes ask followup questions. Answer these questions as best as you can from the conversation history.
    The user will sometimes ask you to write the analysis results to a file. Take the already gathered information from the conversation history and write it to a file.

    # When to use tools
    If you cannot answer the question from the conversation history, then use tools to answer the question.

    # Very important rules and guidelines to follow

    ## Some guides on when to use which  tools

    ### Codebase Interaction Guidelines:

    -   **For simple text searches within the codebase (e.g., finding specific keywords, function names, or patterns across files):**
        -   Use `CodeTermSearch` which efficiently searches both tracked and untracked files while respecting .gitignore.
        -   *Example:* `CodeTermSearch` with `term="your_keyword"`
        -   *For specific file types:* `CodeTermSearch` with `term="your_keyword", file_types=["py", "md"]`
        -   *With limited results:* `CodeTermSearch` with `term="your_keyword", max_results=20`

    -   **For complex, semantic questions about the codebase (e.g., "How does the authentication flow work?", "Where is the main data processing logic located?", or understanding relationships between different parts of the code):**
        -   Use `GiantAskCodebase`. This tool is designed for higher-level, contextual understanding and analysis of the codebase.

    -   **For reviewing recent code changes or understanding differences between versions:**
        -   Use `GiantReviewGitDiff`.

    -   **For reading the content of a specific file:**
        -   Use `ReadFile`.

    -   **For listing the contents of a directory:**
        -   Use `ListDirectory`.

    -   **For writing content to a file:**
        -   Use `WriteFile`.

    ### General Information Retrieval & Action Guidelines:

    -   **For general web research and gathering up-to-date information:**
        -   Use `WebSearchTavilyAgent`.

    -   **For querying internal knowledge bases or specific documentation:**
        -   Use `InternalKnowledgeAgent`.

    -   **For executing general shell commands not related to code search (e.g., checking system status, running scripts):**
        -   Use `RestrictedShell`.    
        
    ## Path of See, think, act
    Please always follow the path: See, think, act!
    Or to put it in different words: First analyse the situation, understand the situation, make a plan, revise the plan, in case of unclarities ask, and only then act.
    Do not do workarounds or hacks just to get things done. We are working professionally here.
    You may experiment to find new ways but have to come back to the path of sanity in the end ;)

    ## Complexity
    If the request is a bit more challenging or you seem stuck use the MCP sequential-thinking.

    ## Need more information ?
    And also think about searching the web with MCP perplexity and your internal web search.

    ## Web Research

    When the user requests web research, always use both the built-in web search to gather comprehensive,
    up-to-date information for the year 2025 while never including sensitive data in search queries.

    """

    # AVAILABLE TOOLS (use as needed for the task):

    # ## INFORMATION RETRIEVAL TOOLS:
    # 1. **InternalKnowledgeAgent** - Search internal knowledge base
    #    - Use for questions about existing documentation/knowledge
    #    - Check chat history first to avoid duplicate searches
    
    # 2. **WebSearchAgent** - Search the web 
    #    - Use when internal knowledge is insufficient
    #    - Great for current tech information, APIs, libraries

    # ## CODING & DEVELOPMENT TOOLS:
    # 3. **ReadFile** - Read any file contents
    #    - Use when user asks about specific files
    #    - Essential for code review, debugging, understanding codebases
    #    - Examples: "Read main.py", "Show me the config file", "What's in that error log?"
    
    # 4. **ListDirectory** - Browse directory contents
    #    - Use to explore project structure
    #    - Find files when user mentions directories or file patterns
    #    - Examples: "What files are in src/", "Show me the project structure"
    
    # 5. **RestrictedShell** - Execute safe commands (git, uv, pytest, ls, etc.)
    #    - Use for development tasks: version control, testing, package management
    #    - Examples: "git status", "uv run pytest", "ls -la"
    #    - IMPORTANT: Only safe, allowlisted commands are permitted
    
    # 6. **CodeTermSearch** - Search for terms/patterns in the codebase
    #    - Efficiently searches both tracked and untracked files while respecting .gitignore
    #    - Examples: "CodeTermSearch" with term="Assistant", "CodeTermSearch" with term="import", file_types=["py"]
    #    - Use this instead of grep for code searches

    # ## TOOL USAGE STRATEGY:
    # - **For coding questions**: Start by exploring with ListDirectory and ReadFile to understand the codebase
    # - **For debugging**: Read relevant files, check git status, run tests if needed  
    # - **For feature requests**: Examine existing code first, then implement
    # - **For project analysis**: Use directory listing and file reading to understand structure
    # - **For version control**: Use git commands to check status, history, branches
    # - **For testing**: Use pytest, mypy, ruff commands to run tests and checks
    # NOTE: If the user asks about conversation history and the history field contains previous messages, provide a summary based on that information. Do NOT say there is no history if the history field is populated.
    history: dspy.History = dspy.InputField(desc="IMPORTANT: In case this 'history' field is not populated but there are previous messages, use them as the history to answer the question.")
    question: str = dspy.InputField(desc="The input question from the user")
    answer: str = dspy.OutputField(desc="The answer to the user's question. Must be fulfilled throughly with the information from the tools or conversation history as appropriate.")


class AgentCodingAssistantAI(dspy.Module):
    def __init__(self, tools: list[dspy.Tool]):
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

## File: `dspy_agent_streaming_service.py`
```
from __future__ import annotations

import json
import asyncio
from typing import Tuple, Callable, Optional, AsyncGenerator, Dict, Any

import dspy
import dspy.streaming
from datetime import datetime

from dspy_agent_lm_vertexai import get_vertexai_lm
from dspy_agent_util_streaming_grounding_manager import StreamingGroundingManager
from dspy_agent_tool_streaming_internal_knowledge import StreamingInternalKnowledgeTool
from dspy_agent_tool_streaming_websearch_tavily import StreamingWebSearchToolTavily
from dspy_agent_tool_cgiant import GiantAskCodebaseTool, GiantReviewGitDiffTool
from dspy_agent_tool_lc_filesystem import LangChainReadFileTool, LangChainListDirectoryTool, LangChainWriteFileTool
from dspy_agent_tool_restricted_shell import RestrictedShellTool
from dspy_agent_tool_code_term_search import CodeTermSearchTool
from dspy_agent_expert_ai import AgentCodingAssistantAI
from dspy_constants import MODEL_NAME_GEMINI_2_5_FLASH, MODEL_NAME_GEMINI_2_5_PRO, MODEL_NAME_GEMINI_2_5_FLASH_LITE, MODEL_NAME_GEMINI_2_0_FLASH
from session_history_manager import SessionHistoryManager
from dspy.utils.callback import BaseCallback
from session_models import ToolCallRecord
from dspy_pricing_service import PricingService, SingleModelPricingService
from dspy_agent_tool_gemini import GeminiAskTool


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
            top_k=10,
            include_raw_content=True,
        )
        
        # Create filesystem tools for coding capabilities
        read_file_tool = LangChainReadFileTool(
            grounding_manager=self.grounding_manager,
        )
        list_directory_tool = LangChainListDirectoryTool(
            grounding_manager=self.grounding_manager,
        )
        write_file_tool = LangChainWriteFileTool(
            grounding_manager=self.grounding_manager,
        )
        
        # Create restricted shell tool for command execution
        restricted_shell_tool = RestrictedShellTool(
            grounding_manager=self.grounding_manager,
        )
        
        # Create code search tool for efficient term searching
        code_term_search_tool = CodeTermSearchTool(
            grounding_manager=self.grounding_manager,
        )

        giant_ask_codebase_tool = GiantAskCodebaseTool(self.grounding_manager)  # type: ignore[no-untyped-call]
        giant_review_git_diff_tool = GiantReviewGitDiffTool(self.grounding_manager)  # type: ignore[no-untyped-call]
        gemini_ask_tool = GeminiAskTool(self.grounding_manager)  # type: ignore[no-untyped-call]

        # Build list of tools for easy iteration
        tools: list[dspy.Tool] = [
            internal_tool,
            web_search_tool,
            read_file_tool,
            list_directory_tool,
            write_file_tool,
            restricted_shell_tool,
            code_term_search_tool,
            giant_ask_codebase_tool,
            giant_review_git_diff_tool,
            gemini_ask_tool,
        ]

        # Attach per-request DSPy callbacks to tools to emit progress via DSPy's native hook system
        if self.threadsafe_event_callback or self.event_callback:
            print("Attaching callbacks to tools ...")
            tool_callback = _ToolProgressCallback(
                event_callback=self.event_callback,
                threadsafe_event_callback=self.threadsafe_event_callback,
                tool_calls=self._tool_calls,
            )
            
            # Instance-level callbacks are honored by DSPy in addition to global callbacks
            for tool in tools:
                current_tool_name = tool.name if hasattr(tool, "name") else tool.__class__.__name__
                try:
                    tool.callbacks = getattr(tool, "callbacks", []) + [tool_callback]  # type: ignore[attr-defined]
                    print(f"Attached callbacks to tool {current_tool_name}")
                except Exception as e:
                    print(f"Error attaching callbacks to tool {current_tool_name}: {e}")

        # Initialize the main agent with streaming tools
        self.expert_ai = AgentCodingAssistantAI(tools=tools)
        
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
                            # Ensure 'current' is a number before adding
                            current_val = current if isinstance(current, (int, float)) else 0
                            result[k] = (current_val or 0) + (v or 0)
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
```

## File: `dspy_agent_tool_cgiant.py`
```
"""
Cgiant-based tools for the DSPy Agent.
This module provides tools that leverage codegiant.sh for codebase analysis and git diff reviews.
"""

import subprocess
import logging
import dspy
from typing import Optional
from dspy_agent_util_grounding_manager import GroundingManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GiantAskCodebaseTool(dspy.Tool):  # type: ignore[misc,no-any-unimported]
    """A dspy.Tool that asks questions about the entire codebase using codegiant.sh."""

    model_config = {"extra": "allow"}

    def __init__(self, grounding_manager: Optional[GroundingManager] = None) -> None:
        """
        Initialize the GiantAskCodebaseTool.

        Args:
            grounding_manager: Optional grounding manager for tracking tool usage
        """
        # Store grounding manager in closure to avoid Pydantic restrictions
        def ask_codebase(query: str) -> str:
            """
            Ask a question about the entire codebase using codegiant.sh.

            Args:
                query: The question to ask about the codebase

            Returns:
                The response from codegiant.sh or error message
            """
            logger.info(f"GiantAskCodebase tool received query: {query}")

            # Track the operation if grounding manager is available
            if grounding_manager:
                grounding_manager.add_query(f"Codebase Analysis: {query}")

            try:
                logger.info(f"Executing codegiant.sh with query: {query}")

                # Execute the codegiant.sh command
                cmd = ["codegiant.sh", "-F", "-y", "-t", query]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout for complex analysis
                    cwd=".",      # Run in current directory
                )

                # Format output
                output_parts = []
                if result.stdout:
                    output_parts.append(f"Cgiant Analysis:\n{result.stdout}")
                if result.stderr:
                    output_parts.append(f"Errors:\n{result.stderr}")
                if result.returncode != 0:
                    output_parts.append(f"Exit code: {result.returncode}")

                output = "\n".join(output_parts) if output_parts else "Cgiant analysis completed successfully (no output)"

                # Add source information to grounding
                if grounding_manager:
                    grounding_manager.add_source(
                        source_type='cgiant',
                        title=f'Codebase Query: {query}',
                        url=f'cgiant://{query}',
                        domain='local'
                    )

                logger.info(f"Cgiant analysis completed. Output length: {len(output)} chars")
                return output

            except subprocess.TimeoutExpired:
                error_msg = f"❌ Cgiant analysis timed out after 5 minutes for query: {query}"
                logger.error(error_msg)
                return error_msg

            except subprocess.CalledProcessError as e:
                error_msg = f"❌ Cgiant command failed with exit code {e.returncode}\nStdout: {e.stdout}\nStderr: {e.stderr}"
                logger.error(f"Cgiant command failed for query: {query} - {error_msg}")
                return error_msg

            except FileNotFoundError:
                error_msg = "❌ codegiant.sh not found. Please ensure codegiant.sh is installed and available in PATH."
                logger.error(error_msg)
                return error_msg

            except Exception as e:
                error_msg = f"❌ Unexpected error executing cgiant analysis: {str(e)}"
                logger.error(f"Unexpected error for query: {query} - {error_msg}")
                return error_msg

        # Initialize the parent dspy.Tool
        super().__init__(func=ask_codebase, name="GiantAskCodebase")


class GiantReviewGitDiffTool(dspy.Tool):  # type: ignore[misc,no-any-unimported]
    """A dspy.Tool that reviews git diff output using codegiant.sh."""

    model_config = {"extra": "allow"}

    def __init__(self, grounding_manager: Optional[GroundingManager] = None) -> None:
        """
        Initialize the GiantReviewGitDiffTool.

        Args:
            grounding_manager: Optional grounding manager for tracking tool usage
        """
        # Store grounding manager in closure to avoid Pydantic restrictions
        def review_git_diff() -> str:
            """
            Review the current git diff using codegiant.sh.

            Returns:
                The review response from codegiant.sh or error message
            """
            logger.info("GiantReviewGitDiff tool called")

            # Track the operation if grounding manager is available
            if grounding_manager:
                grounding_manager.add_query("Git Diff Code Review")

            try:
                # First, get the git diff output
                logger.info("Executing git diff")
                git_result = subprocess.run(
                    ["git", "diff"],
                    capture_output=True,
                    text=True,
                    timeout=30,  # 30 second timeout for git diff
                    cwd=".",      # Run in current directory
                )

                if git_result.returncode != 0:
                    error_msg = f"❌ Git diff failed with exit code {git_result.returncode}\nStderr: {git_result.stderr}"
                    logger.error(error_msg)
                    return error_msg

                git_diff_output = git_result.stdout.strip()

                if not git_diff_output:
                    msg = "ℹ️ No changes found in git diff (working directory is clean)"
                    logger.info(msg)
                    return msg

                logger.info(f"Git diff captured, length: {len(git_diff_output)} chars")

                # Now run codegiant.sh with the diff
                review_query = f"do a review on severe issues on the following git diff: {git_diff_output}"
                logger.info("Executing codegiant.sh with review query")

                cmd = ["codegiant.sh", "-F", "-y", "-t", review_query]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout for complex review
                    cwd=".",      # Run in current directory
                )

                # Format output
                output_parts = []
                if result.stdout:
                    output_parts.append(f"Cgiant Review:\n{result.stdout}")
                if result.stderr:
                    output_parts.append(f"Errors:\n{result.stderr}")
                if result.returncode != 0:
                    output_parts.append(f"Exit code: {result.returncode}")

                output = "\n".join(output_parts) if output_parts else "Cgiant review completed successfully (no output)"

                # Add source information to grounding
                if grounding_manager:
                    grounding_manager.add_source(
                        source_type='cgiant_review',
                        title='Git Diff Code Review',
                        url='cgiant://git_diff_review',
                        domain='local'
                    )

                logger.info(f"Cgiant review completed. Output length: {len(output)} chars")
                return output

            except subprocess.TimeoutExpired as e:
                cmd_name = "git diff" if "git" in str(e) else "codegiant.sh"
                error_msg = f"❌ {cmd_name} timed out after {'30 seconds' if 'git' in str(e) else '5 minutes'}"
                logger.error(error_msg)
                return error_msg

            except subprocess.CalledProcessError as e:
                cmd_name = "git diff" if "git" in str(e) else "codegiant.sh"
                error_msg = f"❌ {cmd_name} failed with exit code {e.returncode}\nStdout: {e.stdout}\nStderr: {e.stderr}"
                logger.error(error_msg)
                return error_msg

            except FileNotFoundError as e:
                missing_cmd = "git" if "git" in str(e) else "codegiant.sh"
                error_msg = f"❌ {missing_cmd} not found. Please ensure {missing_cmd} is installed and available in PATH."
                logger.error(error_msg)
                return error_msg

            except Exception as e:
                error_msg = f"❌ Unexpected error executing git diff review: {str(e)}"
                logger.error(f"Unexpected error - {error_msg}")
                return error_msg

        # Initialize the parent dspy.Tool
        super().__init__(func=review_git_diff, name="GiantReviewGitDiff")


# Test the tools if run directly
if __name__ == "__main__":
    print("🧪 Testing Cgiant Tools")

    # Test GiantAskCodebase
    print("\n--- Testing GiantAskCodebase Tool ---")
    ask_tool = GiantAskCodebaseTool()  # type: ignore[no-untyped-call]

    test_query = "What is the main purpose of this codebase?"
    print(f"Query: {test_query}")
    result = ask_tool(query=test_query)
    print(f"Result: {result[:300]}...")

    # Test GiantReviewGitDiff
    print("\n--- Testing GiantReviewGitDiff Tool ---")
    review_tool = GiantReviewGitDiffTool()  # type: ignore[no-untyped-call]

    result = review_tool()
    print(f"Result: {result[:300]}...")

    print("\n✅ Cgiant tools testing completed")
```

## File: `dspy_agent_tool_code_term_search.py`
```
"""
CodeTermSearch tool for the DSPy Agent.
This module provides efficient code searching across both tracked and untracked files
while respecting .gitignore patterns and preventing context overflow.
"""

import subprocess
import logging
import dspy
from typing import Optional, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CodeTermSearchTool(dspy.Tool):
    """
    A tool for searching terms/patterns in the codebase.
    
    Efficiently searches both git-tracked and untracked files while:
    - Respecting .gitignore patterns
    - Supporting file type filtering
    - Preventing context overflow with output limits
    - Providing clean, manageable results
    """

    model_config = {"extra": "allow"}
    
    def __init__(self, grounding_manager=None, default_max_results: int = 50, max_output_chars: int = 25000):
        """
        Initialize the CodeTermSearchTool.
        
        Args:
            grounding_manager: Optional grounding manager for tracking tool usage
            default_max_results: Default maximum number of result lines to return (default: 50)
            max_output_chars: Maximum output characters before truncation (default: 25000)
        """
        # Store grounding manager in closure to avoid Pydantic restrictions
        def search_code_term(
            term: str, 
            file_types: Optional[List[str]] = None, 
            max_results: int = default_max_results,
            case_sensitive: bool = False,
            show_line_numbers: bool = True
        ) -> str:
            """
            Search for a term or pattern in the codebase.
            
            Args:
                term: The search term or pattern to find
                file_types: Optional list of file extensions (e.g., ["py", "md", "js"])
                max_results: Maximum number of result lines to return (None uses constructor default)
                case_sensitive: Whether the search should be case sensitive (default: False)
                show_line_numbers: Whether to include line numbers in results (default: True)
                
            Returns:
                Search results as a formatted string
            """
            term = term.strip()
            # Use constructor default if max_results not specified
            logger.info(f"CodeTermSearch: Searching for '{term}' with file_types={file_types}, max_results={max_results}")
            
            # Track the operation if grounding manager is available
            if grounding_manager:
                file_types_str = f" (file types: {file_types})" if file_types else ""
                grounding_manager.add_query(f"Code search: '{term}'{file_types_str}")
            
            try:
                # Build the git ls-files command with optional file type filtering
                if file_types:
                    # Convert file extensions to glob patterns
                    patterns = [f"*.{ext.lstrip('.')}" for ext in file_types]
                    tracked_cmd = f"git ls-files {' '.join(patterns)}"
                    untracked_cmd = f"git ls-files --others --exclude-standard {' '.join(patterns)}"
                else:
                    tracked_cmd = "git ls-files"
                    untracked_cmd = "git ls-files --others --exclude-standard"
                
                # Combine tracked and untracked files
                files_cmd = f"({tracked_cmd}; {untracked_cmd})"
                
                # Build grep options
                grep_options = []
                if not case_sensitive:
                    grep_options.append("-i")
                if show_line_numbers:
                    grep_options.append("-n")
                
                grep_opts_str = " ".join(grep_options)
                
                # Complete search command with result limiting
                search_command = f'{files_cmd} | xargs grep {grep_opts_str} "{term}" 2>/dev/null | head -{max_results}'
                
                logger.info(f"Executing search command: {search_command}")
                
                # Execute the search
                result = subprocess.run(
                    search_command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,  # 30 second timeout
                    cwd=".",     # Run in current directory
                )
                
                # Process results
                if result.stdout:
                    output = result.stdout.strip()
                    
                    # Count actual results
                    lines = output.split('\n') if output else []
                    result_count = len(lines)
                    
                    # Apply safety truncation
                    if len(output) > max_output_chars:
                        truncated_output = output[:max_output_chars]
                        truncated_lines = len(truncated_output.split('\n'))
                        output = f"{truncated_output}\n\n[RESULTS TRUNCATED: Showing {truncated_lines:,} of {result_count:,} total matches]"
                    
                    # Format the final output
                    file_filter_info = f" (filtered to {file_types} files)" if file_types else ""
                    header = f"🔍 Found {result_count} matches for '{term}'{file_filter_info}:\n\n"
                    formatted_output = header + output
                    
                else:
                    # No results found
                    file_filter_info = f" in {file_types} files" if file_types else ""
                    formatted_output = f"🔍 No matches found for '{term}'{file_filter_info}"
                
                # Add source information to grounding
                if grounding_manager:
                    grounding_manager.add_source(
                        source_type='code_search',
                        title=f'Code search: {term}',
                        url=f'search://{term}',
                        domain='local'
                    )
                
                logger.info(f"Search completed. Output length: {len(formatted_output)} chars")
                return formatted_output
                
            except subprocess.TimeoutExpired:
                error_msg = f"❌ Code search for '{term}' timed out after 30 seconds"
                logger.error(error_msg)
                return error_msg
                
            except subprocess.CalledProcessError as e:
                error_msg = f"❌ Code search failed: {e}\nStdout: {e.stdout}\nStderr: {e.stderr}"
                logger.error(f"Search failed: {term} - {error_msg}")
                return error_msg
                
            except Exception as e:
                error_msg = f"❌ Unexpected error during code search: {str(e)}"
                logger.error(f"Unexpected error: {term} - {error_msg}")
                return error_msg
        
        # Initialize the parent dspy.Tool with a clear name and description
        super().__init__(
            func=search_code_term, 
            name="CodeTermSearch",
            desc="Search for terms/patterns in the codebase (both tracked and untracked files). Supports file type filtering and provides clean, limited results."
        )


# Test the tool if run directly
if __name__ == "__main__":
    print("🧪 Testing CodeTermSearch Tool")
    
    # Test with default settings
    print("\n--- Testing with default settings ---")
    search_tool = CodeTermSearchTool()
    
    # Test with custom settings
    print("\n--- Testing with custom settings (max_results=3, max_output_chars=500) ---")
    custom_search_tool = CodeTermSearchTool(default_max_results=3, max_output_chars=500)
    
    # Test searches
    test_searches = [
        {"term": "Assistant", "description": "Basic search for 'Assistant'", "tool": search_tool},
        {"term": "Assistant", "file_types": ["py"], "description": "Search in Python files only", "tool": search_tool},
        {"term": "import", "file_types": ["py"], "max_results": 5, "description": "Search for imports in Python (limited results)", "tool": search_tool},
        {"term": "import", "file_types": ["py"], "description": "Search with custom tool defaults", "tool": custom_search_tool},
    ]
    
    for test in test_searches:
        print(f"\n{'='*60}")
        print(f"Test: {test['description']}")
        print(f"{'='*60}")
        
        # Extract test parameters
        tool_to_use = test.pop('tool', search_tool)
        search_params = {k: v for k, v in test.items() if k not in ['description']}
        
        try:
            result = tool_to_use.func(**search_params)
            print(result)
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    print(f"\n{'='*60}")
    print("✅ CodeTermSearch tool testing completed")
```

## File: `dspy_agent_tool_gemini.py`
```
"""
Gemini-based tool for the DSPy Agent.
This module provides a tool that leverages the Google Gemini CLI to answer arbitrary prompts.
"""

import subprocess
import logging
import dspy
from typing import Optional
from dspy_agent_util_grounding_manager import GroundingManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeminiAskTool(dspy.Tool):  # type: ignore[misc,no-any-unimported]
    """A dspy.Tool that sends a prompt to the Google Gemini CLI and returns the response."""

    model_config = {"extra": "allow"}

    def __init__(self, grounding_manager: Optional[GroundingManager] = None) -> None:
        """Initialise the GeminiAskTool.

        Args:
            grounding_manager: Optional grounding manager for tracking tool usage.
        """

        def ask_gemini(prompt: str) -> str:
            """Send an arbitrary prompt to the Gemini CLI.

            Args:
                prompt: The prompt string to forward to the Gemini CLI.

            Returns:
                The raw output from the Gemini CLI (stdout/stderr combined) or an error message.
            """
            logger.info("GeminiAskTool received prompt: %s", prompt)

            # Track operation if grounding manager is available
            if grounding_manager:
                grounding_manager.add_query(f"Gemini Prompt: {prompt}")

            try:
                logger.info("Executing Gemini CLI with prompt: %s", prompt)
                cmd = [
                    "gemini",
                    "-p",
                    prompt,
                    "-y",  # Assume -y is a confirmation/yes flag analogous to the example
                ]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5-minute timeout similar to the cgiant tool
                    cwd=".",
                )

                # Assemble output
                output_parts = []
                if result.stdout:
                    output_parts.append(f"Gemini Response:\n{result.stdout}")
                if result.stderr:
                    output_parts.append(f"Errors:\n{result.stderr}")
                if result.returncode != 0:
                    output_parts.append(f"Exit code: {result.returncode}")

                output = (
                    "\n".join(output_parts)
                    if output_parts
                    else "Gemini command completed successfully (no output)"
                )

                if grounding_manager:
                    grounding_manager.add_source(
                        source_type="gemini",
                        title=f"Gemini Prompt: {prompt}",
                        url=f"gemini://{prompt}",
                        domain="local",
                    )

                logger.info("Gemini command finished. Output length: %d chars", len(output))
                return output

            except subprocess.TimeoutExpired:
                error_msg = (
                    f"❌ Gemini command timed out after 5 minutes for prompt: {prompt}"
                )
                logger.error(error_msg)
                return error_msg

            except subprocess.CalledProcessError as e:
                error_msg = (
                    f"❌ Gemini command failed with exit code {e.returncode}\nStdout: {e.stdout}\nStderr: {e.stderr}"
                )
                logger.error(error_msg)
                return error_msg

            except FileNotFoundError:
                error_msg = (
                    "❌ gemini CLI not found. Please ensure the Google Gemini CLI is installed and in PATH."
                )
                logger.error(error_msg)
                return error_msg

            except Exception as e:  # pragma: no cover
                error_msg = f"❌ Unexpected error executing Gemini command: {str(e)}"
                logger.error(error_msg)
                return error_msg

        # Initialise the parent dspy.Tool
        super().__init__(func=ask_gemini, name="GeminiAsk")


# Self-test block
if __name__ == "__main__":
    print("🧪 Testing GeminiAskTool")

    test_prompt = (
        "TASK_knowledge_file_assign_project_0_files.md and TASK_knowledge_file_assign_project_1_IDEA.md "
        "contain all project files and the task description. pls add your questions and a first rough plan "
        "on what needs to be adapted to the existing file called TASK_knowledge_file_assign_project_1_IDEA.md"
    )

    tool = GeminiAskTool()  # type: ignore[no-untyped-call]
    result = tool(prompt=test_prompt)
    print(result[:300] + ("…" if len(result) > 300 else ""))
```

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

## File: `dspy_agent_tool_lc_filesystem.py`
```
"""
LangChain-based filesystem tools for the DSPy Agent.
This module provides filesystem operations using LangChain's pre-built tools.
"""

import dspy
from langchain_community.tools import ReadFileTool, ListDirectoryTool, WriteFileTool


class LangChainReadFileTool(dspy.Tool):
    """A dspy.Tool wrapper for LangChain's ReadFileTool."""

    model_config = {"extra": "allow"}

    def __init__(self, grounding_manager=None):
        """
        Initialize the ReadFileTool wrapper.
        
        Args:
            grounding_manager: Optional grounding manager for tracking tool usage
        """
        # Store grounding manager in closure to avoid Pydantic restrictions
        def read_file_func(file_path: str) -> str:
            """Read the contents of a file from the filesystem."""
            print(f"--- Reading file: {file_path} ---")
            
            # Track the operation if grounding manager is available
            if grounding_manager:
                grounding_manager.add_query(f"Read file: {file_path}")
            
            try:
                # Use LangChain's ReadFileTool
                langchain_tool = ReadFileTool()
                result = langchain_tool.run(file_path)
                
                # Add source information to grounding
                if grounding_manager:
                    grounding_manager.add_source(
                        source_type='filesystem',
                        title=f'File: {file_path}',
                        url=f'file://{file_path}',
                        domain='local'
                    )
                
                return result
                
            except Exception as e:
                error_msg = f"Error reading file {file_path}: {str(e)}"
                print(f"❌ {error_msg}")
                return error_msg
        
        # Initialize the parent dspy.Tool
        super().__init__(func=read_file_func, name="ReadFileTool")


class LangChainListDirectoryTool(dspy.Tool):
    """A dspy.Tool wrapper for LangChain's ListDirectoryTool."""

    model_config = {"extra": "allow"}

    def __init__(self, grounding_manager=None):
        """
        Initialize the ListDirectoryTool wrapper.
        
        Args:
            grounding_manager: Optional grounding manager for tracking tool usage
        """
        # Store grounding manager in closure to avoid Pydantic restrictions
        def list_directory_func(directory_path: str) -> str:
            """List the contents of a directory."""
            print(f"--- Listing directory: {directory_path} ---")
            
            # Track the operation if grounding manager is available
            if grounding_manager:
                grounding_manager.add_query(f"List directory: {directory_path}")
            
            try:
                # Use LangChain's ListDirectoryTool
                langchain_tool = ListDirectoryTool()
                result = langchain_tool.run(directory_path)
                
                # Add source information to grounding
                if grounding_manager:
                    grounding_manager.add_source(
                        source_type='filesystem',
                        title=f'Directory: {directory_path}',
                        url=f'file://{directory_path}',
                        domain='local'
                    )
                
                return result
                
            except Exception as e:
                error_msg = f"Error listing directory {directory_path}: {str(e)}"
                print(f"❌ {error_msg}")
                return error_msg
        
        # Initialize the parent dspy.Tool
        super().__init__(func=list_directory_func, name="ListDirectoryTool")


class LangChainWriteFileTool(dspy.Tool):
    """A dspy.Tool wrapper for LangChain's WriteFileTool."""

    model_config = {"extra": "allow"}

    def __init__(self, grounding_manager=None):
        """
        Initialize the WriteFileTool wrapper.

        Args:
            grounding_manager: Optional grounding manager for tracking tool usage
        """
        # Store grounding manager in closure to avoid Pydantic restrictions
        def write_file_func(file_path: str, text: str, append: bool = False) -> str:
            """Write content to a file on the filesystem."""
            operation = "appending to" if append else "writing to"
            print(f"--- {operation.capitalize()} file: {file_path} ---")

            # Track the operation if grounding manager is available
            if grounding_manager:
                grounding_manager.add_query(f"Write file: {file_path}")

            try:
                # Use LangChain's WriteFileTool
                langchain_tool = WriteFileTool()
                result = langchain_tool.run({
                    "file_path": file_path,
                    "text": text,
                    "append": append
                })

                # Add source information to grounding
                if grounding_manager:
                    grounding_manager.add_source(
                        source_type='filesystem',
                        title=f'File: {file_path}',
                        url=f'file://{file_path}',
                        domain='local'
                    )

                success_msg = f"{'appended to' if append else 'wrote to'} file: {file_path} - returned result: {result}"
                print(f"✅ {success_msg}")
                return success_msg

            except Exception as e:
                error_msg = f"Error {'appending to' if append else 'writing to'} file {file_path}: {str(e)}"
                print(f"❌ {error_msg}")
                return error_msg

        # Initialize the parent dspy.Tool
        super().__init__(func=write_file_func, name="WriteFileTool")


# Test the tools if run directly
if __name__ == "__main__":
    print("🧪 Testing LangChain Filesystem Tools")
    
    # Test ReadFileTool
    read_tool = LangChainReadFileTool()
    print("\n--- Testing ReadFileTool ---")
    result = read_tool(file_path="TASK_add_coding_1_PLAN.md")
    print(f"Read result preview: {result[:200]}...")
    
    # Test ListDirectoryTool
    list_tool = LangChainListDirectoryTool()
    print("\n--- Testing ListDirectoryTool ---")
    result = list_tool(directory_path=".")
    print(f"Directory listing: {result}")

    # Test WriteFileTool
    write_tool = LangChainWriteFileTool()
    print("\n--- Testing WriteFileTool ---")
    test_content = "This is a test file created by LangChainWriteFileTool."
    result = write_tool(file_path="test_output.txt", text=test_content)
    print(f"Write result: {result}")

    # Test append functionality
    append_content = "\nThis is appended content."
    result = write_tool(file_path="test_output.txt", text=append_content, append=True)
    print(f"Append result: {result}")

    print("\n✅ Tool testing completed")
```

## File: `dspy_agent_tool_restricted_shell.py`
```
"""
Restricted shell tool for the DSPy Agent.
This module provides safe command-line execution with allowlisted commands for coding tasks.
"""

import subprocess
import logging
import dspy

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define allowed command prefixes and their descriptions
ALLOWED_COMMANDS = {
    # Version control
    "git": "Run Git commands",
    
    # Python/UV package management
    "uv": "Run UV commands",
    
    # File system operations (read-only)
    "ls": "List directory contents",
    "find": "Search for files and directories",
    "wc": "Word, line, character, and byte count",
    "head": "Output the first part of files",
    "tail": "Output the last part of files",
    "grep": "Search text using patterns",
    "cat": "Display file contents",
    
    # Process and system info (read-only)
    "ps": "Show running processes",
    "top": "Display running processes",
    "df": "Display filesystem disk space usage",
    "free": "Display memory usage",
    "whoami": "Display current user",
    "pwd": "Print working directory",
    "which": "Locate a command",
    "echo": "Display text",
    
    # Development tools
    "node": "Run Node.js",
    "npm": "Node.js package manager",
    "docker ps": "List Docker containers",
}

def _generate_allowed_commands_desc() -> str:
    """Generate a formatted description of allowed commands."""
    return "\n".join([f"- `{command}`: {description}" for command, description in ALLOWED_COMMANDS.items()])

SHELL_INSTRUCTIONS = f"""

## Restricted Shell Tool

### Allowed Command Prefixes
The shell tool only allows commands that start with specific prefixes:
{_generate_allowed_commands_desc()}

### Common Usage Patterns

#### Development Workflow:
- `uv run python script.py` (run Python scripts)
- `uv run pytest tests/` (run tests)
- `uv run mypy .` (run type checking)
- `uv run ruff check .` (run linting)
- `git status` (check repository status)
- `git diff` (see changes)

#### File Analysis:
- `ls -la` (detailed directory listing)
- `find . -name "*.py"` (find Python files)
- `grep -r "pattern" .` (search for patterns)
- `wc -l file.py` (count lines in file)
- `head -20 file.py` (show first 20 lines)

#### Project Management:
- `uv add package` (add dependency)
- `uv sync` (sync dependencies)
- `uv tree` (show dependency tree)

### Security Notes:
- Only predefined command prefixes are allowed
- No file modification commands (rm, mv, cp, etc.)
- No system administration commands
- All commands are logged for security audit
- Commands run in the current project directory

### Error Handling:
- Invalid commands return error messages
- Failed commands return exit codes and error output
- All execution is logged for debugging
"""


class RestrictedShellTool(dspy.Tool):
    """A dspy.Tool that executes allowlisted shell commands safely."""

    model_config = {"extra": "allow"}

    def __init__(self, grounding_manager=None, max_output_chars: int = 50000):
        """
        Initialize the RestrictedShellTool.
        
        Args:
            grounding_manager: Optional grounding manager for tracking tool usage
            max_output_chars: Maximum number of characters to return from command output (default: 50000)
        """
        # Store grounding manager and max_output_chars in closure to avoid Pydantic restrictions
        def execute_shell_command(command: str) -> str:
            """
            Execute a shell command if it's in the allowlist.
            
            Args:
                command: The command to execute
                
            Returns:
                The command output or error message
            """
            command = command.strip()
            logger.info(f"Shell tool received command: {command}")
            
            # Track the operation if grounding manager is available
            if grounding_manager:
                grounding_manager.add_query(f"Shell command: {command}")
            
            # Check if command is allowed
            if not any(command.startswith(allowed_prefix) for allowed_prefix in ALLOWED_COMMANDS.keys()):
                error_msg = f"❌ Command '{command}' not allowed!\n\nAllowed command prefixes:\n{_generate_allowed_commands_desc()}"
                logger.error(f"Blocked unauthorized command: {command}")
                return error_msg
            
            try:
                logger.info(f"Executing allowed command: {command}")
                
                # Execute the command with security measures
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,  # 30 second timeout
                    cwd=".",     # Run in current directory
                )
                
                # Format output
                output_parts = []
                if result.stdout:
                    output_parts.append(f"Output:\n{result.stdout}")
                if result.stderr:
                    output_parts.append(f"Errors:\n{result.stderr}")
                if result.returncode != 0:
                    output_parts.append(f"Exit code: {result.returncode}")
                
                output = "\n".join(output_parts) if output_parts else "Command completed successfully (no output)"
                
                # SAFETY: Truncate massive outputs to prevent context overflow
                if len(output) > max_output_chars:
                    original_length = len(output)
                    truncated_output = output[:max_output_chars]
                    lines_count = output.count('\n')
                    truncated_lines = truncated_output.count('\n') 
                    output = f"{truncated_output}\n\n[OUTPUT TRUNCATED: {original_length:,} total chars, {lines_count:,} total lines, showing first {truncated_lines:,} lines]"
                
                # Add source information to grounding
                if grounding_manager:
                    grounding_manager.add_source(
                        source_type='shell',
                        title=f'Command: {command}',
                        url=f'shell://{command}',
                        domain='local'
                    )
                
                logger.info(f"Command completed. Output length: {len(output)} chars")
                return output
                
            except subprocess.TimeoutExpired:
                error_msg = f"❌ Command '{command}' timed out after 30 seconds"
                logger.error(error_msg)
                return error_msg
                
            except subprocess.CalledProcessError as e:
                error_msg = f"❌ Command failed with exit code {e.returncode}\nStdout: {e.stdout}\nStderr: {e.stderr}"
                logger.error(f"Command failed: {command} - {error_msg}")
                return error_msg
                
            except Exception as e:
                error_msg = f"❌ Unexpected error executing command: {str(e)}"
                logger.error(f"Unexpected error: {command} - {error_msg}")
                return error_msg
        
        # Initialize the parent dspy.Tool
        super().__init__(func=execute_shell_command, name="RestrictedShell")


# Test the tool if run directly
if __name__ == "__main__":
    print("🧪 Testing Restricted Shell Tool")
    
    shell_tool = RestrictedShellTool()
    
    # Test allowed commands
    test_commands = [
        "ls -la",
        "pwd",
        "echo 'Hello World'",
        "uv --version",
        "git status",
        # This should be blocked
        "rm -rf /", 
    ]
    
    for cmd in test_commands:
        print(f"\n--- Testing command: {cmd} ---")
        result = shell_tool(command=cmd)
        print(f"Result: {result[:200]}...")
    
    print("\n✅ Shell tool testing completed")
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
    
    def forward(self, query: str) -> dspy.Prediction:
        query_classification = self.classifier_credentials_passwords(classify_input=query).classification
        if query_classification != "safe":
            print(f"WebSearchTavilyModule: Query contains exposed credentials or passwords. Classification: {query_classification}.\nQuery: {query}")
            return dspy.Prediction(answer=f"I'm sorry, I can't answer that question because it contains exposed credentials or passwords. Classification: {query_classification}")
        
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
        return self.model_name
```

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
Simple server startup script for the Agent Coding Assistant API.
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
    print("🚀 Starting Agent Coding Assistant API Server")
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
Simple test client for the Agent Coding Assistant WebSocket API.
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

## File: `web/app.js`
```
/* eslint-env browser */
/* global io */

const DEBUG = false;

// --- Constants and Global Variables ---
let numRequestsInProgress = 0;
let querySendInProgress = false;
let chatFetchInProgress = false;
let toolUseFetchInProgress = false;
let messageInput = null; // Declare messageInput globally
const marked = new showdown.Converter({ simplifiedAutoLink: true, tables: true, strikethrough: true });

// Socket.IO connection
let socket = null;
let isConnected = false;

// Track total cost and tokens
const totalTokens = 0;
const totalCost = 0;
const SESSION_HISTORY_KEY = 'sessionHistory';

// Track tool use reporting
let previousToolUseContent = '';
let lastReportedToolUseTimestamp = null;

const MODEL_DEFAULT_CATEGORY = 'medium';

function sanitizeModelCategory(modelCategory) {
  if (!['easy', 'medium', 'hard'].includes(modelCategory)) {
    return MODEL_DEFAULT_CATEGORY;
  }
  return modelCategory;
}

// --- WebSocket Connection Management ---
function initializeWebSocket() {
  if (socket) {
    socket.disconnect();
  }

  socket = io(); // Use current host automatically

  socket.on('connect', () => {
    isConnected = true;
    if (DEBUG) console.log('Connected to WebSocket server');
    updateConnectionStatus();
  });

  socket.on('disconnect', () => {
    isConnected = false;
    if (DEBUG) console.log('Disconnected from WebSocket server');
    updateConnectionStatus();
  });

  socket.on('connection_confirmed', (data) => {
    if (DEBUG) console.log('Connection confirmed:', data);
    showAlert('Connected to Agent Coding Assistant', 'success');
    
    // Request session history after connection is confirmed
    socket.emit('load_session_history', { session_id: getSessionIdFromUrlOrStore() });
  });

  // --- Streaming state & helpers ---
  let currentStreamingMessage = null;
  let streamingContent = '';

  function startStreamingBotMessage() {
    const chatMessages = document.getElementById('chatMessages');
    const timeObj = getCurrentTime();
    const shortTime = typeof timeObj === 'string' ? timeObj : timeObj.short;
    const fullTime = typeof timeObj === 'string' ? timeObj : timeObj.full;

    const messageHTML = `
      <div class="message-wrapper streaming-message">
          <div class="avatar-and-message">
              <div class="chat-avatar bot-avatar">AI</div>
              <div class="message bot-message">
                  <p class="streaming-content"></p>
                  <small class="clearfix">
                      <span class="metadata-info"></span>
                      <span class="time-info" title="${fullTime}">${shortTime}</span>
                  </small>
              </div>
          </div>
      </div>
    `;

    chatMessages.insertAdjacentHTML('beforeend', messageHTML);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    currentStreamingMessage = chatMessages.querySelector('.streaming-message:last-child');
    streamingContent = '';
  }

  function appendToStreamingMessage(chunk) {
    if (!currentStreamingMessage) return;
    streamingContent += chunk;
    const contentElement = currentStreamingMessage.querySelector('.streaming-content');
    if (contentElement) {
      contentElement.innerHTML = convertToSafeHtml(streamingContent);
    }
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function finalizeStreamingMessage(finalAnswer, modelName = null, tokenInfo = null) {
    if (!currentStreamingMessage) return;
    const contentElement = currentStreamingMessage.querySelector('.streaming-content');
    if (contentElement) {
      contentElement.innerHTML = convertToSafeHtml(finalAnswer);
    }

    // Populate metadata (model + tokens) if available
    try {
      const metadataSpan = currentStreamingMessage.querySelector('.metadata-info');
      const normalized = tokenInfo ? parseUsageMetadata(tokenInfo) : null;
      const model = modelName || (normalized && normalized.model) || localStorage.getItem('lastResponseModel') || '';

      if (normalized) {
        localStorage.setItem('lastResponseTokens', JSON.stringify(normalized));
        if (normalized.model) localStorage.setItem('lastResponseModel', normalized.model);
      }

      if (metadataSpan) {
        const modelHtml = model ? `<span class="model-info">${model}</span>` : '';
        let tokenInfoHtml = '';
        if (normalized && (normalized.prompt_tokens != null || normalized.completion_tokens != null)) {
          let tokenText = `(Tokens: ${normalized.prompt_tokens || 0} + ${normalized.completion_tokens || 0}`;
          const costStats = normalized.cost_statistics || {};
          const costVal = costStats.total_cost_llm_api_usd || costStats.total_cost || 0;
          if (costVal > 0) {
            tokenText += ` ($${Number(costVal).toFixed(3)})`;
          }
          tokenText += ')';
          tokenInfoHtml = `<span class="token-info">${tokenText}</span>`;
        }
        metadataSpan.innerHTML = `${modelHtml} ${tokenInfoHtml}`.trim();
      }
    } catch (e) {
      // Non-fatal
      if (DEBUG) console.warn('Failed to finalize metadata for streaming message', e);
    }

    currentStreamingMessage.classList.remove('streaming-message');
    currentStreamingMessage = null;
    streamingContent = '';
  }

  socket.on('question_start', (data) => {
    if (DEBUG) console.log('Question started:', data);
    // Clear chat messages for new response
    registerRequestInProgress();
  });

  socket.on('tool_start', (data) => {
    if (DEBUG) console.log('Tool started:', data);
    // Add tool use entry with normalized wording
    const q = (typeof data.query === 'string' && data.query) ? data.query : '';
    const text = q ? `Query is '${q}'` : (data.description || 'started');
    addToolUseEntry(data.tool, text, 'started');
  });

  socket.on('tool_progress', (data) => {
    if (DEBUG) console.log('Tool progress:', data);
    // Add tool progress entry to Tool Use History
    const progressMessage = data.message || data.status || 'in progress';
    const progressText = data.progress != null ? `${progressMessage} (${data.progress}%)` : progressMessage;
    addToolUseEntry(data.tool || 'tool', progressText, 'progress');
  });

  socket.on('tool_complete', (data) => {
    if (DEBUG) console.log('Tool completed:', data);
    // Prefer result_preview; format as requested
    const hasPreview = typeof data.result_preview === 'string' && data.result_preview.length > 0;
    const text = hasPreview ? `Completed - Result: ${data.result_preview}` : 'Completed';
    addToolUseEntry(data.tool, text, 'completed');
  });

  socket.on('tool_error', (data) => {
    if (DEBUG) console.log('Tool error:', data);
    // Show error in tool use
    addToolUseEntry(data.tool, `Error: ${data.error}`, 'error');
  });

  socket.on('answer_chunk', (data) => {
    if (DEBUG) console.log('Answer chunk received');
    // If this is the first chunk, render the user message (if pending) and start streaming container
    if (!currentStreamingMessage) {
      const lastUserMessage = messageInput && messageInput.dataset ? (messageInput.dataset.lastQuestion || '') : '';
      if (lastUserMessage) {
        renderUserMessage(lastUserMessage);
        delete messageInput.dataset.lastQuestion;
      }
      startStreamingBotMessage();
    }
    // Append chunk
    appendToStreamingMessage(data.chunk || '');
  });

  socket.on('grounding_update', (data) => {
    if (DEBUG) console.log('Grounding update:', data);
    // Handle grounding information updates
  });

  socket.on('answer_complete', (data) => {
    if (DEBUG) console.log('Answer complete:', data);

    // If we streamed, finalize the streaming message; otherwise fall back to full render
    if (currentStreamingMessage) {
      finalizeStreamingMessage(data.answer, null, data.usage_metadata || null);
    } else {
      const lastUserMessage = messageInput && messageInput.dataset ? (messageInput.dataset.lastQuestion || '') : '';
      if (lastUserMessage) {
        renderUserMessage(lastUserMessage);
        delete messageInput.dataset.lastQuestion;
      }
      // Normalize metadata and persist for rendering
      const normalized = data.usage_metadata ? parseUsageMetadata(data.usage_metadata) : null;
      if (normalized) {
        try {
          localStorage.setItem('lastResponseTokens', JSON.stringify(normalized));
          if (normalized.model) localStorage.setItem('lastResponseModel', normalized.model);
        } catch (e) {
          if (DEBUG) console.warn('Failed saving last response tokens/model', e);
        }
      }
      renderBotMessage(data.answer, null, normalized ? normalized.model : null, normalized || null);
    }
    
    // Update cost tracking
    if (data.usage_metadata) {
      updateCostFromUsageMetadata(data.usage_metadata);
    }
    
    unregisterRequestInProgress();
    querySendInProgress = false;
    
    // Clear input and reset textarea height
    messageInput.value = '';
    autoResizeTextarea(messageInput);
    
    // Focus back on the textarea
    messageInput.focus();
  });

  socket.on('session_history_loaded', (data) => {
    if (DEBUG) console.log('Session history loaded:', data);
    displaySessionHistory(data.history || []);
  });

  socket.on('error', (data) => {
    if (DEBUG) console.log('WebSocket error:', data);
    showAlert(`Error: ${data.message}`, 'error');
    unregisterRequestInProgress();
    querySendInProgress = false;
  });

  socket.on('question_cancelled', (data) => {
    if (DEBUG) console.log('Question cancelled:', data);
    showAlert('Question processing cancelled', 'info');
    unregisterRequestInProgress();
    querySendInProgress = false;
  });
}

function updateConnectionStatus() {
  // Update UI to reflect connection status
  if (isConnected) {
    document.body.classList.add('connected');
    document.body.classList.remove('disconnected');
  } else {
    document.body.classList.add('disconnected');
    document.body.classList.remove('connected');
  }
}

function displaySessionHistory(history) {
  if (DEBUG) console.log('Displaying session history:', history);
  
  const chatMessages = document.getElementById('chatMessages');
  if (!chatMessages) {
    console.warn('Chat messages container not found');
    return;
  }
  
  // Clear existing messages
  chatMessages.innerHTML = '';
  // Reset per-session cost/token totals before re-accumulating from history
  resetSessionCostData();
  // Clear tool history as we're reloading a session
  const toolUseHistory = document.getElementById('tool-use-history');
  if (toolUseHistory) {
    toolUseHistory.innerHTML = '';
    const emptyMessage = document.getElementById('tool-history-empty');
    if (emptyMessage) emptyMessage.style.display = 'block';
  }
  
  if (!history || history.length === 0) {
    if (DEBUG) console.log('No session history to display, showing welcome message');
    // Show welcome message if no history
    renderBotMessage('Hi! I\'m your Agent Coding Assistant.\n\nI can help you with:\n- Campaign setup and optimization\n- Bidding strategies and performance analysis\n- Google Ads best practices and recommendations\n- Troubleshooting campaign issues\n\nWhat are we gonna build today?');
    return;
  }
  
  // Collect all tools from all conversations for global sorting by newest first
  const allTools = [];
  history.forEach((entry, index) => {
    if (entry.tools && Array.isArray(entry.tools) && entry.tools.length > 0) {
      entry.tools.forEach((tool) => {
        const toolName = tool.name || 'tool';
        let text = '';
        if (tool.status === 'error' && tool.error) {
          const q = tool.input_summary ? `Query is '${tool.input_summary}'\n` : '';
          text = `${q}Error: ${tool.error}`.trim();
        } else if (tool.status === 'completed') {
          text = tool.result_preview ? `Completed - Result: ${tool.result_preview}` : 'Completed';
        } else {
          text = tool.input_summary ? `Query is '${tool.input_summary}'` : 'started';
        }
        // Prefer ended_at for completed/error, otherwise started_at
        const ts = tool.ended_at || tool.started_at || null;
        allTools.push({
          toolName,
          text,
          status: tool.status || 'started',
          timestamp: ts
        });
      });
    }
  });

  // Sort all tools globally by newest first (descending timestamp order)
  allTools.sort((a, b) => {
    const ta = a.timestamp ? new Date(a.timestamp).getTime() : 0;
    const tb = b.timestamp ? new Date(b.timestamp).getTime() : 0;
    return tb - ta; // Newest first
  });

  // Display each conversation pair
  history.forEach((entry, index) => {
    // Display user question
    renderUserMessage(entry.question);

    // Display bot answer with token/model info if available
    let normalized = null;
    if (entry.usage_metadata) {
      normalized = parseUsageMetadata(entry.usage_metadata);
    }
    renderBotMessage(entry.answer, null, normalized ? normalized.model : null, normalized || null);

    // Update cost information if available
    if (entry.usage_metadata) {
      updateCostFromUsageMetadata(entry.usage_metadata);
    }
  });

  // Add all tools to history in globally sorted order (newest first)
  if (allTools.length > 0) {
    // Ensure section visible
    const toolUseSection = document.getElementById('toolUseSection');
    if (toolUseSection) toolUseSection.style.display = 'block';

    // Add tools in sorted order (newest first)
    allTools.forEach((toolData) => {
      addToolUseEntry(toolData.toolName, toolData.text, toolData.status, toolData.timestamp, true);
    });
  }
  
  // Scroll to bottom
  chatMessages.scrollTop = chatMessages.scrollHeight;
  
  if (DEBUG) console.log(`Displayed ${history.length} conversation entries`);
}

// --- Tool Use History Management ---
function addToolUseEntry(toolName, input, status = 'started', timestamp = null, isHistoryLoad = false) {
  const toolUseHistory = document.getElementById('tool-use-history');
  const emptyMessage = document.getElementById('tool-history-empty');
  
  if (!toolUseHistory) return;
  
  // Show the tool use section
  const toolUseSection = document.getElementById('toolUseSection');
  if (toolUseSection) {
    toolUseSection.style.display = 'block';
  }
  
  // Hide empty message
  if (emptyMessage) {
    emptyMessage.style.display = 'none';
  }
  
  // Create timestamp
  const now = timestamp ? new Date(timestamp) : new Date();
  const formattedTimestamp = now.toLocaleTimeString();
  
  // Create status badge based on status
  let statusBadge = '';
  if (status === 'progress') {
    statusBadge = '<span class="tool-status-badge progress">●</span>';
  } else if (status === 'completed') {
    statusBadge = '<span class="tool-status-badge completed">✓</span>';
  } else if (status === 'error') {
    statusBadge = '<span class="tool-status-badge error">✗</span>';
  }

  // Create tool entry HTML
  const toolEntry = document.createElement('div');
  toolEntry.className = 'tool-entry';
  toolEntry.innerHTML = `
    <div class="tool-timestamp">${formattedTimestamp}</div>
    <div class="tool-bubble">
      <div class="tool-name">${toolName.toUpperCase()}${statusBadge}</div>
      <div class="tool-input">${input}</div>
    </div>
  `.trim();
  
  // Always insert in chronological order (newest first)
  // For live updates, prepend to maintain newest-first order
  // For history loading, append since tools are already sorted globally by newest first
  if (!isHistoryLoad) {
    // Live update: prepend to top (newest)
    toolUseHistory.insertBefore(toolEntry, toolUseHistory.firstChild);
  } else {
    // History loading: append since tools are pre-sorted by newest first
    toolUseHistory.appendChild(toolEntry);
  }
  
  // Limit to last 20 entries for live updates only
  if (!isHistoryLoad) {
    const entries = toolUseHistory.querySelectorAll('.tool-entry');
    if (entries.length > 20) {
      entries[entries.length - 1].remove();
    }
  }
}

// --- Sidebar collapse functions ---
function getSidebarCollapseState() {
  // Default to collapsed (true) if not set
  const storedValue = localStorage.getItem('sidebarCollapsed');
  return storedValue === null ? true : storedValue === 'true';
}

function setSidebarCollapseState(isCollapsed) {
  localStorage.setItem('sidebarCollapsed', isCollapsed.toString());
}

function toggleSidebar(forceOpen = false) {
  const sidebar = document.getElementById('settings-sidebar');
  const chatArea = document.getElementById('chat-area');
  const isCollapsed = sidebar.classList.contains('collapsed');
  
  // If forceOpen is true, we only want to expand (not toggle)
  // Only take action if sidebar is collapsed or we're not forcing open
  if (DEBUG) console.log('toggleSidebar', isCollapsed, forceOpen);
  if (isCollapsed || (!isCollapsed && !forceOpen)) {
    if (isCollapsed || forceOpen) {
      // Expand
      sidebar.classList.remove('collapsed');
      chatArea.classList.remove('col-md-12');
      chatArea.classList.add('col-md-9');
      setSidebarCollapseState(false);
    } else {
      // Collapse
      sidebar.classList.add('collapsed');
      chatArea.classList.remove('col-md-9');
      chatArea.classList.add('col-md-12');
      setSidebarCollapseState(true);
    }
  }
}

function applySidebarCollapseState() {
  const isCollapsed = getSidebarCollapseState();
  const sidebar = document.getElementById('settings-sidebar');
  const chatArea = document.getElementById('chat-area');
  
  // Temporarily disable transitions to prevent animation on page load
  document.body.classList.add('no-transition');
  
  if (isCollapsed) {
    sidebar.classList.add('collapsed');
    chatArea.classList.remove('col-md-9');
    chatArea.classList.add('col-md-12');
  } else {
    sidebar.classList.remove('collapsed');
    chatArea.classList.remove('col-md-12');
    chatArea.classList.add('col-md-9');
  }
  
  // Re-enable transitions after a brief delay
  setTimeout(() => {
    document.body.classList.remove('no-transition');
  }, 50);
}

// --- Toggle dark mode ---
function toggleDarkMode() {
  const darkModeToggle = document.getElementById('darkModeToggle');
  const toggleDarkModeBtn = document.getElementById('toggle-dark-mode-btn');
  
  // Toggle the state
  const isDarkMode = localStorage.getItem('darkMode') === 'true';
  const newDarkModeState = !isDarkMode;
  
  // Update localStorage
  localStorage.setItem('darkMode', newDarkModeState.toString());
  
  // Update checkbox state
  if (darkModeToggle) {
    darkModeToggle.checked = newDarkModeState;
  }
  
  // Update body class
  if (newDarkModeState) {
    document.body.classList.add('dark-mode');
  } else {
    document.body.classList.remove('dark-mode');
  }
  
  // Update button icon - show the opposite of current state (what will happen on next click)
  updateDarkModeButtonIcon();
}

// Update button icon based on current dark mode state
// Now shows what it will become when clicked (reversed logic)
function updateDarkModeButtonIcon() {
  const toggleDarkModeBtn = document.getElementById('toggle-dark-mode-btn');
  if (toggleDarkModeBtn) {
    const isDarkMode = localStorage.getItem('darkMode') === 'true';
    const iconElement = toggleDarkModeBtn.querySelector('i');
    if (iconElement) {
      // Reversed logic - show sun if in dark mode, moon if in light mode
      if (isDarkMode) {
        iconElement.classList.remove('bi-moon-fill');
        iconElement.classList.add('bi-sun-fill');
      } else {
        iconElement.classList.remove('bi-sun-fill');
        iconElement.classList.add('bi-moon-fill');
      }
    }
  }
}

// --- Alert function ---
function showAlert(message, type = 'error') {
  // Create alert element if it doesn't exist
  let alertElement = document.getElementById('clarity-alert');
  if (!alertElement) {
    alertElement = document.createElement('div');
    alertElement.id = 'clarity-alert';
    alertElement.style.position = 'fixed';
    alertElement.style.top = '80px';
    alertElement.style.right = '30px';
    alertElement.style.padding = '12px 20px';
    alertElement.style.borderRadius = '6px';
    alertElement.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';
    alertElement.style.zIndex = '1000';
    alertElement.style.maxWidth = '450px';
    alertElement.style.opacity = '0';
    alertElement.style.visibility = 'hidden';
    alertElement.style.pointerEvents = 'none';
    alertElement.style.transition = 'opacity 0.3s ease, visibility 0.3s ease';
    alertElement.style.fontSize = '16px';
    alertElement.style.display = 'flex';
    alertElement.style.alignItems = 'center';
    alertElement.style.justifyContent = 'space-between';
    document.body.appendChild(alertElement);
  }

  // Set background color based on type
  if (type === 'error') {
    alertElement.style.backgroundColor = 'rgba(220, 53, 69, 0.95)';
    alertElement.style.color = 'white';
    alertElement.style.borderLeft = '5px solid #dc3545';
  } else if (type === 'warning') {
    alertElement.style.backgroundColor = 'rgba(255, 193, 7, 0.95)';
    alertElement.style.color = 'black';
    alertElement.style.borderLeft = '5px solid #ffc107';
  } else if (type === 'info') {
    alertElement.style.backgroundColor = 'rgba(66, 165, 245, 0.95)';
    alertElement.style.color = 'white';
    alertElement.style.borderLeft = '5px solid #42a5f5';
  } else if (type === 'success') {
    alertElement.style.backgroundColor = 'rgba(25, 135, 84, 0.95)';
    alertElement.style.color = 'white';
    alertElement.style.borderLeft = '5px solid #198754';
  } 

  // Create content wrapper with improved close button functionality
  const contentHTML = `
    <div style="flex: 1">${message}</div>
    <button style="background: transparent; border: none; color: inherit; cursor: pointer; font-size: 18px; margin-left: 10px;" onclick="hideAlert();">×</button>
  `;

  // Update alert content and show
  alertElement.innerHTML = contentHTML;
  alertElement.style.opacity = '1';
  alertElement.style.visibility = 'visible';
  alertElement.style.pointerEvents = 'auto';

  // Auto-hide after 5 seconds
  setTimeout(() => {
    hideAlert();
  }, 5000);
}

// Helper function to properly hide the alert
function hideAlert() {
  const alertElement = document.getElementById('clarity-alert');
  if (alertElement) {
    alertElement.style.opacity = '0';
    alertElement.style.visibility = 'hidden';
    alertElement.style.pointerEvents = 'none';
  }
}

// --- Request tracking functions ---
function registerRequestInProgress() {
  numRequestsInProgress++;
  document.body.classList.add('loading');
  // You could add a loading indicator here
}

function unregisterRequestInProgress() {
  numRequestsInProgress--;
  if (numRequestsInProgress <= 0) {
    document.body.classList.remove('loading');
    numRequestsInProgress = 0;
  }
}

// --- Session and Password Management ---
function getSessionIdFromUrlOrStore() {
  // First try to get from URL
  const urlParams = new URLSearchParams(window.location.search);
  let sessionIdParam = urlParams.get('session_id');
    
  if (sessionIdParam) {
    // Check if the session ID contains _new_ and replace it with current date/time
    if (sessionIdParam.includes('_new_')) {
      const now = new Date();
      const formattedDateTime = now.getFullYear() + 
        String(now.getMonth() + 1).padStart(2, '0') + 
        String(now.getDate()).padStart(2, '0') + '_' +
        String(now.getHours()).padStart(2, '0') + 
        String(now.getMinutes()).padStart(2, '0') + 
        String(now.getSeconds()).padStart(2, '0');
      
      // Replace _new_ with the formatted date/time
      const newSessionId = sessionIdParam.replace('_new_', formattedDateTime);
      
      // Update the URL with the new session ID
      const url = new URL(window.location.href);
      url.searchParams.set('session_id', newSessionId);
      window.history.replaceState(null, '', url.toString());
      
      sessionIdParam = newSessionId;
      if (DEBUG) console.log('Replaced _new_ in session ID with current date/time:', newSessionId);
    }
    
    // Store in localStorage for persistence
    addOrUpdateSessionInHistory(sessionIdParam);
    localStorage.setItem('sessionId', sessionIdParam);
    return sessionIdParam;
  }
    
  // Fall back to localStorage
  let storedId = localStorage.getItem('sessionId');
  if (!storedId) {
    // Generate a default ID if none exists
    storedId = 'coding_assistant_' + Date.now();
    addOrUpdateSessionInHistory(storedId);
    localStorage.setItem('sessionId', storedId);
        
    // Update URL with the new session ID
    const url = new URL(window.location.href);
    url.searchParams.set('session_id', storedId);
    window.history.replaceState(null, '', url.toString());
  } else {
    addOrUpdateSessionInHistory(storedId); // Update last_seen_time for existing stored ID
  }
    
  return storedId;
}

function getModelCategoryFromStore() {
  return localStorage.getItem('selectedModel') || MODEL_DEFAULT_CATEGORY;
}

function setModelCategoryInStore(modelCategory) {
  localStorage.setItem('selectedModel', modelCategory);
}

// --- URL parameter handling functions ---
function getUrlParameter(name) {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get(name);
}

// --- Auto-query functionality ---
let autoQueryProcessed = false;

function processAutoQuery() {
  // Only process once per page load
  if (autoQueryProcessed) {
    return;
  }
  
  const queryParam = getUrlParameter('query');
  if (!queryParam) {
    return;
  }
  
  // Mark as processed to prevent multiple executions
  autoQueryProcessed = true;
  
  try {
    // URL decode the query parameter
    const decodedQuery = decodeURIComponent(queryParam);
    
    // Get the input field
    if (!messageInput) {
      console.error('Chat input field not found for auto-query');
      return;
    }
    
    // Only populate if the input field is empty (don't overwrite user input)
    if (messageInput.value.trim() === '') {
      messageInput.value = decodedQuery;
      autoResizeTextarea(messageInput);
      
      // Remove the query parameter from URL to prevent re-execution
      const url = new URL(window.location.href);
      url.searchParams.delete('query');
      window.history.replaceState(null, '', url.toString());
      
      // Show a brief message that auto-query was applied
      showAlert('Auto-submitting query from URL...', 'info');
      
      // Wait a brief moment then auto-submit
      setTimeout(() => {
        sendQuery();
      }, 500);
    }
  } catch (error) {
    console.error('Error processing auto-query:', error);
    showAlert('Error processing query from URL: ' + error.message, 'error');
  }
}

// --- Session ID handling functions ---
function incrementSessionId() {
  const sessionId = document.getElementById('session-id').value.trim();
  
  // Check if the session ID ends with a number
  const match = sessionId.match(/^(.*?)(\d+)$/);
  
  if (match) {
    // Extract the prefix and the numeric part
    const prefix = match[1];
    const numericPart = parseInt(match[2], 10);
    
    // Increment the numeric part
    const newNumericPart = numericPart + 1;
    
    // Create the new session ID
    const newSessionId = prefix + newNumericPart;
    
    // Update the session ID in localStorage
    addOrUpdateSessionInHistory(newSessionId);
    localStorage.setItem('sessionId', newSessionId);
    
    // Update the URL and reload the page
    const url = new URL(window.location.href);
    url.searchParams.set('session_id', newSessionId);
    window.location.href = url.toString();
  } else {
    // Show error message if the session ID doesn't end with a number
    showAlert('Session ID must end with a number to increment it');
  }
}

// --- Convert markdown to HTML ---
function convertToSafeHtml(aiOrToolAnswer) {
  if (aiOrToolAnswer.includes('": "') && aiOrToolAnswer.includes('{') && aiOrToolAnswer.includes('}')) {
    if (DEBUG) console.log('toJson');
    aiOrToolAnswer = '```json\n' + aiOrToolAnswer.replaceAll('\\n', '\n') + '\n```';
  } else if (aiOrToolAnswer.includes('<rss')) {
    if (DEBUG) console.log('toXml');
    aiOrToolAnswer = '```xml\n' + aiOrToolAnswer.replaceAll('\\n', '\n') + '\n```';
  } else if (aiOrToolAnswer.includes('</style>')) {
    if (DEBUG) console.log('toHtml');
    aiOrToolAnswer = '```html\n' + aiOrToolAnswer.replaceAll('\\n', '\n') + '\n```';
  }
    
  let answerHtml = marked.makeHtml(aiOrToolAnswer);
  if (answerHtml.startsWith('<p>') && answerHtml.endsWith('</p>')) {
    answerHtml = answerHtml.substring(3, answerHtml.length - 4);
  }
  answerHtml = answerHtml.replace(/(<a\s+href="[^"]*")/g, '$1 target="_blank" rel="noopener noreferrer"');
  return answerHtml;
}

// --- Chat Message Rendering ---
function renderBotMessage(message, timestamp = null, modelName = null, tokenInfo = null) {
  const chatMessages = document.getElementById('chatMessages');
  const timeObj = timestamp || getCurrentTime();
  // Support both old format (string) and new format (object with short and full properties)
  const shortTime = typeof timeObj === 'string' ? timeObj : timeObj.short;
  const fullTime = typeof timeObj === 'string' ? timeObj : timeObj.full;
  
  // Try to get model and token info from parameters or localStorage if not provided
  const model = modelName || localStorage.getItem('lastResponseModel') || '';
  const tokens = tokenInfo || safeJsonParse(localStorage.getItem('lastResponseTokens'), {});
  
  if (DEBUG) console.log('converting bot message', message);
  // Convert markdown to HTML using the safe HTML converter
  const messageHtml = convertToSafeHtml(message);
  
  // Create token info HTML if available
  let tokenInfoHtml = '';
  if (tokens && (tokens.prompt_tokens || tokens.completion_tokens)) {
    let tokenText = `(Tokens: ${tokens.prompt_tokens || 0} + ${tokens.completion_tokens || 0}`;
    if (tokens.cost_statistics) {
      const cost = tokens.cost_statistics.total_cost_llm_api_usd || tokens.cost_statistics.total_cost || 0;
      if (cost > 0) {
        tokenText += ` ($${cost.toFixed(3)})`;
      }
    }
    tokenText += ')';
    tokenInfoHtml = `<span class="token-info">${tokenText}</span>`;
  }
  
  // Create model info HTML if available
  const modelInfoHtml = model ? `<span class="model-info">${model}</span>` : '';
  
  const messageHTML = `
    <div class="message-wrapper">
        <div class="avatar-and-message">
            <div class="chat-avatar bot-avatar">AI</div>
            <div class="message bot-message">
                <p>${messageHtml}</p>
                <small class="clearfix">
                    <span class="metadata-info">${modelInfoHtml} ${tokenInfoHtml}</span>
                    <span class="time-info" title="${fullTime}">${shortTime}</span>
                </small>
            </div>
        </div>
    </div>
    `;
  
  chatMessages.insertAdjacentHTML('beforeend', messageHTML);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function renderUserMessage(message, timestamp = null) {
  const chatMessages = document.getElementById('chatMessages');
  const timeObj = timestamp || getCurrentTime();
  // Support both old format (string) and new format (object with short and full properties)
  const shortTime = typeof timeObj === 'string' ? timeObj : timeObj.short;
  const fullTime = typeof timeObj === 'string' ? timeObj : timeObj.full;
    
  if (DEBUG) console.log('converting user message', message);
  // Convert markdown to HTML with proper newline handling
  let messageHtml = marked.makeHtml(message);
  if (messageHtml.startsWith('<p>') && messageHtml.endsWith('</p>')) {
    messageHtml = messageHtml.substring(3, messageHtml.length - 4);
  }
    
  const messageHTML = `
    <div class="message-wrapper user-message-wrapper">
        <div class="avatar-and-message">
            <div class="message user-message">
                <p>${messageHtml}</p>
                <small title="${fullTime}">${shortTime}</small>
            </div>
            <div class="chat-avatar user-avatar">U</div>
        </div>
    </div>
    `;
    
  chatMessages.insertAdjacentHTML('beforeend', messageHTML);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function getCurrentTime() {
  const now = new Date();
  const formattedTime = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  // Create a full timestamp for the title attribute
  const fullTimestamp = now.toLocaleString([], {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: 'numeric',
    minute: 'numeric',
    second: 'numeric'
  });
  return { short: formattedTime, full: fullTimestamp };
}

// --- Session and Cost Management ---
function getSessionTotalCost() {
  const sessionId = getSessionIdFromUrlOrStore();
  const storageKey = `sessionTotalCost_${sessionId}`;
  return parseFloat(localStorage.getItem(storageKey) || '0');
}

function getSessionTotalTokens() {
  const sessionId = getSessionIdFromUrlOrStore();
  const storageKey = `sessionTotalTokens_${sessionId}`;
  return parseInt(localStorage.getItem(storageKey) || '0');
}

function updateSessionTotalCost(cost) {
  const sessionId = getSessionIdFromUrlOrStore();
  const storageKey = `sessionTotalCost_${sessionId}`;
  // Fix floating point precision by multiplying by 1000 first
  const currentCost = Math.round(parseFloat(localStorage.getItem(storageKey) || '0') * 1000) / 1000;
  // Add with precise calculation
  const newCost = (Math.round((currentCost + cost) * 1000)) / 1000;
  localStorage.setItem(storageKey, newCost.toString());
  
  // Update UI
  const totalCostElement = document.getElementById('total-cost');
  if (totalCostElement) {
    totalCostElement.textContent = `$${newCost.toFixed(3)}`;
  }
  
  return newCost;
}

function updateSessionTotalTokens(tokens) {
  const sessionId = getSessionIdFromUrlOrStore();
  const storageKey = `sessionTotalTokens_${sessionId}`;
  const currentTokens = parseInt(localStorage.getItem(storageKey) || '0');
  const newTokens = currentTokens + tokens;
  localStorage.setItem(storageKey, newTokens.toString());
  
  // Update UI
  const totalTokensElement = document.getElementById('total-tokens');
  if (totalTokensElement) {
    totalTokensElement.textContent = `${newTokens.toLocaleString()} tokens`;
  }
  
  return newTokens;
}

function loadSessionCostData() {
  const sessionId = getSessionIdFromUrlOrStore();
  const costStorageKey = `sessionTotalCost_${sessionId}`;
  const tokensStorageKey = `sessionTotalTokens_${sessionId}`;
  
  // Fix floating point precision by multiplying by 1000 first
  const cost = Math.round(parseFloat(localStorage.getItem(costStorageKey) || '0') * 1000) / 1000;
  const tokens = parseInt(localStorage.getItem(tokensStorageKey) || '0');
  
  // Update UI
  const totalCostElement = document.getElementById('total-cost');
  const totalTokensElement = document.getElementById('total-tokens');
  
  if (totalCostElement) {
    totalCostElement.textContent = `$${cost.toFixed(3)}`;
  }
  
  if (totalTokensElement) {
    totalTokensElement.textContent = `${tokens.toLocaleString()} tokens`;
  }
  
  return { cost, tokens };
}

function updateCostFromUsageMetadata(usageMetadata) {
  const normalized = parseUsageMetadata(usageMetadata);
  if (!normalized) return;
  const prompt = Number(normalized.prompt_tokens || 0);
  const completion = Number(normalized.completion_tokens || 0);
  const totalNewTokens = prompt + completion;
  if (totalNewTokens > 0) updateSessionTotalTokens(totalNewTokens);
  const costStats = normalized.cost_statistics || {};
  const costVal = costStats.total_cost_llm_api_usd || costStats.total_cost || 0;
  if (costVal && Number(costVal) > 0) updateSessionTotalCost(Number(costVal));
}

// Normalize various usage metadata shapes into a standard structure
function parseUsageMetadata(usageMetadata) {
  if (!usageMetadata || typeof usageMetadata !== 'object') return null;
  // Case 1: already flat
  if (typeof usageMetadata.prompt_tokens === 'number' || typeof usageMetadata.completion_tokens === 'number') {
    return {
      model: usageMetadata.model || '',
      prompt_tokens: usageMetadata.prompt_tokens || 0,
      completion_tokens: usageMetadata.completion_tokens || 0,
      total_tokens: usageMetadata.total_tokens || ((usageMetadata.prompt_tokens || 0) + (usageMetadata.completion_tokens || 0)),
      cost_statistics: usageMetadata.cost_statistics || null,
    };
  }

  // Case 2: nested under model key(s), e.g., { "vertex_ai/gemini-2.5-flash": { ... } }
  const keys = Object.keys(usageMetadata);
  for (let i = 0; i < keys.length; i++) {
    const k = keys[i];
    const v = usageMetadata[k];
    if (v && typeof v === 'object' && (typeof v.prompt_tokens === 'number' || typeof v.completion_tokens === 'number' || typeof v.total_tokens === 'number')) {
      return {
        model: k,
        prompt_tokens: v.prompt_tokens || 0,
        completion_tokens: v.completion_tokens || 0,
        total_tokens: v.total_tokens || ((v.prompt_tokens || 0) + (v.completion_tokens || 0)),
        cost_statistics: v.cost_statistics || usageMetadata.cost_statistics || null,
      };
    }
  }

  // Case 3: unknown shape
  return null;
}

// Reset per-session totals to zero and update UI
function resetSessionCostData() {
  const sessionId = getSessionIdFromUrlOrStore();
  const costStorageKey = `sessionTotalCost_${sessionId}`;
  const tokensStorageKey = `sessionTotalTokens_${sessionId}`;
  try {
    localStorage.setItem(costStorageKey, '0');
    localStorage.setItem(tokensStorageKey, '0');
  } catch (e) {
    if (DEBUG) console.warn('Failed resetting session cost data', e);
  }
  const totalCostElement = document.getElementById('total-cost');
  const totalTokensElement = document.getElementById('total-tokens');
  if (totalCostElement) totalCostElement.textContent = '$0.000';
  if (totalTokensElement) totalTokensElement.textContent = '0 tokens';
}

// --- Core API functions ---
async function sendQuery() {
  if (querySendInProgress) {
    if (DEBUG) console.log('Query already in progress');
    return;
  }
    
  const messageInput = document.querySelector('.chat-input-area .form-control');
  const query = messageInput.value.trim();
    
  if (query === '') {
    showAlert('Please enter a message');
    return;
  }
  
  if (!isConnected) {
    showAlert('Not connected to server. Please refresh the page.', 'error');
    return;
  }

  // Store the question for rendering later
  messageInput.dataset.lastQuestion = query;
  
  // Get the selected model from the dropdown
  const modelSelect = document.getElementById('model-select');
  const selectedModelCategory = sanitizeModelCategory(modelSelect.value);
  
  // Store the selected model in localStorage
  setModelCategoryInStore(selectedModelCategory);

  try {
    querySendInProgress = true;
    
    // Send question via WebSocket
    socket.emit('ask_question', {
      question: query,
      model_category: selectedModelCategory,
      session_id: getSessionIdFromUrlOrStore()
    });

  } catch (e) {
    console.error('Error in sendQuery:', e);
    showAlert('Error sending message: ' + e.message);
    unregisterRequestInProgress();
    querySendInProgress = false;
  }
}

// --- Session initialization function ---
async function initSession() {
  const sessionIdField = document.getElementById('session-id');
  const sessionId = sessionIdField.value.trim();
  
  if (sessionId === '') {
    showAlert('Please enter a session ID');
    return;
  }
  
  // Get current values to compare
  const currentStoredSessionId = localStorage.getItem('sessionId');
  const urlParams = new URLSearchParams(window.location.search);
  const currentSessionIdInUrl = urlParams.get('session_id');
  
  // Check if anything actually changed
  const needsUpdate = (sessionId !== currentStoredSessionId) || (sessionId !== currentSessionIdInUrl);
  
  if (needsUpdate) {
    // Update session ID in localStorage
    localStorage.setItem('sessionId', sessionId);
    
    // Check if URL needs to be updated
    if (currentSessionIdInUrl !== sessionId) {
      // Update URL with session ID and reload
      const url = new URL(window.location.href);
      url.searchParams.set('session_id', sessionId);
      
      window.location.href = url.toString();
      return; // Stop execution, page will reload
    }
  }
  
  // Clear chat for new session
  document.getElementById('chatMessages').innerHTML = '';
  
  // Load session cost data
  loadSessionCostData();
}

// --- Text area auto-resize function ---
function autoResizeTextarea(textarea) {
  // Reset height to auto to calculate the new height
  textarea.style.height = 'auto';
  
  // Set new height based on scrollHeight (with a min-height of one row)
  const newHeight = Math.max(textarea.scrollHeight, parseInt(window.getComputedStyle(textarea).lineHeight, 10));
  
  // Limit the max height
  const maxHeight = 100;
  textarea.style.height = Math.min(newHeight, maxHeight) + 'px';
  
  // Show/hide scrollbar based on content height
  textarea.style.overflowY = newHeight > maxHeight ? 'auto' : 'hidden';
}

// --- Session History Modal ---
function populateSessionHistoryModal() {
  const history = getSessionHistory();
  const listElement = document.getElementById('sessionHistoryList');
  if (!listElement) return;

  // Sort by last_seen_time descending
  history.sort((a, b) => new Date(b.last_seen_time) - new Date(a.last_seen_time));

  listElement.innerHTML = ''; // Clear existing items

  if (history.length === 0) {
    const li = document.createElement('li');
    li.className = 'list-group-item';
    li.textContent = 'No session history recorded yet.';
    listElement.appendChild(li);
    return;
  }

  history.forEach(item => {
    const li = document.createElement('li');
    li.className = 'list-group-item';

    const link = document.createElement('a');
    const url = new URL(window.location.href);
    url.searchParams.set('session_id', item.session_id);
    link.href = url.toString();
    link.className = 'session-history-link';
    link.textContent = item.session_id;
    
    // Make links open in the same tab (more intuitive for session switching)
    link.addEventListener('click', function(e) {
      e.preventDefault();
      window.location.href = this.href;
    });

    const details = document.createElement('small');
    details.className = 'd-block text-muted mt-1';
    details.textContent = `Created: ${new Date(item.created_time).toLocaleString()} | Last Seen: ${new Date(item.last_seen_time).toLocaleString()}`;

    li.appendChild(link);
    li.appendChild(details);
    listElement.appendChild(li);
  });
}

// --- Initialization and Event Listeners ---
document.addEventListener('DOMContentLoaded', async () => {
  // Initialize sidebar collapse state
  applySidebarCollapseState();
  
  // Load session cost data
  loadSessionCostData();
  
  // Setup sidebar toggle button
  const toggleSidebarBtn = document.getElementById('toggle-sidebar-btn');
  if (toggleSidebarBtn) {
    toggleSidebarBtn.addEventListener('click', () => toggleSidebar());
  }
  
  // Initialize darkMode toggle
  const darkModeToggle = document.getElementById('darkModeToggle');
    
  // Set default for dark mode if not set
  let isDarkMode = localStorage.getItem('darkMode');
  if (isDarkMode === null) {
    isDarkMode = 'true';
    localStorage.setItem('darkMode', isDarkMode);
  }
  if (isDarkMode === 'true') {
    document.body.classList.add('dark-mode');
    if (darkModeToggle) {
      darkModeToggle.checked = true;
    }
  }
    
  // Listen for dark mode toggle changes
  if (darkModeToggle) {
    darkModeToggle.addEventListener('change', () => {
      if (darkModeToggle.checked) {
        document.body.classList.add('dark-mode');
        localStorage.setItem('darkMode', 'true');
      } else {
        document.body.classList.remove('dark-mode');
        localStorage.setItem('darkMode', 'false');
      }
      // Update the icon on the button
      updateDarkModeButtonIcon();
    });
  }
  
  // Set up the dark mode button
  const toggleDarkModeBtn = document.getElementById('toggle-dark-mode-btn');
  if (toggleDarkModeBtn) {
    toggleDarkModeBtn.addEventListener('click', toggleDarkMode);
    // Initialize button icon
    updateDarkModeButtonIcon();
  }
  
  // Initialize model selection from localStorage
  const modelSelect = document.getElementById('model-select');
  if (modelSelect) {
    const savedModelCategory = sanitizeModelCategory(getModelCategoryFromStore());
    setModelCategoryInStore(savedModelCategory);
    modelSelect.value = savedModelCategory;
    
    // Add event listener to save model changes
    modelSelect.addEventListener('change', function() {
      setModelCategoryInStore(sanitizeModelCategory(modelSelect.value));
    });
  }
  
  // Set up session history modal button and event
  const sessionHistoryBtn = document.getElementById('toggle-session-history-btn');
  const sessionHistoryModalElement = document.getElementById('sessionHistoryModal');
  if (sessionHistoryBtn && sessionHistoryModalElement) {
    // Using Bootstrap's event to populate modal just before it's shown
    sessionHistoryModalElement.addEventListener('show.bs.modal', function () {
      populateSessionHistoryModal();
      
      // Apply dark mode to the modal if needed
      const isDarkMode = localStorage.getItem('darkMode') === 'true';
      if (isDarkMode) {
        document.querySelectorAll('.modal-content, .list-group-item').forEach(element => {
          // Force dark mode classes to apply properly
          if (!element.classList.contains('dark-mode-element')) {
            element.classList.add('dark-mode-element');
          }
        });
      }
    });
  }
    
  // Set up help modal event for dark mode styling
  const helpModalElement = document.getElementById('helpModal');
  if (helpModalElement) {
    helpModalElement.addEventListener('show.bs.modal', function () {
      // Apply dark mode to the help modal if needed
      const isDarkMode = localStorage.getItem('darkMode') === 'true';
      if (isDarkMode) {
        // Ensure dark mode styling is applied to all modal elements
        const modalContent = this.querySelector('.modal-content');
        if (modalContent && !modalContent.classList.contains('dark-mode-applied')) {
          modalContent.classList.add('dark-mode-applied');
        }
      }
    });
  }
    
  // Initialize show LLM tool calls toggle
  const showLLMToolCalls = document.getElementById('showLLMToolCalls');
    
  // Set default for showLLMToolCalls if not set
  let showToolCalls = localStorage.getItem('showLLMToolCalls');
  if (showToolCalls === null) {
    showToolCalls = 'true';
    localStorage.setItem('showLLMToolCalls', showToolCalls);
  }
  if (showToolCalls === 'true') {
    showLLMToolCalls.checked = true;
    document.getElementById('toolUseSection').style.display = 'block';
  }
    
  // Listen for tool calls toggle changes
  showLLMToolCalls.addEventListener('change', () => {
    localStorage.setItem('showLLMToolCalls', showLLMToolCalls.checked);
    document.getElementById('toolUseSection').style.display = 
            showLLMToolCalls.checked ? 'block' : 'none';
  });
  
  // Initialize session ID from URL or localStorage
  const sessionIdField = document.getElementById('session-id');
  sessionIdField.value = getSessionIdFromUrlOrStore();
  
  // Add event listener for session ID field blur
  sessionIdField.addEventListener('blur', function() {
    const newSessionId = sessionIdField.value.trim();
    const currentSessionId = getSessionIdFromUrlOrStore();
    
    if (newSessionId) {
      // Only update and reload if the session ID has actually changed
      if (newSessionId !== currentSessionId) {
        addOrUpdateSessionInHistory(newSessionId);
        localStorage.setItem('sessionId', newSessionId);
        // Update URL with new session ID and reload page
        const url = new URL(window.location.href);
        url.searchParams.set('session_id', newSessionId);
        window.location.href = url.toString();
      }
      // If no change, do nothing
    } else {
      showAlert('Session ID cannot be empty.');
      // Revert to the previous value
      sessionIdField.value = currentSessionId;
    }
  });
  
  // Add event listener for increment button
  const incrementButton = document.getElementById('increment-button');
  if (incrementButton) {
    incrementButton.addEventListener('click', incrementSessionId);
  }
  
  // Setup chat functionality
  messageInput = document.querySelector('.chat-input-area .form-control');
  const sendButton = document.querySelector('.chat-input-area .btn');
    
  // Initialize textarea auto-resize
  autoResizeTextarea(messageInput);
  
  // Add input event for auto-resizing textarea as user types
  messageInput.addEventListener('input', function() {
    autoResizeTextarea(this);
  });
  
  // Event listeners for sending messages
  sendButton.addEventListener('click', sendQuery);
  
  // Updated keypress handler to handle Shift+Enter
  messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      if (e.shiftKey) {
        // Allow new line with Shift+Enter
        // The default behavior will add a new line
      } else {
        // Submit with Enter (no shift)
        e.preventDefault();
        sendQuery();
      }
    }
  });
  
  // Initialize WebSocket connection
  initializeWebSocket();
  
  // Welcome message will be handled by displaySessionHistory function
  
  // Process auto-query from URL if present (after everything is initialized)
  setTimeout(() => {
    processAutoQuery();
  }, 1500);
});

// Utility function to safely parse JSON
function safeJsonParse(jsonString, defaultValue = {}) {
  if (!jsonString) return defaultValue;
  try {
    return JSON.parse(jsonString);
  } catch (e) {
    console.error('Error parsing JSON:', e);
    return defaultValue;
  }
}

// --- Session History Management ---
function getSessionHistory() {
  try {
    const historyJson = localStorage.getItem(SESSION_HISTORY_KEY);
    return historyJson ? JSON.parse(historyJson) : [];
  } catch (e) {
    console.error('Error reading session history from localStorage:', e);
    return [];
  }
}

function saveSessionHistory(history) {
  try {
    localStorage.setItem(SESSION_HISTORY_KEY, JSON.stringify(history));
  } catch (e) {
    console.error('Error saving session history to localStorage:', e);
  }
}

function addOrUpdateSessionInHistory(sessionId) {
  if (!sessionId) return;

  const history = getSessionHistory();
  const now = new Date().toISOString();
  const existingSessionIndex = history.findIndex(item => item.session_id === sessionId);

  if (existingSessionIndex > -1) {
    history[existingSessionIndex].last_seen_time = now;
  } else {
    history.push({
      session_id: sessionId,
      created_time: now,
      last_seen_time: now
    });
  }
  saveSessionHistory(history);
}
```

## File: `web/index.html`
```
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Agent Coding Assistant</title>
    <link rel="icon" href="/static/favicon_google-ads.webp" />
    <!-- Include self-hosted Bootstrap CSS -->
    <link rel="stylesheet" href="/static/external/bootstrap-5.3.6-dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="/static/external/bootstrap-icons-1.13.1/bootstrap-icons.css">
    <style>
        /* Override Bootstrap code color */
        :root {
            --bs-code-color: #ff4081;
        }
        /* Minimal custom CSS for layout and dark mode */
        body {
            padding: 0;
            margin: 0;
            overflow: hidden; /* Prevent scrolling on the body */
            height: 100vh; /* Full viewport height */
            display: flex;
            flex-direction: column;
            transition: background-color 0.3s ease;
        }
        .container-fluid {
            flex-grow: 1; /* Allow container to take up remaining space */
            overflow-y: hidden; /* Prevent vertical scrolling on the container */
            padding: 0; /* Remove default container padding */
        }
        .row {
             height: 100%; /* Make the row take full height of the container */
             margin: 0; /* Remove default row margin */
        }
        .chat-area, .settings-sidebar {
            height: 100%; /* Make columns take full height of the row */
            display: flex;
            flex-direction: column;
            padding: 15px; /* Add some padding inside the columns */
        }
        .settings-sidebar {
            background-color: #e8f4f8;
            transition: width 0.3s ease, flex 0.3s ease, padding 0.3s ease, margin 0.3s ease;
        }
        .chat-area {
            /* background-color: #b7b7b7; */
            border-right: 1px solid #dee2e6;
            transition: width 0.3s ease, flex 0.3s ease;
        }
        .chat-header, .settings-header {
            flex-shrink: 0; /* Prevent headers from shrinking */
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #dee2e6;
        }
        .chat-messages {
            flex-grow: 1; /* Allow messages area to take up remaining space */
            overflow-y: auto; /* Enable scrolling for chat messages */
            display: flex;
            flex-direction: column;
            margin-bottom: 15px;
            padding: 10px;
        }
        .chat-input-area {
            flex-shrink: 0; /* Prevent input area from shrinking */
            display: flex;
            gap: 10px;
            padding-top: 10px;
            border-top: 1px solid #dee2e6;
        }
        .chat-input-area .form-control {
            border-radius: 20px;
            padding-left: 15px;
            padding-right: 15px;
            max-height: 100px;
            overflow-y: auto;
            resize: none;
        }
        .chat-input-area .btn {
            border-radius: 50%;
            width: 40px;
            height: 40px;
            padding: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            align-self: flex-end;
        }
        .settings-section {
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 1px solid #dee2e6;
        }
        .settings-section h5 {
            margin-bottom: 15px;
            font-weight: 600;
        }
        .settings-section:last-child {
            border-bottom: none;
        }
        .setting-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .form-check-input {
            width: 40px;
            height: 20px;
        }
        .form-switch .form-check-input {
            margin-left: 10px;
        }

        /* Chat message styling */
        .message {
            margin-bottom: 15px;
            padding: 12px 15px;
            border-radius: 15px;
            max-width: 95%;
            /* word-wrap: break-word;
            word-break: break-all; */
            /* position: relative; */
        }
        .bot-message {
            background-color: #d1ecf1;
            align-self: flex-start;
            margin-right: auto; /* Align to the left */
            border-bottom-left-radius: 5px;
        }
        .user-message {
            background-color: rgb(66, 165, 245);
            color: white;
            align-self: flex-end;
            margin-left: auto; /* Align to the right */
            border-bottom-right-radius: 5px;
            /* max-height: 200px; */
            overflow-y: auto;
        }
        .message p {
            margin: 0;
        }
        .message small {
            display: block;
            font-size: 0.7em;
            color: #888;
            margin-top: 5px;
        }
        .message .model-info {
            display: inline-block;
            font-size: 0.65em;
            margin-right: 5px;
            color: #6c757d;
            background-color: rgba(220, 220, 220, 0.5);
            padding: 1px 4px;
            border-radius: 3px;
        }
        .message .token-info {
            display: inline-block;
            font-size: 0.65em;
            color: #6c757d;
            background-color: rgba(220, 220, 220, 0.5);
            padding: 1px 4px;
            border-radius: 3px;
        }
        .message .time-info {
            float: right;
        }
        .message .metadata-info {
            float: left;
        }
        .message .metadata-info:empty {
            display: none;
        }
        .message .metadata-info:not(:empty) {
            margin-right: 5px;
        }
        .clearfix::after {
            content: "";
            clear: both;
            display: table;
        }
        .dark-mode .message .model-info,
        .dark-mode .message .token-info {
            color: #bbb;
            background-color: rgba(80, 80, 80, 0.5);
        }
        .chat-avatar {
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            margin-bottom: 5px;
            border-radius: 50%;
        }
        .bot-avatar {
            background-color: #42a5f5;
            color: white;
            border: 1px solid #1976d2;
        }
        .user-avatar {
            background-color: #6c757d;
            color: white;
        }
        .message-wrapper {
            display: flex;
            flex-direction: column;
            margin-bottom: 15px;
        }
        .avatar-and-message {
            display: flex;
            align-items: flex-end;
            gap: 8px;
        }
        .user-message-wrapper {
            align-items: flex-end;
        }
        .user-message small {
            color: rgba(255, 255, 255, 0.8);
            text-align: right;
        }

        /* Clear button styling */
        .btn-clear-history {
            margin-top: auto;
            border-radius: 5px;
        }

        /* Cost indicator styles */
        .cost-indicator {
            font-size: 0.8em;
            padding: 3px 7px;
            border-radius: 12px;
            background-color: rgba(66, 165, 245, 0.1);
            color: rgb(66, 165, 245);
            border: 1px solid rgba(66, 165, 245, 0.2);
            display: flex;
            align-items: center;
            gap: 6px;
            margin-right: 25px;
        }
        
        .cost-indicator i {
            font-size: 0.9em;
        }
        
        .dark-mode .cost-indicator {
            background-color: rgba(66, 165, 245, 0.2);
            border-color: rgba(66, 165, 245, 0.3);
            color: rgba(100, 181, 246, 0.9);
        }

        /* Dark mode styles */
        .dark-mode {
            background-color: #1e1e1e;
            color: #e9e9e9;
        }
        .dark-mode a {
            color: rgb(100, 181, 246);
        }
        .dark-mode code {
            color: #ff86c3;
        }
        .dark-mode .chat-area {
            border-right-color: #444;
        }
        .dark-mode .chat-header,
        .dark-mode .settings-header,
        .dark-mode .settings-section,
        .dark-mode .chat-input-area {
            border-color: #444;
        }
        .dark-mode .settings-sidebar {
            background-color: #2d2d30;
        }
        .dark-mode .bot-message {
            background-color: #3a3a3a;
            color: #e9e9e9;
        }
        .dark-mode .form-control::placeholder {
            color: #666;
        }
        .dark-mode .form-control {
            background-color: #333;
            border-color: #444;
            color: #e9e9e9;
        }
        .dark-mode .form-check-input {
            background-color: #444;
            border-color: #555;
        }
        .dark-mode .form-check-input:checked {
            background-color: #42a5f5;
            border-color: #42a5f5;
        }
        .dark-mode .bot-avatar {
            background-color: #42a5f5;
            border-color: #1976d2;
            color: white;
        }
        .dark-mode .bot-message small {
            color: #aaa;
        }
        
        /* Helper text dark mode styling */
        .dark-mode .text-muted {
            color: #aaa !important;
        }
        
        /* Danger text styling */
        .text-danger {
            color: #dc3545 !important;
        }
        
        .dark-mode .text-danger {
            color: #ff6b6b !important;
        }
        
        /* Model select dark mode styling */
        .dark-mode .form-select {
            background-color: #333;
            border-color: #444;
            color: #e9e9e9;
        }
        .dark-mode .form-select option {
            background-color: #333;
            color: #e9e9e9;
        }
        .dark-mode .form-select optgroup {
            background-color: #333;
            color: #e9e9e9;
        }
        /* Fix for dropdown arrow in dark mode */
        .dark-mode .form-select {
            background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3e%3cpath fill='none' stroke='%23e9e9e9' stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M2 5l6 6 6-6'/%3e%3c/svg%3e");
        }

        /* Better button visibility in dark mode */
        .dark-mode .btn-outline-secondary {
            border-color: #6c757d;
            color: #e9e9e9;
        }
        .dark-mode .btn-outline-secondary i {
            color: #e9e9e9;
        }
        .dark-mode .btn-outline-secondary:disabled {
            color: #e9e9e9;
            opacity: 0.8;
        }

        /* Tool Use History styling */
        .tool-use-container {
            font-family: monospace;
            word-wrap: break-word;
            white-space: normal;
            font-size: 0.7em;
            background-color: #787878;
            border-radius: 4px;
            padding: 4px;
            line-height: 1;
        }
        
        .dark-mode .tool-use-container {
            background-color: #222 !important;
            color: #e0e0e0;
        }
        
        /* Tool use entries styling */
        .tool-entry {
            border-left: 2px solid #42a5f5;
            padding: 0 0 0 4px;
            margin: 2px 0;
            font-size: 10px;
            line-height: 1;
            margin-bottom: 2px;
        }

        .dark-mode .tool-entry {
            border-left-color: #42a5f5;
        }
        
        .tool-timestamp {
            font-size: 9px;
            color: #a2a2a2;
            margin: 0;
            padding: 0;
            line-height: 1;
        }

        .dark-mode .tool-timestamp {
            color: #c9c9c9;
        }
        
        .tool-bubble {
            border-radius: 2px;
            padding: 2px 4px;
            margin: 1px 0;
        }

        .tool-name {
            color: #42a5f5;
            font-weight: 600;
            font-size: 9px;
            text-transform: uppercase;
            margin: 0;
            padding: 0;
            line-height: 1;
            display: flex;
            align-items: center;
        }
        
        .tool-name i {
            margin-right: 3px;
            font-size: 8px;
        }
        
        .tool-input {
            font-size: 9px;
            font-family: monospace;
            white-space: pre-wrap;
            line-height: 1;
            color: #dcdfe4;
            margin: 1px 0 0 0;
            padding: 0;
        }
        
        .text-primary {
            color: #c678dd !important;
        }
        
        .text-success {
            color: #98c379 !important;
        }
        
        /* Dark mode adjustments */
        .dark-mode .tool-name {
            color: #42a5f5;
        }
        
        .dark-mode .tool-input {
            color: #dcdfe4;
        }
        
        /* Tool status badge styling */
        .tool-status-badge {
            margin-left: 4px;
            font-size: 8px;
            font-weight: normal;
        }
        
        .tool-status-badge.progress {
            color: #ffc107;
            animation: pulse 1.5s infinite;
        }
        
        .tool-status-badge.completed {
            color: #28a745;
        }
        
        .tool-status-badge.error {
            color: #dc3545;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }

        /* Custom scrollbar for webkit browsers */
        .chat-messages::-webkit-scrollbar,
        #tool-use-history::-webkit-scrollbar {
            width: 8px;
        }
        .chat-messages::-webkit-scrollbar-track,
        #tool-use-history::-webkit-scrollbar-track {
            background: #f1f1f1;
        }
        .chat-messages::-webkit-scrollbar-thumb,
        #tool-use-history::-webkit-scrollbar-thumb {
            background: #c1c1c1;
            border-radius: 4px;
        }
        .chat-messages::-webkit-scrollbar-thumb:hover,
        #tool-use-history::-webkit-scrollbar-thumb:hover {
            background: #a8a8a8;
        }
        .dark-mode .chat-messages::-webkit-scrollbar-track,
        .dark-mode #tool-use-history::-webkit-scrollbar-track {
            background: #2d2d30;
        }
        .dark-mode .chat-messages::-webkit-scrollbar-thumb,
        .dark-mode #tool-use-history::-webkit-scrollbar-thumb {
            background: #555;
        }
        .dark-mode .chat-messages::-webkit-scrollbar-thumb:hover,
        .dark-mode #tool-use-history::-webkit-scrollbar-thumb:hover {
            background: #666;
        }
        
        /* Loading state styles */
        body.loading::after {
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(to right, #42a5f5, #0dcaf0);
            animation: loading-bar 1.5s infinite;
            z-index: 1000;
        }
        
        @keyframes loading-bar {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }

        /* Collapsible sidebar styles */
        .toggle-sidebar-btn {
            position: absolute;
            right: 12px;
            top: 20px;
            z-index: 100;
            border-radius: 50%;
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: #e8f4f8;
            border: 1px solid #dee2e6;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            padding: 0;
            font-size: 10px;
            transition: background-color 0.2s ease, box-shadow 0.2s ease;
            cursor: pointer;
        }
        
        .toggle-sidebar-btn:hover {
            background-color: #d4edda;
            border-color: #ccc;
            box-shadow: 0 2px 5px rgba(0,0,0,0.15);
        }

        .dark-mode .toggle-sidebar-btn {
            background-color: #2d2d30;
            border-color: #444;
            color: #e9e9e9;
            transition: background-color 0.2s ease;
        }
        
        .dark-mode .toggle-sidebar-btn:hover {
            background-color: #3d3d40;
            border-color: #555;
            box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        }

        .settings-sidebar.collapsed {
            width: 0 !important;
            padding: 0;
            margin-right: -15px;
            overflow: hidden;
        }

        .settings-sidebar.collapsed .settings-content {
            display: none;
        }

        .settings-sidebar.collapsed .settings-header {
            display: none;
        }

        .toggle-sidebar-btn .bi-chevron-left {
            display: none;
        }

        .settings-sidebar.collapsed + .toggle-sidebar-btn .bi-chevron-right {
            display: none;
        }

        .settings-sidebar.collapsed + .toggle-sidebar-btn .bi-chevron-left {
            display: inline;
        }

        /* Disable transitions temporarily during initial load */
        .no-transition,
        .no-transition * {
            transition: none !important;
            animation: none !important;
        }

        /* Dark mode toggle button */
        .btn-icon {
            width: 35px;
            height: 35px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: transparent;
            border: 1px solid #dee2e6;
            color: #6c757d;
            padding: 0;
            transition: all 0.2s ease;
        }
        
        .btn-icon:hover {
            background-color: rgba(0, 0, 0, 0.05);
        }
        
        .btn-icon i {
            font-size: 1.1rem;
        }
        
        .dark-mode .btn-icon {
            border-color: #444;
            color: #e9e9e9;
        }
        
        .dark-mode .btn-icon:hover {
            background-color: rgba(255, 255, 255, 0.1);
        }

        /* Session History Modal Dark Mode Styles */
        .dark-mode .modal-content {
            background-color: #2d2d30;
            color: #e9e9e9;
            border-color: #444;
        }
        
        .dark-mode .modal-header,
        .dark-mode .modal-footer {
            border-color: #444;
        }
        
        .dark-mode .btn-close {
            filter: invert(1) grayscale(100%) brightness(200%);
        }
        
        .dark-mode .btn-secondary {
            background-color: #444;
            border-color: #555;
        }
        
        .dark-mode .btn-secondary:hover {
            background-color: #555;
            border-color: #666;
        }
        
        .dark-mode .list-group-item {
            background-color: #333;
            color: #e9e9e9;
            border-color: #444;
        }
        
        .dark-mode .list-group-item a {
            color: #42a5f5;
        }
        
        .dark-mode .list-group-item a:hover {
            color: #64b5f6;
        }
        
        /* Help Modal Specific Styles */
        .help-modal .card {
            border: 1px solid rgba(0,0,0,.125);
            box-shadow: 0 0.125rem 0.25rem rgba(0,0,0,.075);
        }
        
        .dark-mode .help-modal .card {
            border-color: #444;
            background-color: #333;
        }
        
        .dark-mode .help-modal .card-body {
            background-color: #333;
            color: #e9e9e9;
        }
        
        .dark-mode .help-modal .card-header {
            border-bottom-color: #444;
        }
        
        .dark-mode .help-modal .bg-light {
            background-color: #444 !important;
            color: #e9e9e9;
        }
        
        .dark-mode .help-modal .alert-info {
            background-color: rgba(66, 165, 245, 0.15);
            border-color: rgba(66, 165, 245, 0.3);
            color: #e9e9e9;
        }
        
        .dark-mode .help-modal .accordion-item {
            background-color: #333;
            border-color: #444;
        }
        
        .dark-mode .help-modal .accordion-button {
            background-color: #333;
            color: #e9e9e9;
            border-color: #444;
        }
        
        .dark-mode .help-modal .accordion-button:not(.collapsed) {
            background-color: #444;
            color: #e9e9e9;
        }
        
        .dark-mode .help-modal .accordion-body {
            background-color: #2d2d30;
            color: #e9e9e9;
            border-top-color: #444;
        }
        
        /* Ensure proper contrast for badges in dark mode */
        .dark-mode .badge {
            color: #fff;
        }
        
        /* kbd styling for keyboard shortcuts */
        kbd {
            background-color: #212529;
            color: #fff;
            padding: 0.2rem 0.4rem;
            font-size: 0.875em;
            border-radius: 0.25rem;
        }
        
        .dark-mode kbd {
            background-color: #495057;
            color: #e9e9e9;
        }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <!-- Chat Area -->
            <div class="col-md-12 chat-area" id="chat-area">
                <div class="chat-header d-flex justify-content-between align-items-center">
                    <div>
                        <h3><i class="bi bi-robot me-2 text-primary"></i>Agent Coding Assistant</h3>
                    </div>
                    <div class="d-flex align-items-center">
                        <button id="toggle-help-btn" class="btn btn-sm btn-icon me-2" title="Help & Getting Started" data-bs-toggle="modal" data-bs-target="#helpModal">
                            <i class="bi bi-question-circle"></i>
                        </button>
                        <button id="toggle-session-history-btn" class="btn btn-sm btn-icon me-2" title="Show Session History" data-bs-toggle="modal" data-bs-target="#sessionHistoryModal">
                            <i class="bi bi-clock-history"></i>
                        </button>
                        <button id="toggle-dark-mode-btn" class="btn btn-sm btn-icon me-2" title="Toggle Dark Mode">
                            <i class="bi bi-sun-fill"></i>
                        </button>
                        <div id="cost-indicator" class="cost-indicator">
                            <i class="bi bi-coin"></i>
                            <span id="total-cost">$0.000</span>
                            <span class="text-muted ms-1"><small id="total-tokens">0 tokens</small></span>
                        </div>
                    </div>
                </div>
                <div class="chat-messages" id="chatMessages">
                </div>
                <div class="chat-input-area">
                    <textarea class="form-control" placeholder="Ask me about Google Ads campaigns, strategies, optimization..." rows="1"></textarea>
                    <button class="btn btn-primary"><i class="bi bi-send-fill"></i></button>
                </div>
                <small class="text-muted mt-1 d-block text-center">
                    Press Enter to send, Shift+Enter for a new line
                </small>
            </div>

            <!-- Settings Sidebar -->
            <div class="col-md-3 settings-sidebar collapsed" id="settings-sidebar">
                <div class="settings-header">
                    <h4><i class="bi bi-gear me-2"></i> Control Center</h4>
                </div>
                <div class="settings-content">
                    <div class="settings-section">
                        <h5>Session Control</h5>
                        <div class="d-flex align-items-center mb-3">
                            <button id="increment-button" class="btn btn-sm btn-outline-secondary me-2" title="Increment session ID">+</button>
                            <input type="text" id="session-id" class="form-control form-control-sm" placeholder="Session ID" onkeydown="if(event.key === 'Enter') { event.preventDefault(); initSession(); }">
                        </div>
                        <div class="mb-3 d-flex align-items-center">
                            <button class="btn btn-sm btn-outline-secondary me-2" style="width: 31px; height: 31px; display: flex; align-items: center; justify-content: center;" disabled title="AI Model">
                                <i class="bi bi-cpu-fill"></i>
                            </button>
                            <select id="model-select" class="form-select form-select-sm" title="Select AI Model" style="flex: 1;">
                                <optgroup label="Complexity of the task at hand">
                                    <option value="easy" title="no thinking required - gemini-2.5-flash-lite" selected>easy</option>
                                    <option value="medium" title="some thinking required - gemini-2.5-flash">medium</option>
                                    <option value="hard" title="a lot of thinking required - gemini-2.5-pro">hard</option>
                                </optgroup>
                            </select>
                        </div>
                    </div>
                    
                    <!-- Dark Mode toggle is now in the header -->
                    <div class="setting-item" style="display: none;">
                        <input class="form-check-input" type="checkbox" id="darkModeToggle">
                        <input class="form-check-input" type="checkbox" id="showLLMToolCalls">
                    </div>
                    
                    <!-- Tool Use History Section -->
                    <div class="settings-section" id="toolUseSection" style="display: none;">
                        <h5><i class="bi bi-tools me-2"></i> Tool Use History</h5>
                        <div id="tool-use-history" class="tool-use-container" style="max-height: 350px; overflow-y: auto; padding: 0; border-radius: 3px; margin: 0;">
                            <div class="text-center text-muted p-1" id="tool-history-empty" style="font-size: 11px;">
                                <i class="bi bi-info-circle mb-1" style="font-size: 1rem;"></i>
                                <p>No tool calls yet.</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Toggle Sidebar Button -->
            <button class="btn btn-sm toggle-sidebar-btn" id="toggle-sidebar-btn">
                <i class="bi bi-chevron-right"></i>
                <i class="bi bi-chevron-left"></i>
            </button>
        </div>
    </div>

    <!-- Session History Modal -->
    <div class="modal fade" id="sessionHistoryModal" tabindex="-1" aria-labelledby="sessionHistoryModalLabel" aria-hidden="true">
        <div class="modal-dialog modal-lg modal-dialog-scrollable">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="sessionHistoryModalLabel"><i class="bi bi-clock-history me-2"></i>Session History</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <ul class="list-group" id="sessionHistoryList">
                        <!-- Session history will be populated here by JavaScript -->
                    </ul>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Help Modal -->
    <div class="modal fade" id="helpModal" tabindex="-1" aria-labelledby="helpModalLabel" aria-hidden="true">
        <div class="modal-dialog modal-xl modal-dialog-scrollable">
            <div class="modal-content help-modal">
                <div class="modal-header">
                    <h5 class="modal-title" id="helpModalLabel"><i class="bi bi-question-circle me-2"></i>Help & Getting Started</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div class="container-fluid">
                        <!-- Use Cases Section -->
                        <div class="row mb-4">
                            <div class="col-12">
                                <h4><i class="bi bi-lightbulb me-2 text-primary"></i>What can you do with Agent Coding Assistant?</h4>
                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="card mb-3">
                                            <div class="card-body">
                                                <h6 class="card-title"><i class="bi bi-search me-1"></i>Campaign Strategy & Planning</h6>
                                                <ul class="small">
                                                    <li>Get expert advice on campaign structure and setup</li>
                                                    <li>Learn about different campaign types and their use cases</li>
                                                    <li>Understand bidding strategies and optimization techniques</li>
                                                    <li>Get guidance on keyword research and targeting</li>
                                                </ul>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="col-md-6">
                                        <div class="card mb-3">
                                            <div class="card-body">
                                                <h6 class="card-title"><i class="bi bi-graph-up me-1"></i>Performance Optimization</h6>
                                                <ul class="small">
                                                    <li>Analyze campaign performance and identify improvements</li>
                                                    <li>Learn about Quality Score optimization</li>
                                                    <li>Get recommendations for ad copy and extensions</li>
                                                    <li>Understand conversion tracking and attribution models</li>
                                                </ul>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Getting Started Section -->
                        <div class="row mb-4">
                            <div class="col-12">
                                <h4><i class="bi bi-play-circle me-2 text-success"></i>Getting Started</h4>
                                <div class="alert alert-info" role="alert">
                                    <i class="bi bi-info-circle me-2"></i>
                                    <strong>Ready to use:</strong> The Agent Coding Assistant is configured and ready to answer your questions.
                                </div>
                                
                                <div class="row">
                                    <div class="col-md-6">
                                        <h6><span class="badge bg-primary me-2">1</span>Choose Your Session</h6>
                                        <ol class="small">
                                            <li>Each conversation is tied to a unique Session ID</li>
                                            <li>You can create a new session or continue an existing one</li>
                                            <li>Use the <strong>+</strong> button to increment to a new session</li>
                                            <li>Previous sessions can be accessed via the history button</li>
                                        </ol>
                                        
                                        <h6><span class="badge bg-primary me-2">2</span>Select AI Complexity</h6>
                                        <ol class="small">
                                            <li><strong>Easy:</strong> Quick answers to simple Google Ads questions</li>
                                            <li><strong>Medium:</strong> Detailed analysis and strategic recommendations</li>
                                            <li><strong>Hard:</strong> Complex problem-solving and multi-faceted strategies</li>
                                        </ol>
                                    </div>
                                    <div class="col-md-6">
                                        <h6><span class="badge bg-primary me-2">3</span>Start Asking Questions</h6>
                                        <div class="bg-light p-3 rounded small">
                                            <strong>Example queries to try:</strong>
                                            <ul class="mb-0">
                                                <li>"How do I set up a Performance Max campaign?"</li>
                                                <li>"What's the best bidding strategy for e-commerce?"</li>
                                                <li>"How can I improve my Quality Score?"</li>
                                                <li>"Explain different Google Ads campaign types"</li>
                                                <li>"What are responsive search ads best practices?"</li>
                                            </ul>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- UI Description Section -->
                        <div class="row mb-4">
                            <div class="col-12">
                                <h4><i class="bi bi-display me-2 text-warning"></i>User Interface Guide</h4>
                                
                                <div class="row">
                                    <div class="col-md-6">
                                        <div class="card mb-3">
                                            <div class="card-header bg-warning text-dark">
                                                <h6 class="mb-0"><i class="bi bi-lightbulb me-1"></i>Pro Tips</h6>
                                            </div>
                                            <div class="card-body small">
                                                <ul class="mb-0">
                                                    <li>Be specific in your questions for better results</li>
                                                    <li>Ask follow-up questions to dive deeper into topics</li>
                                                    <li>Use the tool history to see what sources are being used</li>
                                                    <li>Each session preserves context for related questions</li>
                                                    <li>Higher complexity models provide more detailed analysis</li>
                                                    <li>The assistant can explain both basic and advanced concepts</li>
                                                </ul>
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <div class="col-md-6">
                                        <div class="card mb-3">
                                            <div class="card-header bg-info text-white">
                                                <h6 class="mb-0"><i class="bi bi-tools me-1"></i>Interface Features</h6>
                                            </div>
                                            <div class="card-body small">
                                                <ul class="mb-0">
                                                    <li><strong>Tool Use History:</strong> See what knowledge sources are accessed</li>
                                                    <li><strong>Cost Indicator:</strong> Track tokens used and estimated costs</li>
                                                    <li><i class="bi bi-question-circle me-1"></i> <strong>Help:</strong> Opens this help dialog</li>
                                                    <li><i class="bi bi-clock-history me-1"></i> <strong>History:</strong> View and switch between sessions</li>
                                                    <li><i class="bi bi-sun-fill me-1"></i>/<i class="bi bi-moon-fill me-1"></i> <strong>Theme:</strong> Toggle dark/light mode</li>
                                                    <li><i class="bi bi-gear me-1"></i> <strong>Settings:</strong> Show/hide the Control Center panel</li>
                                                </ul>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Include self-hosted Bootstrap JS -->
    <script src="/static/external/bootstrap-5.3.6-dist/js/bootstrap.bundle.min.js"></script>
    
    <!-- Include Showdown for markdown conversion -->
    <script src="/static/external/showdown.min.js"></script>
    
    <!-- Include Socket.IO client -->
    <script src="https://cdn.socket.io/4.8.1/socket.io.min.js"></script>
    
    <!-- Include our custom JS -->
    <script src="/js/app.js?v=2"></script>
    
    <script>
        // Add event delegation for tool entry expansion
        document.getElementById('tool-use-history').addEventListener('click', function(event) {
            let target = event.target;
            while (target && !target.classList.contains('tool-entry')) {
                if (target === this) return;
                target = target.parentElement;
            }
            
            if (target) {
                target.classList.toggle('expanded');
            }
        });
    </script>
</body>
</html>
```

## File: `web/start_web_server.py`
```
#!/usr/bin/env python3
"""
Start script for the Agent Coding Assistant web interface.
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
    print("🚀 Starting Agent Coding Assistant Web Interface")
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
