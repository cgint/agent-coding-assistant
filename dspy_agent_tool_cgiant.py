"""
Cgiant-based tools for the DSPy Agent.
This module provides tools that leverage codegiant.sh for codebase analysis and git diff reviews.
"""

import subprocess
import logging
import dspy
from typing import Optional
from dspy_agent_util_grounding_manager import GroundingManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GiantAskCodebaseTool(dspy.Tool):  # type: ignore[misc,no-any-unimported]
    """A dspy.Tool that asks questions about the entire codebase using codegiant.sh."""

    model_config = {"extra": "allow"}

    def __init__(self, grounding_manager: Optional[GroundingManager] = None) -> None:
        """
        Initialize the GiantAskCodebaseTool.

        Args:
            grounding_manager: Optional grounding manager for tracking tool usage
        """
        # Store grounding manager in closure to avoid Pydantic restrictions
        def ask_codebase(query: str) -> str:
            """
            Ask a question about the entire codebase using codegiant.sh.

            Args:
                query: The question to ask about the codebase

            Returns:
                The response from codegiant.sh or error message
            """
            logger.info(f"GiantAskCodebase tool received query: {query}")

            # Track the operation if grounding manager is available
            if grounding_manager:
                grounding_manager.add_query(f"Codebase Analysis: {query}")

            try:
                logger.info(f"Executing codegiant.sh with query: {query}")

                # Execute the codegiant.sh command
                cmd = ["codegiant.sh", "-F", "-y", "-t", query]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout for complex analysis
                    cwd=".",      # Run in current directory
                )

                # Format output
                output_parts = []
                if result.stdout:
                    output_parts.append(f"Cgiant Analysis:\n{result.stdout}")
                if result.stderr:
                    output_parts.append(f"Errors:\n{result.stderr}")
                if result.returncode != 0:
                    output_parts.append(f"Exit code: {result.returncode}")

                output = "\n".join(output_parts) if output_parts else "Cgiant analysis completed successfully (no output)"

                # Add source information to grounding
                if grounding_manager:
                    grounding_manager.add_source(
                        source_type='cgiant',
                        title=f'Codebase Query: {query}',
                        url=f'cgiant://{query}',
                        domain='local'
                    )

                logger.info(f"Cgiant analysis completed. Output length: {len(output)} chars")
                return output

            except subprocess.TimeoutExpired:
                error_msg = f"❌ Cgiant analysis timed out after 5 minutes for query: {query}"
                logger.error(error_msg)
                return error_msg

            except subprocess.CalledProcessError as e:
                error_msg = f"❌ Cgiant command failed with exit code {e.returncode}\nStdout: {e.stdout}\nStderr: {e.stderr}"
                logger.error(f"Cgiant command failed for query: {query} - {error_msg}")
                return error_msg

            except FileNotFoundError:
                error_msg = "❌ codegiant.sh not found. Please ensure codegiant.sh is installed and available in PATH."
                logger.error(error_msg)
                return error_msg

            except Exception as e:
                error_msg = f"❌ Unexpected error executing cgiant analysis: {str(e)}"
                logger.error(f"Unexpected error for query: {query} - {error_msg}")
                return error_msg

        # Initialize the parent dspy.Tool
        super().__init__(func=ask_codebase, name="GiantAskCodebase")


class GiantReviewGitDiffTool(dspy.Tool):  # type: ignore[misc,no-any-unimported]
    """A dspy.Tool that reviews git diff output using codegiant.sh."""

    model_config = {"extra": "allow"}

    def __init__(self, grounding_manager: Optional[GroundingManager] = None) -> None:
        """
        Initialize the GiantReviewGitDiffTool.

        Args:
            grounding_manager: Optional grounding manager for tracking tool usage
        """
        # Store grounding manager in closure to avoid Pydantic restrictions
        def review_git_diff() -> str:
            """
            Review the current git diff using codegiant.sh.

            Returns:
                The review response from codegiant.sh or error message
            """
            logger.info("GiantReviewGitDiff tool called")

            # Track the operation if grounding manager is available
            if grounding_manager:
                grounding_manager.add_query("Git Diff Code Review")

            try:
                # First, get the git diff output
                logger.info("Executing git diff")
                git_result = subprocess.run(
                    ["git", "diff"],
                    capture_output=True,
                    text=True,
                    timeout=30,  # 30 second timeout for git diff
                    cwd=".",      # Run in current directory
                )

                if git_result.returncode != 0:
                    error_msg = f"❌ Git diff failed with exit code {git_result.returncode}\nStderr: {git_result.stderr}"
                    logger.error(error_msg)
                    return error_msg

                git_diff_output = git_result.stdout.strip()

                if not git_diff_output:
                    msg = "ℹ️ No changes found in git diff (working directory is clean)"
                    logger.info(msg)
                    return msg

                logger.info(f"Git diff captured, length: {len(git_diff_output)} chars")

                # Now run codegiant.sh with the diff
                review_query = f"do a review on severe issues on the following git diff: {git_diff_output}"
                logger.info("Executing codegiant.sh with review query")

                cmd = ["codegiant.sh", "-F", "-y", "-t", review_query]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout for complex review
                    cwd=".",      # Run in current directory
                )

                # Format output
                output_parts = []
                if result.stdout:
                    output_parts.append(f"Cgiant Review:\n{result.stdout}")
                if result.stderr:
                    output_parts.append(f"Errors:\n{result.stderr}")
                if result.returncode != 0:
                    output_parts.append(f"Exit code: {result.returncode}")

                output = "\n".join(output_parts) if output_parts else "Cgiant review completed successfully (no output)"

                # Add source information to grounding
                if grounding_manager:
                    grounding_manager.add_source(
                        source_type='cgiant_review',
                        title='Git Diff Code Review',
                        url='cgiant://git_diff_review',
                        domain='local'
                    )

                logger.info(f"Cgiant review completed. Output length: {len(output)} chars")
                return output

            except subprocess.TimeoutExpired as e:
                cmd_name = "git diff" if "git" in str(e) else "codegiant.sh"
                error_msg = f"❌ {cmd_name} timed out after {'30 seconds' if 'git' in str(e) else '5 minutes'}"
                logger.error(error_msg)
                return error_msg

            except subprocess.CalledProcessError as e:
                cmd_name = "git diff" if "git" in str(e) else "codegiant.sh"
                error_msg = f"❌ {cmd_name} failed with exit code {e.returncode}\nStdout: {e.stdout}\nStderr: {e.stderr}"
                logger.error(error_msg)
                return error_msg

            except FileNotFoundError as e:
                missing_cmd = "git" if "git" in str(e) else "codegiant.sh"
                error_msg = f"❌ {missing_cmd} not found. Please ensure {missing_cmd} is installed and available in PATH."
                logger.error(error_msg)
                return error_msg

            except Exception as e:
                error_msg = f"❌ Unexpected error executing git diff review: {str(e)}"
                logger.error(f"Unexpected error - {error_msg}")
                return error_msg

        # Initialize the parent dspy.Tool
        super().__init__(func=review_git_diff, name="GiantReviewGitDiff")


# Test the tools if run directly
if __name__ == "__main__":
    print("🧪 Testing Cgiant Tools")

    # Test GiantAskCodebase
    print("\n--- Testing GiantAskCodebase Tool ---")
    ask_tool = GiantAskCodebaseTool()  # type: ignore[no-untyped-call]

    test_query = "What is the main purpose of this codebase?"
    print(f"Query: {test_query}")
    result = ask_tool(query=test_query)
    print(f"Result: {result[:300]}...")

    # Test GiantReviewGitDiff
    print("\n--- Testing GiantReviewGitDiff Tool ---")
    review_tool = GiantReviewGitDiffTool()  # type: ignore[no-untyped-call]

    result = review_tool()
    print(f"Result: {result[:300]}...")

    print("\n✅ Cgiant tools testing completed")
