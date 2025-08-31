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
