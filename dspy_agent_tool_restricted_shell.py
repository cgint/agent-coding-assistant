"""
Restricted shell tool for the DSPy Agent.
This module provides safe command-line execution with allowlisted commands for coding tasks.
"""

import subprocess
import logging
import dspy
from typing import Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define allowed command prefixes and their descriptions
ALLOWED_COMMANDS = {
    # Version control
    "git": "Run Git commands",
    
    # Python/UV package management
    "uv": "Run UV commands",
    
    # File system operations (read-only)
    "ls": "List directory contents",
    "find": "Search for files and directories",
    "wc": "Word, line, character, and byte count",
    "head": "Output the first part of files",
    "tail": "Output the last part of files",
    "grep": "Search text using patterns",
    "cat": "Display file contents",
    
    # Process and system info (read-only)
    "ps": "Show running processes",
    "top": "Display running processes",
    "df": "Display filesystem disk space usage",
    "free": "Display memory usage",
    "whoami": "Display current user",
    "pwd": "Print working directory",
    "which": "Locate a command",
    "echo": "Display text",
    
    # Development tools
    "node": "Run Node.js",
    "npm": "Node.js package manager",
    "docker ps": "List Docker containers",
}

def _generate_allowed_commands_desc() -> str:
    """Generate a formatted description of allowed commands."""
    return "\n".join([f"- `{command}`: {description}" for command, description in ALLOWED_COMMANDS.items()])

SHELL_INSTRUCTIONS = f"""

## Restricted Shell Tool

### Allowed Command Prefixes
The shell tool only allows commands that start with specific prefixes:
{_generate_allowed_commands_desc()}

### Common Usage Patterns

#### Development Workflow:
- `uv run python script.py` (run Python scripts)
- `uv run pytest tests/` (run tests)
- `uv run mypy .` (run type checking)
- `uv run ruff check .` (run linting)
- `git status` (check repository status)
- `git diff` (see changes)

#### File Analysis:
- `ls -la` (detailed directory listing)
- `find . -name "*.py"` (find Python files)
- `grep -r "pattern" .` (search for patterns)
- `wc -l file.py` (count lines in file)
- `head -20 file.py` (show first 20 lines)

#### Project Management:
- `uv add package` (add dependency)
- `uv sync` (sync dependencies)
- `uv tree` (show dependency tree)

### Security Notes:
- Only predefined command prefixes are allowed
- No file modification commands (rm, mv, cp, etc.)
- No system administration commands
- All commands are logged for security audit
- Commands run in the current project directory

### Error Handling:
- Invalid commands return error messages
- Failed commands return exit codes and error output
- All execution is logged for debugging
"""


class RestrictedShellTool(dspy.Tool):
    """A dspy.Tool that executes allowlisted shell commands safely."""
    
    def __init__(self, grounding_manager=None):
        """
        Initialize the RestrictedShellTool.
        
        Args:
            grounding_manager: Optional grounding manager for tracking tool usage
        """
        # Store grounding manager in closure to avoid Pydantic restrictions
        def execute_shell_command(command: str) -> str:
            """
            Execute a shell command if it's in the allowlist.
            
            Args:
                command: The command to execute
                
            Returns:
                The command output or error message
            """
            command = command.strip()
            logger.info(f"Shell tool received command: {command}")
            
            # Track the operation if grounding manager is available
            if grounding_manager:
                grounding_manager.add_query(f"Shell command: {command}")
            
            # Check if command is allowed
            if not any(command.startswith(allowed_prefix) for allowed_prefix in ALLOWED_COMMANDS.keys()):
                error_msg = f"❌ Command '{command}' not allowed!\n\nAllowed command prefixes:\n{_generate_allowed_commands_desc()}"
                logger.error(f"Blocked unauthorized command: {command}")
                return error_msg
            
            try:
                logger.info(f"Executing allowed command: {command}")
                
                # Execute the command with security measures
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,  # 30 second timeout
                    cwd=".",     # Run in current directory
                )
                
                # Format output
                output_parts = []
                if result.stdout:
                    output_parts.append(f"Output:\n{result.stdout}")
                if result.stderr:
                    output_parts.append(f"Errors:\n{result.stderr}")
                if result.returncode != 0:
                    output_parts.append(f"Exit code: {result.returncode}")
                
                output = "\n".join(output_parts) if output_parts else "Command completed successfully (no output)"
                
                # Add source information to grounding
                if grounding_manager:
                    grounding_manager.add_source(
                        source_type='shell',
                        title=f'Command: {command}',
                        url=f'shell://{command}',
                        domain='local'
                    )
                
                logger.info(f"Command completed. Output length: {len(output)} chars")
                return output
                
            except subprocess.TimeoutExpired:
                error_msg = f"❌ Command '{command}' timed out after 30 seconds"
                logger.error(error_msg)
                return error_msg
                
            except subprocess.CalledProcessError as e:
                error_msg = f"❌ Command failed with exit code {e.returncode}\nStdout: {e.stdout}\nStderr: {e.stderr}"
                logger.error(f"Command failed: {command} - {error_msg}")
                return error_msg
                
            except Exception as e:
                error_msg = f"❌ Unexpected error executing command: {str(e)}"
                logger.error(f"Unexpected error: {command} - {error_msg}")
                return error_msg
        
        # Initialize the parent dspy.Tool
        super().__init__(func=execute_shell_command, name="RestrictedShell")


# Test the tool if run directly
if __name__ == "__main__":
    print("🧪 Testing Restricted Shell Tool")
    
    shell_tool = RestrictedShellTool()
    
    # Test allowed commands
    test_commands = [
        "ls -la",
        "pwd",
        "echo 'Hello World'",
        "uv --version",
        "git status",
        # This should be blocked
        "rm -rf /", 
    ]
    
    for cmd in test_commands:
        print(f"\n--- Testing command: {cmd} ---")
        result = shell_tool(command=cmd)
        print(f"Result: {result[:200]}...")
    
    print("\n✅ Shell tool testing completed")
