# Agent Coding Assistant

This project is a **streaming AI agent** for Google Ads expertise, built using **DSPy + FastAPI + Socket.IO**. It provides real-time streaming responses with tool transparency and grounding information.

## ✨ Features

- **Real-time Streaming**: WebSocket-based streaming responses
- **Tool Transparency**: See when internal knowledge vs web search is used
- **Grounding Information**: Track sources and references in real-time
- **Dual Interfaces**: Both HTTP REST API and WebSocket for different use cases
- **Error Handling**: Graceful error handling and recovery

## 🚀 Setup

This project uses `uv` for dependency management.

1.  **Install dependencies:**
    ```bash
    uv sync
    ```

2.  **Set up your environment:**
    You'll need API keys for Google Gemini and Tavily search:
    ```bash
    export GOOGLE_API_KEY="your-google-api-key"
    export TAVILY_API_KEY="your-tavily-api-key"
    ```

## 🎯 Running the Application

### Option 1: Web Interface (recommended)
```bash
uv run python web/start_web_server.py
```
**Access at**: `http://localhost:8000/`

### Option 2: API server with Socket.IO
```bash
uv run python start_server.py
```

### Option 3: Direct uvicorn
```bash
uv run uvicorn api.main:socket_app --host 0.0.0.0 --port 8000 --reload
```

### Option 4: Console-only mode (original)
```bash
uv run python dspy_agent_refactored.py
```

## 🌐 API Endpoints

- **Root**: `http://localhost:8000/` - API information
- **Health Check**: `http://localhost:8000/health` - Service health
- **Documentation**: `http://localhost:8000/docs` - Interactive API docs
- **Socket.IO Info**: `http://localhost:8000/socket.io-info` - WebSocket details

### HTTP Endpoints
- `POST /api/v1/ask` - Ask question (streaming service)
- `POST /api/v1/ask-sync` - Ask question (original service)
- `GET /api/v1/capabilities` - Get AI capabilities

### WebSocket Events
- **Client → Server**: `ask_question`, `cancel_question`, `ping`
- **Server → Client**: `answer_chunk`, `tool_start`, `grounding_update`, `answer_complete`

## 🧪 Testing

Test the WebSocket integration:
```bash
uv run python test_websocket_client.py
```

## 📁 Project Structure

```
├── api/                          # FastAPI application
│   ├── main.py                  # Main FastAPI app
│   ├── websocket_manager.py     # Socket.IO event handling
│   └── routes/                  # HTTP routes
├── dspy_agent_*.py              # DSPy agent components
├── dspy_agent_streaming_*.py    # Streaming versions
└── knowledge_base/              # Internal knowledge
```