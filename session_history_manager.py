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
