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
