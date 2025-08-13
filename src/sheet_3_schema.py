import csv
from gemini_grounding_search import GeminiSearch
from pydantic import BaseModel, Field, field_validator
from typing import List
import re
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sheet_3_processing.log'),
        logging.StreamHandler()
    ]
)

class BatteryInformation(BaseModel):
    contains_battery: bool = Field(..., description="Whether the product contains a battery")
    battery_count: int = Field(..., ge=0, description="Number of batteries per unit (0 if no battery)")
    battery_weight_kg: float = Field(..., ge=0, description="Weight of single battery in kilograms (0 if no battery)")
    battery_type_model: str = Field(..., description="Battery type or model (empty string if no battery)")
    battery_chemistry: str = Field(..., description="Battery chemistry (e.g., Li-ion, NiMH, Alkaline)")
    is_rechargeable: bool = Field(..., description="Whether the battery is rechargeable")
    battery_brand: str = Field(..., description="Battery brand if available (empty string if not available)")
    is_integrated: bool = Field(..., description="True if integrated, False if standalone")
    reference_sources: List[str] = Field(..., min_length=1, max_length=5, description="Reference source URLs")

    @field_validator('battery_weight_kg')
    @classmethod
    def validate_battery_weight(cls, v, info):
        # If no battery, weight should be 0
        contains_battery = info.data.get('contains_battery', False)
        if not contains_battery and v != 0:
            raise ValueError("Battery weight must be 0 when product contains no battery")
        if contains_battery and v <= 0:
            raise ValueError("Battery weight must be greater than 0 when product contains battery")
        return v

    @field_validator('battery_count')
    @classmethod
    def validate_battery_count(cls, v, info):
        contains_battery = info.data.get('contains_battery', False)
        if not contains_battery and v != 0:
            raise ValueError("Battery count must be 0 when product contains no battery")
        if contains_battery and v <= 0:
            raise ValueError("Battery count must be greater than 0 when product contains battery")
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

class BatteryInfoExtractor:
    def __init__(self, search_client=None):
        self.search_client = search_client or GeminiSearch()
    
    def get_battery_info_prompt(self, manufacturer, part_number, description):
        """
        Generate the prompt for battery information extraction
        
        Args:
            manufacturer (str): Product manufacturer
            part_number (str): Product part number
            description (str): Product description
            
        Returns:
            str: The formatted prompt
        """
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
    
    def extract_battery_info(self, manufacturer, part_number, description):
        """
        Extract structured battery information using structured output with validation
        
        Args:
            manufacturer (str): Product manufacturer
            part_number (str): Product part number
            description (str): Product description
            
        Returns:
            BatteryInformation: Validated structured battery information
        """
        # Input validation
        if not all([manufacturer.strip(), part_number.strip(), description.strip()]):
            logging.error(f"Missing required fields - Manufacturer: {manufacturer}, Part Number: {part_number}, Description: {description}")
            raise ValueError("All product identifiers (manufacturer, part_number, description) must be provided")
        
        logging.info(f"Starting battery info extraction for {manufacturer} - {part_number}")
        
        # Generate the prompt
        query = self.get_battery_info_prompt(manufacturer, part_number, description)
        
        try:
            logging.debug(f"Sending query to search client for {manufacturer} - {part_number}")
            response = self.search_client.structured_search(
                query=query,
                schema=BatteryInformation
            )
            
            # Validate the parsed response
            if hasattr(response, 'parsed') and response.parsed:
                # Additional business logic validation
                battery_info = response.parsed
                logging.info(f"Successfully extracted battery info for {manufacturer} - {part_number}: Battery={battery_info.contains_battery}, Count={battery_info.battery_count}")
                return response
            else:
                logging.error(f"No structured data returned from model for {manufacturer} - {part_number}")
                raise ValueError("No structured data returned from model")
                
        except Exception as e:
            logging.error(f"Structured extraction failed for {manufacturer} - {part_number}: {e}")
            print(f"Structured extraction failed: {e}")
            raise

    def process_csv_file(self, input_file, output_file, test=False):
        """
        Process the entire CSV file and extract battery information for all products
        
        Args:
            input_file (str): Path to input CSV file
            output_file (str): Path to output CSV file
            test (bool): If True, only process the first row for testing
        """
        logging.info(f"Starting CSV processing - Input: {input_file}, Output: {output_file}, Test mode: {test}")
        
        # Read the input CSV file
        with open(input_file, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Prepare output data
            output_data = []
            
            for row_index, row in enumerate(reader):
                # If test mode, only process the first row
                if test and row_index > 0:
                    logging.info(f"Test mode enabled - stopping after first row")
                    break
                    
                manufacturer = row['Manufacturer']
                part_number = row['Part Number']
                description = row['Description']
                
                logging.info(f"Processing row {row_index + 1}: {manufacturer} - {part_number}")
                print(f"Processing: {manufacturer} - {part_number}")
                
                try:
                    # Extract battery information
                    response = self.extract_battery_info(manufacturer, part_number, description)
                    battery_info = response.parsed
                    
                    # Prepare sources (up to 3)
                    sources = battery_info.reference_sources[:3] if battery_info.reference_sources else []
                    source1 = sources[0] if len(sources) > 0 else ""
                    source2 = sources[1] if len(sources) > 1 else ""
                    source3 = sources[2] if len(sources) > 2 else ""
                    
                    logging.debug(f"Found {len(sources)} reference sources for {manufacturer} - {part_number}")
                    
                    # Format output row
                    output_row = {
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
                        'Source1': source1,
                        'Source2': source2,
                        'Source3': source3
                    }
                    
                    logging.info(f"Successfully processed {manufacturer} - {part_number}")
                    
                except Exception as e:
                    logging.error(f"Error processing {manufacturer} - {part_number}: {e}")
                    print(f"Error processing {manufacturer} - {part_number}: {e}")
                    # Add row with empty battery information
                    output_row = {
                        'Manufacturer': manufacturer,
                        'Part Number': part_number,
                        'Description': description,
                        'Does the product contain a battery?': "",
                        'Number of Batteries Per Unit': "",
                        'Weight of Single Battery (in KG to 3 decimals)': "",
                        'Battery type or model': "",
                        'Battery Chemistry': "",
                        'Is the battery rechargeable?': "",
                        'BATTERY BRAND IF AVAILABLE': "",
                        'Is the battery Integrated or Stand Alone': "",
                        'Source1': "",
                        'Source2': "",
                        'Source3': ""
                    }
                
                output_data.append(output_row)
        
        logging.info(f"Processed {len(output_data)} rows total")
        
        # Write the output CSV file
        fieldnames = [
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
        
        logging.info(f"Writing output to {output_file}")
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output_data)
        
        logging.info(f"Processing complete. Output saved to {output_file}")
        print(f"Processing complete. Output saved to {output_file}")

if __name__ == "__main__":
    # Initialize the search client and extractor
    logging.info("Initializing GeminiSearch and BatteryInfoExtractor")
    searcher = GeminiSearch()
    extractor = BatteryInfoExtractor(searcher)
    
    # Process the entire CSV file
    input_file = "data/sheet_3.csv"
    output_file = "sheet_3_output.csv"
    
    logging.info("Starting Battery Information processing from CSV")
    print("Processing Battery Information from CSV")
    print("=" * 70)
    
    try:
        # Set test=True to only process the first row for testing
        extractor.process_csv_file(input_file, output_file, test=False)
        logging.info(f"All products processed successfully! Results saved to: {output_file}")
        print(f"\nAll products processed successfully!")
        print(f"Results saved to: {output_file}")
        
    except Exception as e:
        logging.error(f"Error processing CSV file: {e}")
        print(f"Error processing CSV file: {e}")
