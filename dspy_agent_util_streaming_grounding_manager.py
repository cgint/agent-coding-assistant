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
