from typing import List, Dict, Any

class GroundingManager:
    """A simple class to manage grounding metadata during an agent's run."""
    def __init__(self) -> None:
        self.sources: List[Dict[str, Any]] = []
        self.queries: List[str] = []
        self.supports: List[Dict[str, Any]] = []

    def add_source(self, source_type: str, title: str, url: str, domain: str = "") -> None:
        self.sources.append({"type": source_type, "title": title, "url": url, "domain": domain})

    def add_query(self, query: str) -> None:
        self.queries.append(query)

    def reset(self) -> None:
        self.sources = []
        self.queries = []
        self.supports = []

    def format_for_display(self) -> str:
        """Formats the collected grounding information for display."""
        if not self.sources and not self.queries:
            return ""
        
        formatted_sections = []
        
        if self.sources:
            formatted_sections.append("\n\n📚 **Sources & References:**\n")
            for source in self.sources[:6]:
                title = source.get('title', 'Source')
                url = source.get('url', '')
                display_domain = source.get('domain') or (url.split('/')[2] if '://' in url else url)
                formatted_sections.append(f"- [{title}]({url}) - {display_domain}")
        
        if self.queries:
            formatted_sections.append("\n\n🔍 **Search Queries Used:**\n")
            for query in self.queries[:4]:
                formatted_sections.append(f"- \"{query}\"")
        
        return '\n'.join(formatted_sections)
