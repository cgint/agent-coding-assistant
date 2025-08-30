from __future__ import annotations

import json

import dspy

from dspy_constants import MODEL_NAME_GEMINI_2_5_FLASH
from dspy_agent_util_grounding_manager import GroundingManager
from dspy_agent_tool_internal_knowledge import InternalKnowledgeTool
from dspy_agent_tool_websearch_tavily import WebSearchToolTavily
from dspy_agent_expert_ai import AgentCodingAssistantAI, QuestionAnswerResponse
from dspy_agent_lm_vertexai import get_vertexai_lm


class DspyAgentService:
    """
    Service responsible for configuring DSPy, initializing tools/agents,
    and providing a simple interface for answering questions.
    """

    def __init__(self) -> None:
        self._configure_dspy()

        # Initialize the grounding manager and tools
        self.grounding_manager = GroundingManager()
        internal_tool = InternalKnowledgeTool(self.grounding_manager)
        web_search_tool = WebSearchToolTavily(
            self.grounding_manager,
            include_domains=["google.com"],
            top_k=10,
            include_raw_content=True,
        )

        # Initialize the main agent with the tools
        self.expert_ai = AgentCodingAssistantAI(tools=[internal_tool, web_search_tool])

    def _configure_dspy(self) -> None:
        try:
            dspy.settings.configure(
                lm=get_vertexai_lm(
                    model=f"vertex_ai/{MODEL_NAME_GEMINI_2_5_FLASH}",
                    reasoning_effort="disable",
                ),
                track_usage=True,
            )
            dspy.configure_cache(
                enable_disk_cache=False, enable_memory_cache=False, enable_litellm_cache=False
            )
            print(f"DSPy configured to use {dspy.settings.lm.model}.")
        except Exception as e:  # noqa: BLE001
            print(f"Error configuring DSPy: {e}")
            exit(1)

    def answer_question_with_history(self, question: str, history: dspy.History | None = None) -> QuestionAnswerResponse:
        """
        Answer a question with conversation history, returning a structured response.
        
        Args:
            question: The user's question
            history: Optional conversation history from previous interactions
            
        Returns:
            QuestionAnswerResponse containing question, updated history, metadata, and final answer
        """
        # Use empty history if none provided (first call)
        if history is None:
            history = dspy.History(messages=[])
        
        # Reset grounding manager for the new query
        self.grounding_manager.reset()

        # Run the agent with history
        prediction = self.expert_ai(question=question, history=history)
        tracked_usage_metadata = prediction.get_lm_usage()
        print(f"Tracked usage metadata: {json.dumps(tracked_usage_metadata, indent=4)}")

        # Enhance the answer with grounding information
        final_answer = prediction.answer + self.grounding_manager.format_for_display()

        print("\n--- Final Structured Output ---\n")
        print(final_answer)
        print("\n--- End of Output ---")
        
        # Create response object
        return QuestionAnswerResponse(
            question=question,
            history={"messages": history.messages},  # Serialize history for Pydantic
            tracked_usage_metadata=tracked_usage_metadata,
            final_answer=final_answer
        )


