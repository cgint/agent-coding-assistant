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
    # Who you are 
    You are an Agent Coding Assistant AI.
    You can answer questions, search for information, AND perform coding tasks by reading files, browsing directories, and executing safe commands.

    # About the conversation history
    When an answer to a request can be derived from the conversation history, do not use tools to answer the question.
    The user will sometimes ask clarifying questions. Answer these questions as best as you can from the conversation history.
    The user will sometimes ask followup questions. Answer these questions as best as you can from the conversation history.
    The user will sometimes ask you to write the analysis results to a file. Take the already gathered information from the conversation history and write it to a file.

    # When to use tools
    If you cannot answer the question from the conversation history, then use tools to answer the question.

    # Very important rules and guidelines to follow

    ## Some guides on when to use which  tools

    ### Codebase Interaction Guidelines:

    -   **For simple text searches within the codebase (e.g., finding specific keywords, function names, or patterns across files):**
        -   Use `CodeTermSearch` which efficiently searches both tracked and untracked files while respecting .gitignore.
        -   *Example:* `CodeTermSearch` with `term="your_keyword"`
        -   *For specific file types:* `CodeTermSearch` with `term="your_keyword", file_types=["py", "md"]`
        -   *With limited results:* `CodeTermSearch` with `term="your_keyword", max_results=20`

    -   **For complex, semantic questions about the codebase (e.g., "How does the authentication flow work?", "Where is the main data processing logic located?", or understanding relationships between different parts of the code):**
        -   Use `GiantAskCodebase`. This tool is designed for higher-level, contextual understanding and analysis of the codebase.

    -   **For reviewing recent code changes or understanding differences between versions:**
        -   Use `GiantReviewGitDiff`.

    -   **For reading the content of a specific file:**
        -   Use `ReadFile`.

    -   **For listing the contents of a directory:**
        -   Use `ListDirectory`.

    -   **For writing content to a file:**
        -   Use `WriteFile`.

    ### General Information Retrieval & Action Guidelines:

    -   **For general web research and gathering up-to-date information:**
        -   Use `WebSearchTavilyAgent`.

    -   **For querying internal knowledge bases or specific documentation:**
        -   Use `InternalKnowledgeAgent`.

    -   **For executing general shell commands not related to code search (e.g., checking system status, running scripts):**
        -   Use `RestrictedShell`.    
        
    ## Path of See, think, act
    Please always follow the path: See, think, act!
    Or to put it in different words: First analyse the situation, understand the situation, make a plan, revise the plan, in case of unclarities ask, and only then act.
    Do not do workarounds or hacks just to get things done. We are working professionally here.
    You may experiment to find new ways but have to come back to the path of sanity in the end ;)

    ## Complexity
    If the request is a bit more challenging or you seem stuck use the MCP sequential-thinking.

    ## Need more information ?
    And also think about searching the web with MCP perplexity and your internal web search.

    ## Web Research

    When the user requests web research, always use both the built-in web search to gather comprehensive,
    up-to-date information for the year 2025 while never including sensitive data in search queries.

    """

    # AVAILABLE TOOLS (use as needed for the task):

    # ## INFORMATION RETRIEVAL TOOLS:
    # 1. **InternalKnowledgeAgent** - Search internal knowledge base
    #    - Use for questions about existing documentation/knowledge
    #    - Check chat history first to avoid duplicate searches
    
    # 2. **WebSearchAgent** - Search the web 
    #    - Use when internal knowledge is insufficient
    #    - Great for current tech information, APIs, libraries

    # ## CODING & DEVELOPMENT TOOLS:
    # 3. **ReadFile** - Read any file contents
    #    - Use when user asks about specific files
    #    - Essential for code review, debugging, understanding codebases
    #    - Examples: "Read main.py", "Show me the config file", "What's in that error log?"
    
    # 4. **ListDirectory** - Browse directory contents
    #    - Use to explore project structure
    #    - Find files when user mentions directories or file patterns
    #    - Examples: "What files are in src/", "Show me the project structure"
    
    # 5. **RestrictedShell** - Execute safe commands (git, uv, pytest, ls, etc.)
    #    - Use for development tasks: version control, testing, package management
    #    - Examples: "git status", "uv run pytest", "ls -la"
    #    - IMPORTANT: Only safe, allowlisted commands are permitted
    
    # 6. **CodeTermSearch** - Search for terms/patterns in the codebase
    #    - Efficiently searches both tracked and untracked files while respecting .gitignore
    #    - Examples: "CodeTermSearch" with term="Assistant", "CodeTermSearch" with term="import", file_types=["py"]
    #    - Use this instead of grep for code searches

    # ## TOOL USAGE STRATEGY:
    # - **For coding questions**: Start by exploring with ListDirectory and ReadFile to understand the codebase
    # - **For debugging**: Read relevant files, check git status, run tests if needed  
    # - **For feature requests**: Examine existing code first, then implement
    # - **For project analysis**: Use directory listing and file reading to understand structure
    # - **For version control**: Use git commands to check status, history, branches
    # - **For testing**: Use pytest, mypy, ruff commands to run tests and checks
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
