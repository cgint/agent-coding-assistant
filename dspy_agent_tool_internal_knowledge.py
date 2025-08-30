import dspy
import os
from dspy_agent_util_grounding_manager import GroundingManager

def _read_internal_document() -> str:
    """
    Reads a document from the internal knowledge base.
    """
    filepath = os.path.join("knowledge_base", "internal_notes.md")
    with open(filepath, 'r') as f:
        return f.read()


class InternalKnowledgeSignature(dspy.Signature):
    """You are a specialist in the company's internal knowledge base. 
    The knowledge base content provided to you is a copy of our central knowledge base system.
    Links to that system are provided in the knowledge base content starting with "https://smec.atlassian.net".
    
    You have access to the full internal knowledge base content.
    IMPORTANT: You must use the full knowledge base content to answer the user's question.
    IMPORTANT: You must ONLY use the knowledge base content to answer the user's question.

    Your task is to:
    1. Analyze the user's query carefully
    2. Extract and return ONLY the relevant information from the knowledge base
    3. Be comprehensive but concise - include all relevant details without unnecessary content
    4. If no relevant information is found, clearly state that
    5. provide links to the relevant information in the knowledge base
    
    Focus on providing accurate, specific information that directly answers the user's question.
    """
    knowledge_base: str = dspy.InputField(desc="The full internal knowledge base content")
    query: str = dspy.InputField(desc="The user's question or search query")
    relevant_info: str = dspy.OutputField(desc="Only the relevant information from the knowledge base")


class InternalKnowledgeAgent(dspy.Module):
    """A dedicated agent that processes internal knowledge base queries efficiently."""
    
    def __init__(self):
        super().__init__()
        self.extractor = dspy.Predict(InternalKnowledgeSignature)
    
    def forward(self, query: str) -> str:
        """Process query against full knowledge, return only relevant parts."""
        # === DEBUGGING: Check what LM is being used ===
        print(f"🔧 InternalKnowledgeAgent.forward called with query: '{query}'")
        print(f"🔧 Current dspy.settings.lm: {type(dspy.settings.lm)}")
        print(f"🔧 self.extractor uses LM: {type(getattr(self.extractor, 'lm', 'No LM found'))}")
        
        # Extract only relevant information using the LLM
        result = self.extractor(
            knowledge_base=_read_internal_document(),
            query=query
        )
        
        print(f"🔧 InternalKnowledgeAgent result: {result.relevant_info[:100]}...")
        
        return result.relevant_info


class InternalKnowledgeTool(dspy.Tool):
    """A tool to retrieve information from an internal knowledge base."""
    def __init__(self, grounding_manager: GroundingManager):
        # Create the internal knowledge agent once at initialization
        knowledge_agent = InternalKnowledgeAgent()
        
        # Store grounding_manager in closure for the function
        def search_internal(query: str) -> str:
            print(f"--- Calling InternalKnowledgeAgent with query: '{query}' ---")
            grounding_manager.add_query(f"Internal Knowledge: {query}")
            
            # Get only relevant information from the knowledge agent
            relevant_info = knowledge_agent(query=query)
            
            if relevant_info.startswith("Error:"):
                return relevant_info
            
            # Add source information
            grounding_manager.add_source(
                source_type='internal',
                title='Internal Knowledge Base',
                url='file://knowledge_base/internal_notes.md',
                domain='internal'
            )
            
            return relevant_info
        
        super().__init__(func=search_internal, name="InternalKnowledgeAgent")
