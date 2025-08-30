# Plan: Evolving the Agent into a Coding Assistant

## 1. Objective
The primary goal is to extend the existing `dspy-ai` based "Google Ads Expert AI" into a fully-fledged Coding Assistant. This evolution will enable the agent to interact directly with the development environment, including reading/writing files, executing tests, and running terminal commands, thereby allowing it to autonomously perform coding tasks.

## 2. Current Architecture Summary
The application is built on a robust and modern stack:
- **Backend:** FastAPI server run with Uvicorn.
- **AI Framework:** `dspy-ai`, utilizing a `ReAct` agent (`AgentCodingAssistantAI`) for task orchestration.
- **Real-time Communication:** `python-socketio` for a streaming, interactive web UI.
- **Core Capabilities:** The agent currently specializes in information retrieval using `InternalKnowledgeTool` and `WebSearchToolTavily`.
- **Persistence:** A session management system is in place for chat history.

## 3. Proposed Strategy: A Hybrid "Best of Both Worlds" Approach
We will adopt a hybrid strategy that combines the security of custom **Model Context Protocol (MCP)** servers for high-risk operations with the development speed of **LangChain Tools** for lower-risk, standard operations. This balances security, modularity, and implementation efficiency.

### 3.1 High-Risk Tools via Custom MCP Servers
For any operation that can modify the local file system or execute code, we will use standalone MCP servers. This runs each tool in an isolated process, providing a critical security sandbox that prevents the main application from being directly exposed.

**Implementation:**
- Create small, independent Python scripts for each high-risk tool (e.g., `tools/mcp/filesystem_mcp.py`, `tools/mcp/testing_mcp.py`).
- These scripts will use the `mcp` Python SDK to define and run tools.
- In the main application, we will create `dspy.Tool` wrappers that act as clients, communicating with these servers via `stdio`.

**Example MCP Server (`tools/mcp/testing_mcp.py`):**
```python
from mcp.server.fastmcp import FastMCP
import subprocess

mcp = FastMCP("TestingTools")

@mcp.tool()
def run_tests() -> str:
    """Runs the entire pytest test suite using 'uv run pytest'."""
    try:
        result = subprocess.run(
            ["uv", "run", "pytest"],
            capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Tests failed:\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}"

if __name__ == "__main__":
    mcp.run()
```

### 3.2 Low-Risk Tools via LangChain Wrappers
For read-only operations or interactions with external APIs, we will leverage the extensive library of pre-built LangChain tools. This accelerates development significantly.

**Implementation:**
- Add `langchain-community` as a project dependency.
- Create new `dspy.Tool` classes that wrap specific LangChain tools. These wrappers will instantiate the LangChain tool and call its `run()` method.

### 3.3 Restricted Shell Tool (Medium-Risk)
For command-line operations needed for coding (like running tests, git operations, package management), we will create a restricted shell tool with allowlisted commands. This provides more flexibility than MCP isolation while maintaining security through command filtering.

**Implementation:**
- Create a `RestrictedShellTool` that only allows predefined command prefixes
- Define allowed commands for common coding operations (git, uv, pytest, ls, etc.)
- Implement comprehensive logging and error handling
- Use subprocess with proper security measures

## 4. Agent Instruction (`Signature`) Update
To make the agent aware of its new capabilities, we will update the `AgentCodingAssistantSignature` in `dspy_agent_expert_ai.py`. This is critical for guiding the `ReAct` agent's reasoning process.

**Updated Signature:**
```python
class AgentCodingAssistantSignature(dspy.Signature):
    """
    You are an expert AI Coding Assistant. Your primary goal is to help users by directly modifying and testing the codebase to fulfill their requests.

    ## Development Guidelines:

    1.  **Analyze First:** Before writing or changing code, use tools like `ReadFile` or `ListDirectory` to understand the current state of the codebase.
    2.  **Make Minimal Changes:** Implement the smallest possible change to address the user's request. Do not perform large, unnecessary refactors.
    3.  **Test Your Work:** After every modification made with a tool like `WriteFile`, you MUST run the test suite using the `RunTests` tool to verify that your changes work correctly and have not introduced any regressions.
    4.  **Tool Priority & Usage:**
        - Use `ReadFile` to examine existing code.
        - Use `WriteFile` to create new files or modify existing ones.
        - Use `RunTests` immediately after any file modification.
        - Use `WebSearch` if you encounter an error or need to research a library or concept.
        - Use `Terminal` ONLY for simple, safe, read-only commands as a last resort.
    """
    # ... existing fields ...
```

## 5. Overall Status

### 5.1 Dependencies Added ✅
- **`mcp[cli]`** - Model Context Protocol Python SDK
- **`langchain-community`** - LangChain community tools

### 5.2 Tools Implemented ✅
1. **Filesystem Tools** - See `TASK_add_coding_2_PLAN_tool_filesystem.md`
2. **Restricted Shell Tool** - See `TASK_add_coding_3_PLAN_tool_shell_restricted.md`

### 5.3 Agent Integration ✅
- **Current Tool Count:** 5 tools total
  1. Internal Knowledge Tool (existing)
  2. Web Search Tool (existing)  
  3. Read File Tool (new)
  4. List Directory Tool (new)
  5. Restricted Shell Tool (new)
- **Streaming Architecture:** All tools work with existing streaming and grounding systems
- **Located in:** `dspy_agent_streaming_service.py`

### 5.4 Pending Work ⏳
- **Agent Signature Updates:** Update `AgentCodingAssistantSignature` for coding assistant behavior
- **End-to-End Testing:** Comprehensive testing via web UI
- **Future Tools:** WriteFile (MCP), RunTests (MCP), more as needed

## 6. Next Steps

### Phase 1: Current Capabilities Testing
1. **Test Existing Tools:** Verify filesystem and shell tools work via web UI
2. **Update Agent Instructions:** Modify `AgentCodingAssistantSignature` for coding behavior

### Phase 2: High-Risk Tools (Future)
3. **Create MCP Directory Structure:** Establish `tools/mcp/` directory
4. **Implement WriteFile MCP Server:** Secure file modification
5. **Implement RunTests MCP Server:** Secure test execution

### Phase 3: Advanced Features (Future)
6. **Additional Tools:** Based on usage patterns and requirements
7. **Enhanced Security:** Further refinement of command restrictions
8. **Documentation:** Complete usage documentation

## 7. Architecture Benefits

**✅ Security:** Graduated risk model with appropriate protections  
**✅ Modularity:** Each tool is self-contained and testable  
**✅ Extensibility:** Easy to add new tools following established patterns  
**✅ Performance:** Tools integrate with existing streaming architecture  
**✅ Maintainability:** Clear separation of concerns and documentation
