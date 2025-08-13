#!/usr/bin/env python3
"""
URL and Product Information Evaluation Tool

Validates URLs in CSV output files and checks if they contain correct product information
using LLM-based content analysis.
"""

import csv
import requests
import argparse
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import time

from src.gemini_grounding_search import GeminiSearch
from src.utils import setup_logging


@dataclass
class ValidationResult:
    """Result of URL and content validation"""
    url: str
    is_accessible: bool
    status_code: Optional[int]
    has_correct_info: Optional[bool]
    confidence_score: Optional[float]
    validation_notes: str


class URLEvaluator:
    """Evaluates URLs for accessibility and product information accuracy"""
    
    def __init__(self, gemini_client: Optional[GeminiSearch] = None):
        self.gemini_client = gemini_client or GeminiSearch()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def check_url_accessibility(self, url: str) -> Tuple[bool, Optional[int]]:
        """Check if URL is accessible"""
        if not url or not url.strip():
            return False, None
            
        try:
            response = self.session.head(url, timeout=10, allow_redirects=True)
            return response.status_code < 400, response.status_code
        except requests.exceptions.RequestException as e:
            self.logger.debug(f"URL check failed for {url}: {e}")
            return False, None
    
    def fetch_page_content(self, url: str) -> Optional[str]:
        """Fetch page content for analysis"""
        try:
            response = self.session.get(url, timeout=15, allow_redirects=True)
            if response.status_code < 400:
                return response.text[:50000]  # Limit content size
        except requests.exceptions.RequestException as e:
            self.logger.debug(f"Content fetch failed for {url}: {e}")
        return None
    
    def validate_product_info_with_llm(
        self, 
        content: str, 
        manufacturer: str, 
        part_number: str, 
        description: str,
        expected_specs: Dict[str, str]
    ) -> Tuple[bool, float, str]:
        """Use LLM to validate if content contains correct product information"""
        
        validation_prompt = f"""
        Analyze the following webpage content to determine if it contains accurate information about this product:
        
        Expected Product:
        - Manufacturer: {manufacturer}
        - Part Number: {part_number}
        - Description: {description}
        - Expected Weight: {expected_specs.get('weight', 'N/A')} kg
        - Expected Dimensions: {expected_specs.get('length', 'N/A')} x {expected_specs.get('width', 'N/A')} x {expected_specs.get('height', 'N/A')} cm
        
        Webpage Content (first 2000 chars):
        {content[:2000]}
        
        Please evaluate:
        1. Does this page contain information about the correct product (matching manufacturer and part number)?
        2. Are the product specifications (dimensions, weight) consistent with expected values?
        3. Is this a reliable source (manufacturer site, official retailer, technical documentation)?
        
        Respond with:
        - CORRECT: if product matches and specs are consistent
        - INCORRECT: if wrong product or significantly different specs
        - PARTIAL: if correct product but missing/unclear specs
        
        Also provide a confidence score (0.0-1.0) and brief explanation.
        
        Format: STATUS|CONFIDENCE|EXPLANATION
        """
        
        try:
            response = self.gemini_client.search(validation_prompt)
            result_text = response.text.strip()
            
            # Parse response
            parts = result_text.split('|')
            if len(parts) >= 3:
                status = parts[0].strip()
                confidence = float(parts[1].strip())
                explanation = parts[2].strip()
                
                is_correct = status == "CORRECT"
                return is_correct, confidence, explanation
            else:
                return False, 0.0, "Unable to parse LLM response"
                
        except Exception as e:
            self.logger.error(f"LLM validation failed: {e}")
            return False, 0.0, f"Validation error: {str(e)}"
    
    def evaluate_url(
        self, 
        url: str, 
        manufacturer: str, 
        part_number: str, 
        description: str,
        expected_specs: Dict[str, str]
    ) -> ValidationResult:
        """Evaluate a single URL comprehensively"""
        
        # Check accessibility
        is_accessible, status_code = self.check_url_accessibility(url)
        
        if not is_accessible:
            return ValidationResult(
                url=url,
                is_accessible=False,
                status_code=status_code,
                has_correct_info=None,
                confidence_score=None,
                validation_notes="URL not accessible"
            )
        
        # Fetch content
        content = self.fetch_page_content(url)
        if not content:
            return ValidationResult(
                url=url,
                is_accessible=True,
                status_code=status_code,
                has_correct_info=None,
                confidence_score=None,
                validation_notes="Could not fetch page content"
            )
        
        # Validate with LLM
        has_correct_info, confidence, notes = self.validate_product_info_with_llm(
            content, manufacturer, part_number, description, expected_specs
        )
        
        return ValidationResult(
            url=url,
            is_accessible=True,
            status_code=status_code,
            has_correct_info=has_correct_info,
            confidence_score=confidence,
            validation_notes=notes
        )


def evaluate_csv_file(input_file: str, output_file: str = None) -> None:
    """Evaluate all URLs in a CSV file"""
    logger = logging.getLogger('evaluation')
    evaluator = URLEvaluator()
    
    results = []
    
    with open(input_file, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row_idx, row in enumerate(reader, 1):
            manufacturer = row['Manufacturer']
            part_number = row['Part Number']
            description = row['Description']
            
            if not all([manufacturer, part_number, description]):
                logger.info(f"Skipping row {row_idx}: missing product information")
                continue
            
            expected_specs = {
                'weight': row.get('Product Weight in kg (3 decimals)', ''),
                'length': row.get('Dim (L) CM', ''),
                'width': row.get('Dim (W) CM', ''),
                'height': row.get('Dim (H) CM', '')
            }
            
            logger.info(f"Evaluating row {row_idx}: {manufacturer} - {part_number}")
            print(f"Processing: {manufacturer} - {part_number}")
            
            # Check each source URL
            for source_num in [1, 2, 3]:
                source_key = f'Source{source_num}'
                url = row.get(source_key, '').strip()
                
                if not url:
                    continue
                
                print(f"  Checking Source{source_num}: {url}")
                result = evaluator.evaluate_url(url, manufacturer, part_number, description, expected_specs)
                
                results.append({
                    'Row': row_idx,
                    'Manufacturer': manufacturer,
                    'Part Number': part_number,
                    'Source Number': source_num,
                    'URL': url,
                    'Accessible': result.is_accessible,
                    'Status Code': result.status_code,
                    'Has Correct Info': result.has_correct_info,
                    'Confidence Score': result.confidence_score,
                    'Validation Notes': result.validation_notes
                })
                
                # Small delay to be respectful to servers
                time.sleep(1)
    
    # Write results
    if not output_file:
        output_file = input_file.replace('.csv', '_evaluation.csv')
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'Row', 'Manufacturer', 'Part Number', 'Source Number', 'URL',
            'Accessible', 'Status Code', 'Has Correct Info', 'Confidence Score', 'Validation Notes'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    # Summary
    total_urls = len(results)
    accessible_urls = sum(1 for r in results if r['Accessible'])
    correct_info_urls = sum(1 for r in results if r['Has Correct Info'])
    
    print(f"\n=== EVALUATION SUMMARY ===")
    print(f"Total URLs evaluated: {total_urls}")
    print(f"Accessible URLs: {accessible_urls} ({accessible_urls/total_urls*100:.1f}%)")
    print(f"URLs with correct info: {correct_info_urls} ({correct_info_urls/total_urls*100:.1f}%)")
    print(f"Results saved to: {output_file}")


def evaluate_csv_file_test_mode(input_file: str, output_file: str = None) -> None:
    """Evaluate URLs for first row only (test mode)"""
    logger = logging.getLogger('evaluation')
    evaluator = URLEvaluator()
    
    results = []
    
    with open(input_file, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        # Process only first row
        row = next(reader)
        manufacturer = row['Manufacturer']
        part_number = row['Part Number']
        description = row['Description']
        
        if not all([manufacturer, part_number, description]):
            print("First row missing product information")
            return
        
        expected_specs = {
            'weight': row.get('Product Weight in kg (3 decimals)', ''),
            'length': row.get('Dim (L) CM', ''),
            'width': row.get('Dim (W) CM', ''),
            'height': row.get('Dim (H) CM', '')
        }
        
        logger.info(f"Testing first row: {manufacturer} - {part_number}")
        print(f"Processing: {manufacturer} - {part_number}")
        
        # Check each source URL
        for source_num in [1, 2, 3]:
            source_key = f'Source{source_num}'
            url = row.get(source_key, '').strip()
            
            if not url:
                continue
            
            print(f"  Checking Source{source_num}: {url}")
            result = evaluator.evaluate_url(url, manufacturer, part_number, description, expected_specs)
            
            results.append({
                'Row': 1,
                'Manufacturer': manufacturer,
                'Part Number': part_number,
                'Source Number': source_num,
                'URL': url,
                'Accessible': result.is_accessible,
                'Status Code': result.status_code,
                'Has Correct Info': result.has_correct_info,
                'Confidence Score': result.confidence_score,
                'Validation Notes': result.validation_notes
            })
            
            # Small delay to be respectful to servers
            time.sleep(1)
    
    # Write results
    if not output_file:
        output_file = input_file.replace('.csv', '_evaluation_test.csv')
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'Row', 'Manufacturer', 'Part Number', 'Source Number', 'URL',
            'Accessible', 'Status Code', 'Has Correct Info', 'Confidence Score', 'Validation Notes'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    # Summary
    total_urls = len(results)
    accessible_urls = sum(1 for r in results if r['Accessible'])
    correct_info_urls = sum(1 for r in results if r['Has Correct Info'])
    
    print(f"\n=== TEST MODE EVALUATION SUMMARY ===")
    print(f"Total URLs evaluated: {total_urls}")
    print(f"Accessible URLs: {accessible_urls} ({accessible_urls/total_urls*100:.1f}%)")
    print(f"URLs with correct info: {correct_info_urls} ({correct_info_urls/total_urls*100:.1f}%)")
    print(f"Results saved to: {output_file}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Evaluate URLs in CSV output files")
    parser.add_argument('input_file', help='Input CSV file to evaluate')
    parser.add_argument('-o', '--output', help='Output file for evaluation results')
    parser.add_argument('--test', action='store_true', help='Test mode: evaluate only first row')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging('url_evaluation', level=args.log_level)
    
    try:
        if args.test:
            evaluate_csv_file_test_mode(args.input_file, args.output)
        else:
            evaluate_csv_file(args.input_file, args.output)
    except Exception as e:
        logging.error(f"Evaluation failed: {e}")
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()