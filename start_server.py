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
