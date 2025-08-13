import csv
from gemini_grounding_search import GeminiSearch, ProductSpecification, convert_specs_to_imperial

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

    def process_csv_file(self, input_file, output_file, test=False):
        """
        Process the entire CSV file and extract specifications for all products
        
        Args:
            input_file (str): Path to input CSV file
            output_file (str): Path to output CSV file
            test (bool): If True, only process the first row for testing
        """
        # Read the input CSV file
        with open(input_file, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Prepare output data
            output_data = []
            
            for row_index, row in enumerate(reader):
                # If test mode, only process the first row
                if test and row_index > 0:
                    break
                    
                manufacturer = row['Manufacturer']
                part_number = row['Part Number']
                description = row['Description']
                
                print(f"Processing: {manufacturer} - {part_number}")
                
                try:
                    # Extract product specifications
                    response = self.extract_product_specs(manufacturer, part_number, description)
                    specs = response.parsed
                    
                    # Prepare sources (up to 3)
                    sources = specs.reference_sources[:3] if specs.reference_sources else []
                    source1 = sources[0] if len(sources) > 0 else ""
                    source2 = sources[1] if len(sources) > 1 else ""
                    source3 = sources[2] if len(sources) > 2 else ""
                    
                    # Format output row
                    output_row = {
                        'Manufacturer': manufacturer,
                        'Part Number': part_number,
                        'Description': description,
                        'Product Weight in kg (3 decimals)': f"{specs.weight_kg:.3f}" if specs.weight_kg else "",
                        'Dim (L) CM': specs.length_cm if specs.length_cm else "",
                        'Dim (W) CM': specs.width_cm if specs.width_cm else "",
                        'Dim (H) CM': specs.height_cm if specs.height_cm else "",
                        'Source1': source1,
                        'Source2': source2,
                        'Source3': source3
                    }
                    
                except Exception as e:
                    print(f"Error processing {manufacturer} - {part_number}: {e}")
                    # Add row with empty specifications
                    output_row = {
                        'Manufacturer': manufacturer,
                        'Part Number': part_number,
                        'Description': description,
                        'Product Weight in kg (3 decimals)': "",
                        'Dim (L) CM': "",
                        'Dim (W) CM': "",
                        'Dim (H) CM': "",
                        'Source1': "",
                        'Source2': "",
                        'Source3': ""
                    }
                
                output_data.append(output_row)
        
        # Write the output CSV file
        fieldnames = [
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
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output_data)
        
        print(f"Processing complete. Output saved to {output_file}")

if __name__ == "__main__":
    # Initialize the search client and extractor
    searcher = GeminiSearch()
    extractor = ProductSpecsExtractor(searcher)
    
    # Process the entire CSV file
    input_file = "data/sheet_2.csv"
    output_file = "sheet_2_output.csv"
    
    print("Processing Product Specifications from CSV")
    print("=" * 70)
    
    try:
        # Set test=True to only process the first row for testing
        extractor.process_csv_file(input_file, output_file, test=False)
        print(f"\nAll products processed successfully!")
        print(f"Results saved to: {output_file}")
        
    except Exception as e:
        print(f"Error processing CSV file: {e}")
