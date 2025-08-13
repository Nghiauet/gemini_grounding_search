from google import genai
from google.genai import types
from typing import Optional, Dict, Any
import os

class GeminiSearch:
    def __init__(self, model: str = "gemini-2.5-pro", config: Optional[Dict[str, Any]] = None):
        self.model = model
        self.client = genai.Client()
        
        # Default configuration
        default_config = {
            "temperature": 0.1,
            "top_p": 0.8,
            "top_k": 40,
            "structured_temperature": 0.2,
            "structured_top_p": 0.9
        }
        
        # Merge with provided config
        self.config_params = {**default_config, **(config or {})}
        
        # Define the grounding tool
        self.grounding_tool = types.Tool(google_search=types.GoogleSearch())
        
        # Configure generation settings
        self.config = types.GenerateContentConfig(
            tools=[self.grounding_tool],
            temperature=self.config_params["temperature"],
            top_p=self.config_params["top_p"],
            top_k=self.config_params["top_k"]
        )
    
    def search(self, query: str):
        """Perform a grounded search using Gemini with Google Search"""
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
            
        optimized_query = self._optimize_search_query(query)
        
        return self.client.models.generate_content(
            model=self.model,
            contents=optimized_query,
            config=self.config,
        )
    
    def structured_search(self, query: str, schema=None, config=None):
        """Perform a structured search with custom schema"""
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        if config is None and schema is not None:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                temperature=self.config_params["structured_temperature"],
                top_p=self.config_params["structured_top_p"]
            )
        
        if config is None:
            raise ValueError("Either schema or config must be provided for structured search")
        
        return self.client.models.generate_content(
            model=self.model,
            contents=query,
            config=config,
        )
    
    def _optimize_search_query(self, query: str) -> str:
        """Optimize the search query for better grounding results"""
        return f"""
        Search for accurate and current information about: {query}
        
        Focus on finding:
        - Official product specifications
        - Manufacturer documentation
        - Technical datasheets
        - Verified retailer information
        
        Prioritize recent and authoritative sources.
        """
    
    def add_citations(self, response):
        """
        Add inline citations to the response text based on grounding metadata
        
        Args:
            response: The grounded response from Gemini
            
        Returns:
            str: Text with inline citations
        """
        if not hasattr(response, 'candidates') or not response.candidates:
            return response.text
            
        candidate = response.candidates[0]
        if not hasattr(candidate, 'grounding_metadata') or not candidate.grounding_metadata:
            return response.text
            
        text = response.text
        metadata = candidate.grounding_metadata
        
        if not hasattr(metadata, 'grounding_supports') or not hasattr(metadata, 'grounding_chunks'):
            return text
            
        supports = metadata.grounding_supports
        chunks = metadata.grounding_chunks

        # Sort supports by end_index in descending order to avoid shifting issues when inserting.
        sorted_supports = sorted(supports, key=lambda s: s.segment.end_index, reverse=True)

        for support in sorted_supports:
            end_index = support.segment.end_index
            if support.grounding_chunk_indices:
                # Create citation string like [1](link1)[2](link2)
                citation_links = []
                for i in support.grounding_chunk_indices:
                    if i < len(chunks):
                        uri = chunks[i].web.uri
                        citation_links.append(f"[{i + 1}]({uri})")

                citation_string = ", ".join(citation_links)
                text = text[:end_index] + citation_string + text[end_index:]

        return text
    
    def get_grounded_response(self, query):
        """
        Get a grounded response and return both text and metadata
        
        Args:
            query (str): The search query
            
        Returns:
            dict: Dictionary containing response text and grounding metadata
        """
        response = self.search(query)
        
        result = {
            'text': response.text,
            'text_with_citations': self.add_citations(response),
            'grounding_metadata': None,
            'sources_count': 0
        }
        
        # Extract grounding metadata if available
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'grounding_metadata'):
                result['grounding_metadata'] = candidate.grounding_metadata
                
                # Count sources for quality assessment
                if hasattr(candidate.grounding_metadata, 'grounding_chunks'):
                    result['sources_count'] = len(candidate.grounding_metadata.grounding_chunks)
        
        return result
    
    def print_response_with_sources(self, query):
        """
        Print the grounded response with source information
        
        Args:
            query (str): The search query
        """
        result = self.get_grounded_response(query)
        
        print(f"Query: {query}")
        print(f"Response: {result['text']}")
        print(f"Response with citations: {result['text_with_citations']}")
        print(f"Sources found: {result['sources_count']}")
        
        if result['grounding_metadata']:
            metadata = result['grounding_metadata']
            
            if hasattr(metadata, 'web_search_queries'):
                print(f"\nSearch Queries Used: {metadata.web_search_queries}")
            
            if hasattr(metadata, 'grounding_chunks'):
                print("\nSources:")
                for i, chunk in enumerate(metadata.grounding_chunks):
                    if hasattr(chunk, 'web'):
                        print(f"  {i+1}. {chunk.web.title} - {chunk.web.uri}")


