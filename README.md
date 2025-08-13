# Grounding Search

A professional Python tool for extracting product information using Google's Gemini AI with grounded search capabilities. This system processes CSV files containing product data and extracts detailed specifications using structured AI-powered web searches.

## 🚀 Quick Start

```bash
# Install dependencies
uv sync

# Extract product specifications
python main.py specs -i data/sheet_2.csv

# Extract battery information with test mode
python main.py battery -i data/sheet_3.csv --test

# Extract both types of information
python main.py both -i data/products.csv

# Use custom config and detailed logging
python main.py specs -i data/sheet_2.csv --config config.json --log-level DEBUG
```

## 📋 Requirements

- **Python**: >=3.11
- **Package Manager**: `uv` (recommended) or `pip`
- **Key Dependencies**: 
  - `google-genai>=1.29.0` - Gemini AI API
  - `pydantic>=2.0.0` - Data validation
  - `google>=3.0.0` - Google services

## 🏗️ Architecture

### Clean, Modular Design

```
src/
├── __init__.py                    # Package initialization
├── models.py                     # Pydantic data models
├── gemini_grounding_search.py    # Core AI search client
├── base_extractor.py             # Abstract base for extractors
├── product_specs_extractor.py    # Product specifications
├── battery_info_extractor.py     # Battery information
├── config.py                     # Configuration management
└── utils.py                      # Logging and utilities
```

### Core Components

**🔍 GeminiSearch**
- Configurable Gemini 2.5-pro integration
- Grounded search with Google Search
- Structured and unstructured output modes
- Citation extraction and response optimization

**📦 Product Extractors**
- `ProductSpecsExtractor` - Dimensions, weight, specifications
- `BatteryInfoExtractor` - Battery presence, type, chemistry, specs
- Extensible base class for new extraction types

**📊 Data Models**
- `ProductSpecification` - Validated product dimensions and weight
- `BatteryInformation` - Comprehensive battery data with validation
- URL validation and realistic measurement constraints

## 🎯 Usage

### Command Line Interface

```bash
# Basic usage
python main.py <extraction_type> -i <input_file> [options]

# Extraction types
python main.py specs -i data/sheet_2.csv           # Product specifications
python main.py battery -i data/sheet_3.csv         # Battery information  
python main.py both -i data/products.csv           # Both types

# Options
--test                    # Process only first row (testing)
--output OUTPUT_FILE      # Custom output file path
--config CONFIG_FILE      # Custom configuration file
--log-file LOG_FILE       # Custom log file path
--log-level LEVEL         # Logging level (DEBUG, INFO, WARNING, ERROR)
```

### Configuration

**Environment Variables:**
```bash
export GEMINI_MODEL="gemini-2.5-pro"
export GEMINI_TEMPERATURE="0.1"
export LOG_LEVEL="INFO"
export TEST_MODE="false"
```

**Configuration File (`config.json`):**
```json
{
  "gemini": {
    "model": "gemini-2.5-pro",
    "temperature": 0.1,
    "structured_temperature": 0.2
  },
  "processing": {
    "max_sources": 3,
    "retry_attempts": 3
  },
  "logging": {
    "level": "INFO",
    "file_enabled": true
  }
}
```

## 📤 Output Format

**Product Specifications CSV:**
- Original fields (Manufacturer, Part Number, Description)
- Product Weight in kg (3 decimals)
- Dimensions: Length, Width, Height (CM)
- Up to 3 reference source URLs

**Battery Information CSV:**
- Original fields + battery presence (Yes/No)
- Battery count, weight, type/model
- Chemistry, rechargeability, integration status
- Up to 3 reference source URLs

## 🔧 Extension Points

### Adding New Extractors

```python
from src.base_extractor import BaseExtractor
from src.models import YourModel

class YourExtractor(BaseExtractor):
    def get_extraction_prompt(self, manufacturer, part_number, description):
        # Your extraction prompt logic
        
    def extract_info(self, manufacturer, part_number, description):
        # Your extraction logic using self.search_client
        
    def format_output_row(self, manufacturer, part_number, description, extracted_data):
        # Format for CSV output
        
    def get_output_fieldnames(self):
        # Return list of CSV column names
```

### Custom Configuration

Extend `src/config.py` to add new configuration sections and environment variable mappings.

## 🛡️ Features

- **Reliable**: Retry logic, comprehensive error handling
- **Validated**: Strict part number matching, realistic constraints
- **Extensible**: Clean abstractions, configuration-driven
- **Observable**: Structured logging, progress tracking
- **Professional**: CLI interface, proper packaging

## 📝 Migration from Legacy Scripts

The legacy scripts `src/sheet_2_schema.py` and `src/sheet_3_schema.py` still work but are deprecated:

```bash
# Old way (still works, shows deprecation warning)
python src/sheet_2_schema.py
python src/sheet_3_schema.py

# New way (recommended)
python main.py specs -i data/sheet_2.csv
python main.py battery -i data/sheet_3.csv
```

## ⚠️ Important Notes

- Requires valid Google/Gemini API credentials
- Part number matching is strict (exact matches only)
- Test mode processes only the first row for development
- All extractions include source URL validation
- Failed extractions result in empty fields (graceful degradation)