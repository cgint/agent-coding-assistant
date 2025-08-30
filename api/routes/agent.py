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
