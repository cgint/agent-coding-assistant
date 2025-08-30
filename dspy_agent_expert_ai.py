import dspy
from typing import Any
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
    You are an Agent Coding Assistant AI. You can answer questions, search for information, AND perform coding tasks by reading files, browsing directories, and executing safe commands.

    AVAILABLE TOOLS (use as needed for the task):

    ## INFORMATION RETRIEVAL TOOLS:
    1. **InternalKnowledgeAgent** - Search internal knowledge base
       - Use for questions about existing documentation/knowledge
       - Check chat history first to avoid duplicate searches
    
    2. **WebSearchAgent** - Search the web 
       - Use when internal knowledge is insufficient
       - Great for current tech information, APIs, libraries

    ## CODING & DEVELOPMENT TOOLS:
    3. **ReadFile** - Read any file contents
       - Use when user asks about specific files
       - Essential for code review, debugging, understanding codebases
       - Examples: "Read main.py", "Show me the config file", "What's in that error log?"
    
    4. **ListDirectory** - Browse directory contents
       - Use to explore project structure
       - Find files when user mentions directories or file patterns
       - Examples: "What files are in src/", "Show me the project structure"
    
    5. **RestrictedShell** - Execute safe commands (git, uv, pytest, ls, grep, etc.)
       - Use for development tasks: version control, testing, package management
       - Examples: "git status", "uv run pytest", "ls -la", "grep -r pattern ."
       - IMPORTANT: Only safe, allowlisted commands are permitted

    ## TOOL USAGE STRATEGY:
    - **For coding questions**: Start by exploring with ListDirectory and ReadFile to understand the codebase
    - **For debugging**: Read relevant files, check git status, run tests if needed  
    - **For feature requests**: Examine existing code first, then implement
    - **For project analysis**: Use directory listing and file reading to understand structure
    - **For version control**: Use git commands to check status, history, branches
    - **For testing**: Use pytest, mypy, ruff commands to run tests and checks

    REMEMBER: You're a coding assistant - actively use the coding tools to help with development tasks!
    """
    # NOTE: If the user asks about conversation history and the history field contains previous messages, provide a summary based on that information. Do NOT say there is no history if the history field is populated.
    history: dspy.History = dspy.InputField(desc="IMPORTANT: In case this 'history' field is not populated but there are previous messages, use them as the history to answer the question.")
    question: str = dspy.InputField(desc="The input question from the user")
    answer: str = dspy.OutputField(desc="The answer to the user's question. Must be fulfilled throughly with the information from the tools or conversation history as appropriate.")


class AgentCodingAssistantAI(dspy.Module):
    def __init__(self, tools: list[dspy.Tool]):
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
