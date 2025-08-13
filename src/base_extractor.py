from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import csv
import logging
from .gemini_grounding_search import GeminiSearch


class BaseExtractor(ABC):
    """Base class for all product information extractors"""
    
    def __init__(self, search_client: Optional[GeminiSearch] = None):
        self.search_client = search_client or GeminiSearch()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def get_extraction_prompt(self, manufacturer: str, part_number: str, description: str) -> str:
        """Generate the prompt for information extraction"""
        pass
    
    @abstractmethod
    def extract_info(self, manufacturer: str, part_number: str, description: str):
        """Extract structured information using the search client"""
        pass
    
    @abstractmethod
    def format_output_row(self, manufacturer: str, part_number: str, description: str, extracted_data) -> Dict[str, Any]:
        """Format the extracted data into CSV output format"""
        pass
    
    @abstractmethod
    def get_output_fieldnames(self) -> List[str]:
        """Get the fieldnames for CSV output"""
        pass
    
    def validate_inputs(self, manufacturer: str, part_number: str, description: str) -> None:
        """Validate input parameters"""
        if not all([manufacturer.strip(), part_number.strip(), description.strip()]):
            raise ValueError("All product identifiers (manufacturer, part_number, description) must be provided")
    
    def format_sources(self, sources: List[str], max_sources: int = 3) -> Dict[str, str]:
        """Format reference sources for output"""
        limited_sources = sources[:max_sources] if sources else []
        source_dict = {}
        
        for i in range(max_sources):
            source_key = f'Source{i + 1}'
            source_dict[source_key] = limited_sources[i] if i < len(limited_sources) else ""
        
        return source_dict
    
    def create_empty_row(self, manufacturer: str, part_number: str, description: str) -> Dict[str, Any]:
        """Create an empty output row for failed extractions"""
        empty_row = {
            'Manufacturer': manufacturer,
            'Part Number': part_number,
            'Description': description
        }
        
        # Add empty values for all other fields
        for field in self.get_output_fieldnames():
            if field not in empty_row:
                empty_row[field] = ""
        
        return empty_row
    
    def process_csv_file(self, input_file: str, output_file: str, test: bool = False) -> None:
        """Process CSV file and extract information for all products"""
        self.logger.info(f"Starting CSV processing - Input: {input_file}, Output: {output_file}, Test mode: {test}")
        
        with open(input_file, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            output_data = []
            
            for row_index, row in enumerate(reader):
                if test and row_index > 0:
                    self.logger.info("Test mode enabled - stopping after first row")
                    break
                    
                manufacturer = row['Manufacturer']
                part_number = row['Part Number']
                description = row['Description']
                
                self.logger.info(f"Processing row {row_index + 1}: {manufacturer} - {part_number}")
                print(f"Processing: {manufacturer} - {part_number}")
                
                try:
                    extracted_data = self.extract_info(manufacturer, part_number, description)
                    output_row = self.format_output_row(manufacturer, part_number, description, extracted_data)
                    self.logger.info(f"Successfully processed {manufacturer} - {part_number}")
                    
                except Exception as e:
                    self.logger.error(f"Error processing {manufacturer} - {part_number}: {e}")
                    print(f"Error processing {manufacturer} - {part_number}: {e}")
                    output_row = self.create_empty_row(manufacturer, part_number, description)
                
                output_data.append(output_row)
        
        self.logger.info(f"Processed {len(output_data)} rows total")
        
        # Write output CSV
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.get_output_fieldnames())
            writer.writeheader()
            writer.writerows(output_data)
        
        self.logger.info(f"Processing complete. Output saved to {output_file}")
        print(f"Processing complete. Output saved to {output_file}")