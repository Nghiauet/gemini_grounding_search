from typing import Dict, Any, List
from .base_extractor import BaseExtractor
from .models import ProductSpecification


class ProductSpecsExtractor(BaseExtractor):
    """Extract product specifications (dimensions and weight)"""
    
    def get_extraction_prompt(self, manufacturer: str, part_number: str, description: str) -> str:
        """Generate the prompt for product specification extraction"""
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
    
    def extract_info(self, manufacturer: str, part_number: str, description: str):
        """Extract structured product specifications"""
        self.validate_inputs(manufacturer, part_number, description)
        
        query = self.get_extraction_prompt(manufacturer, part_number, description)
        
        response = self.search_client.structured_search(
            query=query,
            schema=ProductSpecification
        )
        
        if hasattr(response, 'parsed') and response.parsed:
            return response
        else:
            raise ValueError("No structured data returned from model")
    
    def format_output_row(self, manufacturer: str, part_number: str, description: str, extracted_data) -> Dict[str, Any]:
        """Format the extracted data into CSV output format"""
        specs = extracted_data.parsed
        sources = self.format_sources(specs.reference_sources, 3)
        
        return {
            'Manufacturer': manufacturer,
            'Part Number': part_number,
            'Description': description,
            'Product Weight in kg (3 decimals)': f"{specs.weight_kg:.3f}" if specs.weight_kg else "",
            'Dim (L) CM': specs.length_cm if specs.length_cm else "",
            'Dim (W) CM': specs.width_cm if specs.width_cm else "",
            'Dim (H) CM': specs.height_cm if specs.height_cm else "",
            **sources
        }
    
    def get_output_fieldnames(self) -> List[str]:
        """Get the fieldnames for CSV output"""
        return [
            'Manufacturer', 
            'Part Number', 
            'Description', 
            'Product Weight in kg (3 decimals)', 
            'Dim (L) CM', 
            'Dim (W) CM', 
            'Dim (H) CM', 
            'Source1', 
            'Source2', 
            'Source3'
        ]