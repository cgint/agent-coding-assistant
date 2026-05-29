"""
Gemini-based tool for the DSPy Agent.
This module provides a tool that leverages the Google Gemini CLI to answer arbitrary prompts.
"""

import subprocess
import logging
import dspy
from typing import Optional
from dspy_agent_util_grounding_manager import GroundingManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeminiAskTool(dspy.Tool):  # type: ignore[misc,no-any-unimported]
    """A dspy.Tool that sends a prompt to the Google Gemini CLI and returns the response."""

    model_config = {"extra": "allow"}

    def __init__(self, grounding_manager: Optional[GroundingManager] = None) -> None:
        """Initialise the GeminiAskTool.

        Args:
            grounding_manager: Optional grounding manager for tracking tool usage.
        """

        def ask_gemini(prompt: str) -> str:
            """Send an arbitrary prompt to the Gemini CLI.

            Args:
                prompt: The prompt string to forward to the Gemini CLI.

            Returns:
                The raw output from the Gemini CLI (stdout/stderr combined) or an error message.
            """
            logger.info("GeminiAskTool received prompt: %s", prompt)

            # Track operation if grounding manager is available
            if grounding_manager:
                grounding_manager.add_query(f"Gemini Prompt: {prompt}")

            try:
                logger.info("Executing Gemini CLI with prompt: %s", prompt)
                cmd = [
                    "gemini",
                    "-p",
                    prompt,
                    "-y",  # Assume -y is a confirmation/yes flag analogous to the example
                ]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5-minute timeout similar to the cgiant tool
                    cwd=".",
                )

                # Assemble output
                output_parts = []
                if result.stdout:
                    output_parts.append(f"Gemini Response:\n{result.stdout}")
                if result.stderr:
                    output_parts.append(f"Errors:\n{result.stderr}")
                if result.returncode != 0:
                    output_parts.append(f"Exit code: {result.returncode}")

                output = (
                    "\n".join(output_parts)
                    if output_parts
                    else "Gemini command completed successfully (no output)"
                )

                if grounding_manager:
                    grounding_manager.add_source(
                        source_type="gemini",
                        title=f"Gemini Prompt: {prompt}",
                        url=f"gemini://{prompt}",
                        domain="local",
                    )

                logger.info("Gemini command finished. Output length: %d chars", len(output))
                return output

            except subprocess.TimeoutExpired:
                error_msg = (
                    f"❌ Gemini command timed out after 5 minutes for prompt: {prompt}"
                )
                logger.error(error_msg)
                return error_msg

            except subprocess.CalledProcessError as e:
                error_msg = (
                    f"❌ Gemini command failed with exit code {e.returncode}\nStdout: {e.stdout}\nStderr: {e.stderr}"
                )
                logger.error(error_msg)
                return error_msg

            except FileNotFoundError:
                error_msg = (
                    "❌ gemini CLI not found. Please ensure the Google Gemini CLI is installed and in PATH."
                )
                logger.error(error_msg)
                return error_msg

            except Exception as e:  # pragma: no cover
                error_msg = f"❌ Unexpected error executing Gemini command: {str(e)}"
                logger.error(error_msg)
                return error_msg

        # Initialise the parent dspy.Tool
        super().__init__(func=ask_gemini, name="GeminiAsk")


# Self-test block
if __name__ == "__main__":
    print("🧪 Testing GeminiAskTool")

    test_prompt = (
        "TASK_knowledge_file_assign_project_0_files.md and TASK_knowledge_file_assign_project_1_IDEA.md "
        "contain all project files and the task description. pls add your questions and a first rough plan "
        "on what needs to be adapted to the existing file called TASK_knowledge_file_assign_project_1_IDEA.md"
    )

    tool = GeminiAskTool()  # type: ignore[no-untyped-call]
    result = tool(prompt=test_prompt)
    print(result[:300] + ("…" if len(result) > 300 else ""))
