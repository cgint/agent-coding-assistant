from dspy_agent_tool_internal_knowledge import InternalKnowledgeTool, InternalKnowledgeAgent
from dspy_agent_util_streaming_grounding_manager import StreamingGroundingManager

class StreamingInternalKnowledgeTool(InternalKnowledgeTool):
    """Enhanced InternalKnowledgeTool with real-time event emission for WebSocket communication."""
    
    model_config = {"extra": "allow"}
    
    def __init__(self, grounding_manager: StreamingGroundingManager):
        super().__init__(grounding_manager)
        # Override with streaming grounding manager
        self.grounding_manager = grounding_manager

    async def call_async(self, query: str) -> str:
        """Async version that relies on central DSPy callbacks and grounding manager for emissions."""

        try:
            # Execute the internal knowledge agent
            internal_agent = InternalKnowledgeAgent()
            result = internal_agent.forward(query)
            
            # Add to grounding (this will emit grounding events automatically)
            await self.grounding_manager.add_source_async(
                source_type="internal", 
                title="Internal Knowledge Base",
                url="knowledge_base/internal_notes.md",
                domain="internal"
            )
            await self.grounding_manager.add_query_async(query)

            return result

        except Exception:
            raise

    def __call__(self, query: str) -> str:
        """Synchronous call that relies on central DSPy callbacks for events."""
        result = super().__call__(query=query)
        return result
