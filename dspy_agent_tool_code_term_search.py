"""
CodeTermSearch tool for the DSPy Agent.
This module provides efficient code searching across both tracked and untracked files
while respecting .gitignore patterns and preventing context overflow.
"""

import subprocess
import logging
import dspy
from typing import Optional, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CodeTermSearchTool(dspy.Tool):
    """
    A tool for searching terms/patterns in the codebase.
    
    Efficiently searches both git-tracked and untracked files while:
    - Respecting .gitignore patterns
    - Supporting file type filtering
    - Preventing context overflow with output limits
    - Providing clean, manageable results
    """
    
    def __init__(self, grounding_manager=None, default_max_results: int = 50, max_output_chars: int = 25000):
        """
        Initialize the CodeTermSearchTool.
        
        Args:
            grounding_manager: Optional grounding manager for tracking tool usage
            default_max_results: Default maximum number of result lines to return (default: 50)
            max_output_chars: Maximum output characters before truncation (default: 25000)
        """
        # Store grounding manager in closure to avoid Pydantic restrictions
        def search_code_term(
            term: str, 
            file_types: Optional[List[str]] = None, 
            max_results: int = default_max_results,
            case_sensitive: bool = False,
            show_line_numbers: bool = True
        ) -> str:
            """
            Search for a term or pattern in the codebase.
            
            Args:
                term: The search term or pattern to find
                file_types: Optional list of file extensions (e.g., ["py", "md", "js"])
                max_results: Maximum number of result lines to return (None uses constructor default)
                case_sensitive: Whether the search should be case sensitive (default: False)
                show_line_numbers: Whether to include line numbers in results (default: True)
                
            Returns:
                Search results as a formatted string
            """
            term = term.strip()
            # Use constructor default if max_results not specified
            logger.info(f"CodeTermSearch: Searching for '{term}' with file_types={file_types}, max_results={max_results}")
            
            # Track the operation if grounding manager is available
            if grounding_manager:
                file_types_str = f" (file types: {file_types})" if file_types else ""
                grounding_manager.add_query(f"Code search: '{term}'{file_types_str}")
            
            try:
                # Build the git ls-files command with optional file type filtering
                if file_types:
                    # Convert file extensions to glob patterns
                    patterns = [f"*.{ext.lstrip('.')}" for ext in file_types]
                    tracked_cmd = f"git ls-files {' '.join(patterns)}"
                    untracked_cmd = f"git ls-files --others --exclude-standard {' '.join(patterns)}"
                else:
                    tracked_cmd = "git ls-files"
                    untracked_cmd = "git ls-files --others --exclude-standard"
                
                # Combine tracked and untracked files
                files_cmd = f"({tracked_cmd}; {untracked_cmd})"
                
                # Build grep options
                grep_options = []
                if not case_sensitive:
                    grep_options.append("-i")
                if show_line_numbers:
                    grep_options.append("-n")
                
                grep_opts_str = " ".join(grep_options)
                
                # Complete search command with result limiting
                search_command = f'{files_cmd} | xargs grep {grep_opts_str} "{term}" 2>/dev/null | head -{max_results}'
                
                logger.info(f"Executing search command: {search_command}")
                
                # Execute the search
                result = subprocess.run(
                    search_command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,  # 30 second timeout
                    cwd=".",     # Run in current directory
                )
                
                # Process results
                if result.stdout:
                    output = result.stdout.strip()
                    
                    # Count actual results
                    lines = output.split('\n') if output else []
                    result_count = len(lines)
                    
                    # Apply safety truncation
                    if len(output) > max_output_chars:
                        truncated_output = output[:max_output_chars]
                        truncated_lines = len(truncated_output.split('\n'))
                        output = f"{truncated_output}\n\n[RESULTS TRUNCATED: Showing {truncated_lines:,} of {result_count:,} total matches]"
                    
                    # Format the final output
                    file_filter_info = f" (filtered to {file_types} files)" if file_types else ""
                    header = f"🔍 Found {result_count} matches for '{term}'{file_filter_info}:\n\n"
                    formatted_output = header + output
                    
                else:
                    # No results found
                    file_filter_info = f" in {file_types} files" if file_types else ""
                    formatted_output = f"🔍 No matches found for '{term}'{file_filter_info}"
                
                # Add source information to grounding
                if grounding_manager:
                    grounding_manager.add_source(
                        source_type='code_search',
                        title=f'Code search: {term}',
                        url=f'search://{term}',
                        domain='local'
                    )
                
                logger.info(f"Search completed. Output length: {len(formatted_output)} chars")
                return formatted_output
                
            except subprocess.TimeoutExpired:
                error_msg = f"❌ Code search for '{term}' timed out after 30 seconds"
                logger.error(error_msg)
                return error_msg
                
            except subprocess.CalledProcessError as e:
                error_msg = f"❌ Code search failed: {e}\nStdout: {e.stdout}\nStderr: {e.stderr}"
                logger.error(f"Search failed: {term} - {error_msg}")
                return error_msg
                
            except Exception as e:
                error_msg = f"❌ Unexpected error during code search: {str(e)}"
                logger.error(f"Unexpected error: {term} - {error_msg}")
                return error_msg
        
        # Initialize the parent dspy.Tool with a clear name and description
        super().__init__(
            func=search_code_term, 
            name="CodeTermSearch",
            desc="Search for terms/patterns in the codebase (both tracked and untracked files). Supports file type filtering and provides clean, limited results."
        )


# Test the tool if run directly
if __name__ == "__main__":
    print("🧪 Testing CodeTermSearch Tool")
    
    # Test with default settings
    print("\n--- Testing with default settings ---")
    search_tool = CodeTermSearchTool()
    
    # Test with custom settings
    print("\n--- Testing with custom settings (max_results=3, max_output_chars=500) ---")
    custom_search_tool = CodeTermSearchTool(default_max_results=3, max_output_chars=500)
    
    # Test searches
    test_searches = [
        {"term": "Assistant", "description": "Basic search for 'Assistant'", "tool": search_tool},
        {"term": "Assistant", "file_types": ["py"], "description": "Search in Python files only", "tool": search_tool},
        {"term": "import", "file_types": ["py"], "max_results": 5, "description": "Search for imports in Python (limited results)", "tool": search_tool},
        {"term": "import", "file_types": ["py"], "description": "Search with custom tool defaults", "tool": custom_search_tool},
    ]
    
    for test in test_searches:
        print(f"\n{'='*60}")
        print(f"Test: {test['description']}")
        print(f"{'='*60}")
        
        # Extract test parameters
        tool_to_use = test.pop('tool', search_tool)
        search_params = {k: v for k, v in test.items() if k not in ['description']}
        
        try:
            result = tool_to_use.func(**search_params)
            print(result)
        except Exception as e:
            print(f"❌ Test failed: {e}")
    
    print(f"\n{'='*60}")
    print("✅ CodeTermSearch tool testing completed")
