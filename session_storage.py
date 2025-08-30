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



