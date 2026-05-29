#!/usr/bin/env python3
"""
CLI tool to gather information using code search, web search, and codebase analysis.

This script uses a ReAct agent to intelligently gather information from:
1. CodeTermSearch - Search for terms/patterns in the codebase
2. WebSearchTavilyAgent - Search the web for up-to-date information
3. GiantAskCodebase - Semantic Q&A over the entire codebase

Usage:
    uv run python cli_gather_info.py "How is pricing calculated in the service?"
    uv run python cli_gather_info.py "Explain Gemini cost logic" --verbose
"""

import argparse
import os
import sys

import dspy
from dspy_agent_lm_vertexai import get_vertexai_lm
from dspy_agent_tool_code_term_search import CodeTermSearchTool
from dspy_agent_tool_websearch_tavily import WebSearchToolTavily
from dspy_agent_tool_cgiant import GiantAskCodebaseTool
from dspy_agent_util_grounding_manager import GroundingManager
from dspy_constants import MODEL_NAME_GEMINI_2_5_FLASH


class GatherInfoSignature(dspy.Signature):
    """Signature for gathering information using available tools."""

    context: str = dspy.InputField(desc="The context that describes the environment this question is being asked in")
    question: str = dspy.InputField(desc="The question to gather information about")
    answer: str = dspy.OutputField(desc="The comprehensive answer based on gathered information")


def configure_dspy() -> None:
    """Configure DSPy with Gemini 2.5 Flash model."""
    try:
        # Check for required Vertex AI credentials
        if not os.getenv("VERTEXAI_PROJECT"):
            project = os.getenv("GOOGLE_CLOUD_PROJECT")
            if not project:
                print("❌ VERTEXAI_PROJECT environment variable not set")
                print("   Set it with: export VERTEXAI_PROJECT=your-project-id")
                print("   Or use: export GOOGLE_CLOUD_PROJECT=your-project-id")
                sys.exit(1)
            os.environ["VERTEXAI_PROJECT"] = project

        if not os.getenv("VERTEXAI_LOCATION"):
            location = os.getenv("GOOGLE_CLOUD_LOCATION") or "us-central1"
            os.environ["VERTEXAI_LOCATION"] = location

        # Configure DSPy
        dspy.settings.configure(
            lm=get_vertexai_lm(
                model=f"vertex_ai/{MODEL_NAME_GEMINI_2_5_FLASH}",
                reasoning_effort="disable",
            ),
            track_usage=True,
        )

        # Disable caching for fresh results
        dspy.configure_cache(
            enable_disk_cache=False,
            enable_memory_cache=False,
            enable_litellm_cache=False
        )

        print(f"✅ DSPy configured with {dspy.settings.lm.model}")
    except Exception as e:
        print(f"❌ Error configuring DSPy: {e}")
        print("   Make sure you have:")
        print("   - Valid VertexAI credentials")
        print("   - GOOGLE_APPLICATION_CREDENTIALS set (if using service account)")
        sys.exit(1)


def create_tools(grounding_manager: GroundingManager):
    """Create the information gathering tools."""
    tools = []

    # Create code search tool (always available)
    code_search_tool = CodeTermSearchTool(grounding_manager=grounding_manager)
    tools.append(code_search_tool)
    print("✅ Code search tool ready")

    # Create web search tool (requires Tavily API key)
    web_search_tool = WebSearchToolTavily(
        grounding_manager=grounding_manager,
        top_k=10,
        include_raw_content=True
    )
    tools.append(web_search_tool)
    print("✅ Web search tool ready")

    # Create GiantAskCodebase tool (requires codegiant.sh)
    giant_ask_tool = GiantAskCodebaseTool(grounding_manager=grounding_manager)
    tools.append(giant_ask_tool)
    print("✅ Codebase analysis tool ready")

    return tools


def create_react_agent(tools):
    """Create a ReAct agent with the information gathering tools."""
    return dspy.ReAct(GatherInfoSignature, tools=tools)


def print_grounding_info(grounding_manager: GroundingManager, verbose: bool = False):
    """Print grounding information from all tools."""

    if grounding_manager.queries and verbose:
        print("\n🔍 **Queries Made:**")
        for query in grounding_manager.queries[:5]:  # Limit to avoid clutter
            print(f"  - {query}")

    if grounding_manager.sources and verbose:
        print("\n📚 **Sources Used:**")
        for source in grounding_manager.sources[:8]:  # Limit to avoid clutter
            title = source.get('title', 'Unknown')
            domain = source.get('domain', 'N/A')
            print(f"  - {title} ({domain})")


def main():
    """Main CLI entry point."""
    try:
        parser = argparse.ArgumentParser(
            description="Gather information using code search, web search, and codebase analysis",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  uv run python cli_gather_info.py "How is pricing calculated in the service?"
  uv run python cli_gather_info.py "Explain Gemini cost logic" --verbose
  uv run python cli_gather_info.py "What are the main components?" --session-id abc123
            """
        )

        parser.add_argument(
            "question",
            help="The question to gather information about"
        )

        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Show detailed information including tool calls and sources"
        )

        parser.add_argument(
            "--session-id",
            help="Optional session identifier for tracking"
        )

        args = parser.parse_args()

        # Configure DSPy
        configure_dspy()

        # Create tools and grounding managers
        grounding_manager = GroundingManager()
        tools = create_tools(grounding_manager=grounding_manager)

        # Create ReAct agent
        react_agent = create_react_agent(tools)

        print(f"🤖 Gathering information for: {args.question}")
        print("=" * 60)

        # Add README.md as context if it exists
        readme_content = ""
        readme_path = "README.md"
        if os.path.exists(readme_path):
            try:
                with open(readme_path, 'r', encoding='utf-8') as f:
                    readme_content = f.read()
                print("📖 Adding README.md as context...")
            except Exception as e:
                print(f"⚠️  Could not read README.md: {e}")
        

        # Run the agent
        result = react_agent(question=args.question, context=readme_content)

        # Print the answer
        print("\n💡 **Answer:**")
        print(result.answer)

        # Print grounding information if verbose
        if args.verbose:
            print_grounding_info(grounding_manager, verbose=True)

        print("\n✅ Information gathering completed successfully")

    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during information gathering: {e}")
        print("\nTroubleshooting tips:")
        print("• Make sure all required API keys are set")
        print("• Check that codegiant.sh is installed and in PATH")
        print("• Verify VertexAI credentials are valid")
        print("• Try running with --verbose for more details")

        # Print full traceback in verbose mode
        if len(sys.argv) > 1 and ("--verbose" in sys.argv or "-v" in sys.argv):
            import traceback
            print("\nFull error traceback:")
            traceback.print_exc()

        sys.exit(1)


if __name__ == "__main__":
    main()
