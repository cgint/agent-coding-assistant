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
