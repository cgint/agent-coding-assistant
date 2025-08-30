"""
LangChain-based filesystem tools for the DSPy Agent.
This module provides safe, read-only filesystem operations using LangChain's pre-built tools.
"""

import dspy
from langchain_community.tools import ReadFileTool, ListDirectoryTool
from typing import Any


class LangChainReadFileTool(dspy.Tool):
    """A dspy.Tool wrapper for LangChain's ReadFileTool."""
    
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
    
    print("\n✅ Tool testing completed")
