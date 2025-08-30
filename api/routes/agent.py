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
