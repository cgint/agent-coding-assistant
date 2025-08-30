from typing import List
import dspy
from dspy_agent_classifier_credentials_passwords import ClassifierCredentialsPasswords
from dspy_agent_util_grounding_manager import GroundingManager
from dspy_agent_tool_rm_tavily import TavilySearchRM, TavilySearchRMResultList

class WebSearchTavilySignature(dspy.Signature):
    question: str = dspy.InputField()
    results: TavilySearchRMResultList = dspy.InputField()
    answer: str = dspy.OutputField(desc="Use the solely the information from the results to answer the question. Do not make up any information.")

def get_domain(url: str) -> str:
    return url.split('/')[2] if '://' in url else url

class WebSearchTavilyModule(dspy.Module):
    def __init__(self, grounding_manager: GroundingManager, include_domains: List[str] | None = None, top_k: int = 5, include_raw_content: bool = False):
        super().__init__()
        self.retriever_tavily = TavilySearchRM(k=top_k, include_raw_content=include_raw_content)
        self.grounding_manager = grounding_manager
        self.include_domains = include_domains
        self.classifier_credentials_passwords = ClassifierCredentialsPasswords()
        self.extractor = dspy.Predict(WebSearchTavilySignature)
    
    def forward(self, query: str) -> str:
        query_classification = self.classifier_credentials_passwords(classify_input=query).classification
        if query_classification != "safe":
            return f"I'm sorry, I can't answer that question because it contains exposed credentials or passwords. Classification: {query_classification}"
        
        results: TavilySearchRMResultList = self.retriever_tavily.forward(query, include_domains=self.include_domains)
        for result in results.results:
            self.grounding_manager.add_source(
                source_type='web',
                title=result.title,
                url=result.url,
                domain=get_domain(result.url)
            )
        return self.extractor(results=results, question=query)

class WebSearchToolTavily(dspy.Tool):
    """A tool that uses Tavily."""
    def __init__(self, grounding_manager: GroundingManager, include_domains: List[str] | None = None, top_k: int = 5, include_raw_content: bool = False):
        # Create the Gemini search tool within closure to avoid Pydantic conflicts
        retriever_tavily_ai = WebSearchTavilyModule(grounding_manager=grounding_manager, include_domains=include_domains, top_k=top_k, include_raw_content=include_raw_content)
        
        # Store grounding_manager in closure for the function
        def search_web(query: str) -> str:
            print(f"--- Calling WebSearchToolTavily with query: '{query}' ---")
            grounding_manager.add_query(f"Web Search: {query}")
            return retriever_tavily_ai(query=query).answer
        
        super().__init__(func=search_web, name="WebSearchTavilyAgent")
