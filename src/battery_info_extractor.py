from typing import Dict, Any, List
from .base_extractor import BaseExtractor
from .models import BatteryInformation


class BatteryInfoExtractor(BaseExtractor):
    """Extract battery information from products"""
    
    def get_extraction_prompt(self, manufacturer: str, part_number: str, description: str) -> str:
        """Generate the prompt for battery information extraction"""
        return f"""
        You are a precise battery information extraction assistant. Extract ONLY verified battery specifications for this exact product:
        
        Product Details:
        - Manufacturer: {manufacturer}
        - Part Number: {part_number}
        - Description: {description}
        
        SEARCH REQUIREMENTS:
        Search using EXACT product identifiers: "{manufacturer} {part_number}" OR "{manufacturer} {part_number} {description}"
        Prioritize official manufacturer websites, technical datasheets, user manuals, and authorized distributors.
        Verify the part number matches exactly - reject information for similar but different part numbers.
        
        REQUIRED OUTPUT (JSON format):
        {{
            "contains_battery": [true/false - does this product contain any battery],
            "battery_count": [number of batteries per unit, 0 if no battery],
            "battery_weight_kg": [weight of single battery in kg to 3 decimals, 0.000 if no battery],
            "battery_type_model": [specific battery type/model like "AA", "18650", "BL-5C", empty string if no battery],
            "battery_chemistry": [battery chemistry like "Li-ion", "NiMH", "Alkaline", "Li-Po", empty string if no battery],
            "is_rechargeable": [true/false - is the battery rechargeable, false if no battery],
            "battery_brand": [battery brand if specified, empty string if not available or no battery],
            "is_integrated": [true if battery is built-in/integrated, false if removable/standalone],
            "reference_sources": [array of 1-5 valid URLs to official sources with exact part number confirmation]
        }}
        
        SEARCH STRATEGY:
        1. Search for: "{manufacturer} {part_number} battery specifications"
        2. Search for: "{manufacturer} {part_number} user manual datasheet"
        3. Search for: "{manufacturer} {part_number} power requirements"
        4. Search manufacturer's official website using part number
        5. Check authorized distributors and technical documentation
        6. Look for FCC ID documents which often contain battery information
        7. Search for product teardowns or technical reviews
        
        VALIDATION RULES:
        - Verify part number EXACTLY matches in all source documents
        - If product has no battery, set contains_battery=false, battery_count=0, battery_weight_kg=0.000
        - For integrated batteries, look for charging specifications and built-in power
        - For standalone batteries, check if they're included or sold separately
        - Battery weight should be realistic for the battery type and product category
        - Common battery chemistries: Li-ion, Li-Po, NiMH, NiCd, Alkaline, Lithium
        - URLs must link to pages that explicitly mention the exact part number
        - Reject information from generic or similar products
        - If battery info not found after thorough search, return contains_battery=false
        
        SPECIAL CONSIDERATIONS:
        - Headsets/audio devices often have rechargeable Li-ion batteries
        - Network testing equipment may use AA/AAA batteries or rechargeable packs
        - Some products may have backup batteries in addition to main power
        - Check for charging docks, USB charging, or external power adapters as indicators
        - Look for battery life specifications in hours as confirmation of battery presence
        
        CRITICAL: Only return battery information if you can verify it's for the EXACT part number provided. 
        Do not use information from similar or related products.
        """
    
    def extract_info(self, manufacturer: str, part_number: str, description: str):
        """Extract structured battery information"""
        self.validate_inputs(manufacturer, part_number, description)
        
        self.logger.info(f"Starting battery info extraction for {manufacturer} - {part_number}")
        
        query = self.get_extraction_prompt(manufacturer, part_number, description)
        
        self.logger.debug(f"Sending query to search client for {manufacturer} - {part_number}")
        response = self.search_client.structured_search(
            query=query,
            schema=BatteryInformation
        )
        
        if hasattr(response, 'parsed') and response.parsed:
            battery_info = response.parsed
            self.logger.info(f"Successfully extracted battery info for {manufacturer} - {part_number}: Battery={battery_info.contains_battery}, Count={battery_info.battery_count}")
            return response
        else:
            self.logger.error(f"No structured data returned from model for {manufacturer} - {part_number}")
            raise ValueError("No structured data returned from model")
    
    def format_output_row(self, manufacturer: str, part_number: str, description: str, extracted_data) -> Dict[str, Any]:
        """Format the extracted data into CSV output format"""
        battery_info = extracted_data.parsed
        sources = self.format_sources(battery_info.reference_sources, 3)
        
        return {
            'Manufacturer': manufacturer,
            'Part Number': part_number,
            'Description': description,
            'Does the product contain a battery?': "Yes" if battery_info.contains_battery else "No",
            'Number of Batteries Per Unit': battery_info.battery_count,
            'Weight of Single Battery (in KG to 3 decimals)': f"{battery_info.battery_weight_kg:.3f}",
            'Battery type or model': battery_info.battery_type_model,
            'Battery Chemistry': battery_info.battery_chemistry,
            'Is the battery rechargeable?': "Yes" if battery_info.is_rechargeable else "No",
            'BATTERY BRAND IF AVAILABLE': battery_info.battery_brand,
            'Is the battery Integrated or Stand Alone': "Integrated" if battery_info.is_integrated else "Stand Alone",
            **sources
        }
    
    def get_output_fieldnames(self) -> List[str]:
        """Get the fieldnames for CSV output"""
        return [
            'Manufacturer', 
            'Part Number', 
            'Description', 
            'Does the product contain a battery?',
            'Number of Batteries Per Unit',
            'Weight of Single Battery (in KG to 3 decimals)',
            'Battery type or model',
            'Battery Chemistry',
            'Is the battery rechargeable?',
            'BATTERY BRAND IF AVAILABLE',
            'Is the battery Integrated or Stand Alone',
            'Source1', 
            'Source2', 
            'Source3'
        ]