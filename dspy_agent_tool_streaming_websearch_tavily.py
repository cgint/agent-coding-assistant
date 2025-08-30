from typing import Optional
from dspy_agent_tool_websearch_tavily import WebSearchToolTavily
from dspy_agent_util_streaming_grounding_manager import StreamingGroundingManager


class StreamingWebSearchToolTavily(WebSearchToolTavily):
    """WebSearchToolTavily variant that can emit grounding updates via async manager methods."""

    model_config = {"extra": "allow"}

    def __init__(
        self,
        grounding_manager: StreamingGroundingManager,
        include_domains: Optional[list[str]] = None,
        top_k: int = 5,
        include_raw_content: bool = False,
    ) -> None:
        super().__init__(
            grounding_manager,
            include_domains=include_domains,
            top_k=top_k,
            include_raw_content=include_raw_content,
        )
        # Override with streaming grounding manager and store config for async flow
        self.grounding_manager = grounding_manager
        self.include_domains = include_domains
        self.top_k = top_k
        self.include_raw_content = include_raw_content

    async def call_async(self, query: str) -> str:
        """Async execution path that emits grounding updates via the StreamingGroundingManager."""
        # Add query to grounding first (emits grounding_update)
        await self.grounding_manager.add_query_async(query)

        # Execute web search
        from tavily import TavilyClient
        import os

        tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

        # Perform the search, only include optional args when defined
        search_kwargs = {
            "query": query,
            "max_results": self.top_k,
            "include_raw_content": self.include_raw_content,
        }
        if self.include_domains is not None:
            search_kwargs["include_domains"] = self.include_domains

        response = tavily_client.search(**search_kwargs)

        # Process results and add sources
        results: list[str] = []
        if response and 'results' in response:
            for result in response['results']:
                # Add source to grounding manager (emits events automatically)
                await self.grounding_manager.add_source_async(
                    source_type="web",
                    title=result.get('title', 'Web Result'),
                    url=result.get('url', ''),
                    domain=result.get('url', '').split('/')[2] if '://' in result.get('url', '') else ''
                )

                # Collect content
                content = result.get('content', '')
                if content:
                    results.append(
                        f"Title: {result.get('title', 'N/A')}\nContent: {content}\nURL: {result.get('url', 'N/A')}\n"
                    )

        final_result = "\n---\n".join(results) if results else "No relevant web search results found."
        return final_result

    async def acall(self, query: str) -> str:  # DSPy-native async tool entrypoint
        return await self.call_async(query)
