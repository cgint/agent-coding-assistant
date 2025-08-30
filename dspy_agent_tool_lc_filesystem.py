"""
LangChain-based filesystem tools for the DSPy Agent.
This module provides filesystem operations using LangChain's pre-built tools.
"""

import dspy
from langchain_community.tools import ReadFileTool, ListDirectoryTool, WriteFileTool


class LangChainReadFileTool(dspy.Tool):
    """A dspy.Tool wrapper for LangChain's ReadFileTool."""

    model_config = {"extra": "allow"}

    def __init__(self, grounding_manager=None):
        """
        Initialize the ReadFileTool wrapper.
        
        Args:
            grounding_manager: Optional grounding manager for tracking tool usage
        """
        # Store grounding manager in closure to avoid Pydantic restrictions
        def read_file_func(file_path: str) -> str:
            """Read the contents of a file from the filesystem."""
            print(f"--- Reading file: {file_path} ---")
            
            # Track the operation if grounding manager is available
            if grounding_manager:
                grounding_manager.add_query(f"Read file: {file_path}")
            
            try:
                # Use LangChain's ReadFileTool
                langchain_tool = ReadFileTool()
                result = langchain_tool.run(file_path)
                
                # Add source information to grounding
                if grounding_manager:
                    grounding_manager.add_source(
                        source_type='filesystem',
                        title=f'File: {file_path}',
                        url=f'file://{file_path}',
                        domain='local'
                    )
                
                return result
                
            except Exception as e:
                error_msg = f"Error reading file {file_path}: {str(e)}"
                print(f"❌ {error_msg}")
                return error_msg
        
        # Initialize the parent dspy.Tool
        super().__init__(func=read_file_func, name="ReadFileTool")


class LangChainListDirectoryTool(dspy.Tool):
    """A dspy.Tool wrapper for LangChain's ListDirectoryTool."""

    model_config = {"extra": "allow"}

    def __init__(self, grounding_manager=None):
        """
        Initialize the ListDirectoryTool wrapper.
        
        Args:
            grounding_manager: Optional grounding manager for tracking tool usage
        """
        # Store grounding manager in closure to avoid Pydantic restrictions
        def list_directory_func(directory_path: str) -> str:
            """List the contents of a directory."""
            print(f"--- Listing directory: {directory_path} ---")
            
            # Track the operation if grounding manager is available
            if grounding_manager:
                grounding_manager.add_query(f"List directory: {directory_path}")
            
            try:
                # Use LangChain's ListDirectoryTool
                langchain_tool = ListDirectoryTool()
                result = langchain_tool.run(directory_path)
                
                # Add source information to grounding
                if grounding_manager:
                    grounding_manager.add_source(
                        source_type='filesystem',
                        title=f'Directory: {directory_path}',
                        url=f'file://{directory_path}',
                        domain='local'
                    )
                
                return result
                
            except Exception as e:
                error_msg = f"Error listing directory {directory_path}: {str(e)}"
                print(f"❌ {error_msg}")
                return error_msg
        
        # Initialize the parent dspy.Tool
        super().__init__(func=list_directory_func, name="ListDirectoryTool")


class LangChainWriteFileTool(dspy.Tool):
    """A dspy.Tool wrapper for LangChain's WriteFileTool."""

    model_config = {"extra": "allow"}

    def __init__(self, grounding_manager=None):
        """
        Initialize the WriteFileTool wrapper.

        Args:
            grounding_manager: Optional grounding manager for tracking tool usage
        """
        # Store grounding manager in closure to avoid Pydantic restrictions
        def write_file_func(file_path: str, text: str, append: bool = False) -> str:
            """Write content to a file on the filesystem."""
            operation = "appending to" if append else "writing to"
            print(f"--- {operation.capitalize()} file: {file_path} ---")

            # Track the operation if grounding manager is available
            if grounding_manager:
                grounding_manager.add_query(f"Write file: {file_path}")

            try:
                # Use LangChain's WriteFileTool
                langchain_tool = WriteFileTool()
                result = langchain_tool.run({
                    "file_path": file_path,
                    "text": text,
                    "append": append
                })

                # Add source information to grounding
                if grounding_manager:
                    grounding_manager.add_source(
                        source_type='filesystem',
                        title=f'File: {file_path}',
                        url=f'file://{file_path}',
                        domain='local'
                    )

                success_msg = f"Successfully {'appended to' if append else 'wrote to'} file: {file_path}"
                print(f"✅ {success_msg}")
                return success_msg

            except Exception as e:
                error_msg = f"Error {'appending to' if append else 'writing to'} file {file_path}: {str(e)}"
                print(f"❌ {error_msg}")
                return error_msg

        # Initialize the parent dspy.Tool
        super().__init__(func=write_file_func, name="WriteFileTool")


# Test the tools if run directly
if __name__ == "__main__":
    print("🧪 Testing LangChain Filesystem Tools")
    
    # Test ReadFileTool
    read_tool = LangChainReadFileTool()
    print("\n--- Testing ReadFileTool ---")
    result = read_tool(file_path="TASK_add_coding_1_PLAN.md")
    print(f"Read result preview: {result[:200]}...")
    
    # Test ListDirectoryTool
    list_tool = LangChainListDirectoryTool()
    print("\n--- Testing ListDirectoryTool ---")
    result = list_tool(directory_path=".")
    print(f"Directory listing: {result}")

    # Test WriteFileTool
    write_tool = LangChainWriteFileTool()
    print("\n--- Testing WriteFileTool ---")
    test_content = "This is a test file created by LangChainWriteFileTool."
    result = write_tool(file_path="test_output.txt", text=test_content)
    print(f"Write result: {result}")

    # Test append functionality
    append_content = "\nThis is appended content."
    result = write_tool(file_path="test_output.txt", text=append_content, append=True)
    print(f"Append result: {result}")

    print("\n✅ Tool testing completed")
