from google import genai
from google.genai import types
from pydantic import BaseModel, Field, field_validator
from typing import List
import re

MODEL = "gemini-2.5-pro"

class ProductSpecification(BaseModel):
    weight_kg: float = Field(..., description="Product weight in kilograms")
    length_cm: float = Field(..., description="Product length in centimeters")
    width_cm: float = Field(..., description="Product width in centimeters")
    height_cm: float = Field(..., description="Product height in centimeters")
    reference_sources: List[str] = Field(..., min_length=1, max_length=5, description="Reference source URLs")
    
    @field_validator('weight_kg', 'length_cm', 'width_cm', 'height_cm')
    @classmethod
    def validate_positive(cls, v):
        if v <= 0:
            raise ValueError(f"Value must be greater than 0, got {v}")
        return v
    
    @field_validator('reference_sources')
    @classmethod
    def validate_urls(cls, v):
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        for url in v:
            if not url_pattern.match(url):
                raise ValueError(f"Invalid URL format: {url}")
        return v

class GeminiSearch:
    def __init__(self):
        # Configure the client
        self.client = genai.Client()
        
        # Define the grounding tool with optimized search parameters
        self.grounding_tool = types.Tool(
            google_search=types.GoogleSearch()
        )
        
        # Configure generation settings with optimized parameters
        self.config = types.GenerateContentConfig(
            tools=[self.grounding_tool],
            temperature=0.1,  # Lower temperature for more consistent results
            top_p=0.8,
            top_k=40
        )
        
        # Configure structured output settings with validation
        self.structured_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ProductSpecification,
            temperature=0.2,  # Slightly higher for structured output creativity
            top_p=0.9
        )
    
    def search(self, query):
        """
        Perform a grounded search using Gemini with Google Search
        
        Args:
            query (str): The search query
            
        Returns:
            response: The grounded response from Gemini
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
            
        # Optimize query for better search results
        optimized_query = self._optimize_search_query(query)
        
        # Make the request
        response = self.client.models.generate_content(
            model=MODEL,
            contents=optimized_query,
            config=self.config,
        )
        
        return response
    
    def structured_search(self, query, schema=None, config=None):
        """
        Perform a structured search with custom schema and configuration
        
        Args:
            query (str): The search query
            schema: Pydantic model class for structured output (optional)
            config: Custom configuration (optional)
            
        Returns:
            response: The structured response from Gemini
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        # Use provided config or fall back to default structured config
        if config is None:
            if schema is not None:
                # Create a custom config with the provided schema
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.2,
                    top_p=0.9
                )
            else:
                config = self.structured_config
        
        # Make the request
        response = self.client.models.generate_content(
            model=MODEL,
            contents=query,
            config=config,
        )
        
        return response
    
    def _optimize_search_query(self, query):
        """
        Optimize the search query for better grounding results
        
        Args:
            query (str): Original query
            
        Returns:
            str: Optimized query
        """
        # Add search optimization instructions
        optimized = f"""
        Search for accurate and current information about: {query}
        
        Focus on finding:
        - Official product specifications
        - Manufacturer documentation
        - Technical datasheets
        - Verified retailer information
        
        Prioritize recent and authoritative sources.
        """
        return optimized
    
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

class ProductSpecsExtractor:
    def __init__(self, search_client=None):
        self.search_client = search_client or GeminiSearch()
    
    def get_product_specs_prompt(self, manufacturer, part_number, description):
        """
        Generate the prompt for product specification extraction
        
        Args:
            manufacturer (str): Product manufacturer
            part_number (str): Product part number
            description (str): Product description
            
        Returns:
            str: The formatted prompt
        """
        return f"""
        You are a precise product specification extraction assistant. Extract ONLY verified technical specifications for this exact product:
        
        Product Details:
        - Manufacturer: {manufacturer}
        - Part Number: {part_number}
        - Description: {description}
        
        SEARCH REQUIREMENTS:
        Search using EXACT product identifiers: "{manufacturer} {part_number}" OR "{manufacturer} {part_number} {description}"
        Prioritize official manufacturer websites, technical datasheets, and authorized distributors.
        Verify the part number matches exactly - reject specifications for similar but different part numbers.
        
        REQUIRED OUTPUT (JSON format):
        {{
            "weight_kg": [exact weight in kg as decimal number, must be > 0],
            "length_cm": [exact length in cm as decimal number, must be > 0],
            "width_cm": [exact width in cm as decimal number, must be > 0],
            "height_cm": [exact height in cm as decimal number, must be > 0],
            "reference_sources": [array of 1-5 valid URLs to official sources with exact part number confirmation]
        }}
        
        SEARCH STRATEGY:
        1. Search for: "{manufacturer} {part_number} specifications datasheet"
        2. Search for: "{manufacturer} {part_number} dimensions weight"
        3. Search manufacturer's official website using part number
        4. Check authorized distributors: Digi-Key, Mouser, Arrow, etc.
        5. Look for technical documentation and product manuals
        6. Cross-reference multiple sources to ensure part number accuracy
        
        VALIDATION RULES:
        - Verify part number EXACTLY matches in all source documents
        - All measurements must be positive numbers
        - Weight should be realistic for the product type and category
        - Dimensions should be consistent across sources
        - URLs must link to pages that explicitly mention the exact part number
        - Reject specifications from generic or similar products
        - If exact specs not found after thorough search, return null values rather than estimates
        
        CRITICAL: Only return specifications if you can verify they are for the EXACT part number provided. 
        Do not use specifications from similar or related products.
        """
    
    def extract_product_specs(self, manufacturer, part_number, description):
        """
        Extract structured product specifications using structured output with validation
        
        Args:
            manufacturer (str): Product manufacturer
            part_number (str): Product part number
            description (str): Product description
            
        Returns:
            ProductSpecification: Validated structured product specifications
        """
        # Input validation
        if not all([manufacturer.strip(), part_number.strip(), description.strip()]):
            raise ValueError("All product identifiers (manufacturer, part_number, description) must be provided")
        
        # Generate the prompt
        query = self.get_product_specs_prompt(manufacturer, part_number, description)
        
        try:
            response = self.search_client.structured_search(
                query=query,
                schema=ProductSpecification
            )
            
            # Validate the parsed response
            if hasattr(response, 'parsed') and response.parsed:
                # Additional business logic validation
                specs = response.parsed
                return response
            else:
                raise ValueError("No structured data returned from model")
                
        except Exception as e:
            print(f"Structured extraction failed: {e}")
            raise

def convert_specs_to_imperial(specs):
    """
    Convert metric specifications to imperial units
    
    Args:
        specs (ProductSpecification): Specifications in metric units
        
    Returns:
        dict: Converted specifications with imperial units
    """
    # Convert kg to pounds (1 kg = 2.20462 lbs)
    weight_lbs = specs.weight_kg * 2.20462
    
    # Convert cm to inches (1 cm = 0.393701 inches)
    length_in = specs.length_cm * 0.393701
    width_in = specs.width_cm * 0.393701
    height_in = specs.height_cm * 0.393701
    
    return {
        'weight_lbs': weight_lbs,
        'length_in': length_in,
        'width_in': width_in,
        'height_in': height_in
    }

