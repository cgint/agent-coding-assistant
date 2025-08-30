import dspy
from typing import List, Any
from pydantic import BaseModel

# --- Response Model ---

class QuestionAnswerResponse(BaseModel):
    """Response object containing question, history, metadata, and final answer."""
    question: str
    history: dict[str, Any]  # Will contain dspy.History serialized data
    tracked_usage_metadata: dict[str, Any]
    final_answer: str

# --- Main DSPy Agent ---

class AgentCodingAssistantSignature(dspy.Signature):
    """
    You are an Agent Coding Assistant AI. Answer the user's question by retrieving information from the internal knowledge base or web search.

    IMPORTANT: Use the tools in this STRICT priority order. Only proceed to the next tool if the previous tool's response is insufficient to answer the user's question:

    1. FIRST: For simple questions that don't require specialized knowledge or the information to answer the question is already in the history,
       you may answer directly without using tools.

    2. SECOND: Use InternalKnowledgeAgent from chat history if it was already requested by search term once during the conversation!
       - Do not fetch the internal knowledge base with the very same search term again within the same conversation.

    3. THIRD: Use InternalKnowledgeAgent - Retrieves information from the internal knowledge base.
       - If this provides a complete answer, use it and do NOT call other tools.
       - Only proceed to step 4 if the internal knowledge is insufficient or unavailable.

    4. FOURTH: If needed, use WebSearchAgent - Retrieves information from web search with native Google Search grounding.
       - Only use this if InternalKnowledgeAgent didn't provide sufficient information.
       - In case the user wants you to specifically search within our internal knowledge base, then do not use the WebSearchAgent.

    """
    # NOTE: If the user asks about conversation history and the history field contains previous messages, provide a summary based on that information. Do NOT say there is no history if the history field is populated.
    history: dspy.History = dspy.InputField(desc="IMPORTANT: In case this 'history' field is not populated but there are previous messages, use them as the history to answer the question.")
    question: str = dspy.InputField(desc="The input question from the user")
    answer: str = dspy.OutputField(desc="The answer to the user's question. Must be fulfilled throughly with the information from the tools or conversation history as appropriate.")


class AgentCodingAssistantAI(dspy.Module):
    def __init__(self, tools: List[Any]):
        super().__init__()
        self.react_agent = dspy.ReAct(AgentCodingAssistantSignature, tools=tools)

    def forward(self, question: str, history: dspy.History | None = None) -> Any:  # type: ignore[misc]
        # Use empty history if none provided
        if history is None:
            print("AgentCodingAssistantAI: No history provided, creating empty history")
            history = dspy.History(messages=[])

        print(f"AgentCodingAssistantAI: History contains # {len(history.messages)} messages")
        
        # Debug: Print actual history content
        for i, msg in enumerate(history.messages):
            print(f"  History message {i+1}: Q='{msg.get('question', 'N/A')[:50]}...' A='{msg.get('answer', 'N/A')[:50]}...'")
        
        # Get the result from ReAct agent
        result = self.react_agent(question=question, history=history)
        
        # Append the current Q/A turn to the history
        history.messages.append({
            "question": question,
            "answer": result.answer  # type: ignore[attr-defined]
        })
        
        return result
