#!/usr/bin/env python3
"""
Grounding Search - Product Information Extraction Tool

This tool extracts product specifications and battery information from CSV files
using Google's Gemini AI with grounded search capabilities.
"""

import argparse
import sys

from src.product_specs_extractor import ProductSpecsExtractor
from src.battery_info_extractor import BatteryInfoExtractor
from src.gemini_grounding_search import GeminiSearch
from src.config import config
from src.utils import setup_logging, validate_file_paths


def create_parser():
    """Create and configure argument parser"""
    parser = argparse.ArgumentParser(
        description="Extract product information using Gemini grounded search",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'extraction_type',
        choices=['specs', 'battery', 'both'],
        help='Type of extraction to perform'
    )
    
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input CSV file path'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output file path (auto-generated if not provided)'
    )
    
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test mode: process only first row'
    )
    
    parser.add_argument(
        '--config',
        help='Configuration file path'
    )
    
    parser.add_argument(
        '--log-file',
        help='Log file path'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )
    
    return parser


def extract_product_specs(input_file: str, output_file: str, test_mode: bool = False):
    """Extract product specifications"""
    print("=" * 70)
    print("PRODUCT SPECIFICATIONS EXTRACTION")
    print("=" * 70)
    
    search_client = GeminiSearch(config=config.get_gemini_config())
    extractor = ProductSpecsExtractor(search_client)
    
    extractor.process_csv_file(input_file, output_file, test=test_mode)
    print(f"\nProduct specifications saved to: {output_file}")


def extract_battery_info(input_file: str, output_file: str, test_mode: bool = False):
    """Extract battery information"""
    print("=" * 70)
    print("BATTERY INFORMATION EXTRACTION")
    print("=" * 70)
    
    search_client = GeminiSearch(config=config.get_gemini_config())
    extractor = BatteryInfoExtractor(search_client)
    
    extractor.process_csv_file(input_file, output_file, test=test_mode)
    print(f"\nBattery information saved to: {output_file}")


def main():
    """Main application entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging
    log_file = args.log_file
    if not log_file and args.extraction_type in ['battery', 'both']:
        log_file = 'processing.log'
    
    logger = setup_logging(
        logger_name='grounding_search',
        log_file=log_file,
        level=args.log_level
    )
    
    try:
        # Validate file paths
        input_path, _ = validate_file_paths(args.input, args.output or "dummy.csv")
        
        logger.info(f"Starting {args.extraction_type} extraction")
        logger.info(f"Input file: {input_path}")
        logger.info(f"Test mode: {args.test}")
        
        # Generate output file names if not provided
        input_stem = input_path.stem
        
        if args.extraction_type == 'specs':
            output_file = args.output or f"{input_stem}_specs_output.csv"
            extract_product_specs(str(input_path), output_file, args.test)
            
        elif args.extraction_type == 'battery':
            output_file = args.output or f"{input_stem}_battery_output.csv"
            extract_battery_info(str(input_path), output_file, args.test)
            
        elif args.extraction_type == 'both':
            specs_output = f"{input_stem}_specs_output.csv"
            battery_output = f"{input_stem}_battery_output.csv"
            
            extract_product_specs(str(input_path), specs_output, args.test)
            print()  # Add spacing between extractions
            extract_battery_info(str(input_path), battery_output, args.test)
        
        logger.info("Extraction completed successfully!")
        print("\n✅ All extractions completed successfully!")
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
