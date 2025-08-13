# Grounding Search
## Project Overview

This is a Python-based product specification and battery information extraction system that uses Google's Gemini AI with grounded search capabilities. The system processes CSV files containing product information (manufacturer, part number, description) and extracts detailed specifications using structured AI-powered web searches.

## Environment & Dependencies
  Usage Examples:

  # Extract product specifications
  python main.py specs -i data/sheet_2.csv

  # Extract battery information with test mode
  python main.py battery -i data/sheet_3.csv --test

  # Extract both types of information
  python main.py both -i data/products.csv

  # Use custom config and logging
  python main.py specs -i data/sheet_2.csv --config config.json --log-level DEBUG
- **Python Version**: >=3.11 (specified in pyproject.toml)
- **Package Manager**: Uses `uv` (uv.lock present)
- **Key Dependencies**: 
  - `google-genai>=1.29.0` for Gemini AI API
  - `google>=3.0.0` for Google services
  - `pydantic` for data validation (imported in code)

## Running the Application

### Main Entry Points

1. **Product Specifications Extraction** (Sheet 2 processing):
   ```bash
   python src/sheet_2_schema.py
   ```

2. **Battery Information Extraction** (Sheet 3 processing):
   ```bash
   python src/sheet_3_schema.py
   ```

3. **Basic Hello World** (for testing):
   ```bash
   python main.py
   ```

### Development Commands

```bash
# Install dependencies using uv
uv sync

# Run specific processors
python src/sheet_2_schema.py  # Process product specifications
python src/sheet_3_schema.py  # Process battery information
```

## Code Architecture

### Core Components

1. **GeminiSearch** (`src/gemini_grounding_search.py`):
   - Primary AI search client using Gemini 2.5-pro model
   - Handles grounded search with Google Search integration
   - Supports both regular and structured output generation
   - Includes citation extraction and response optimization

2. **ProductSpecsExtractor** (`src/sheet_2_schema.py`):
   - Extracts product dimensions and weight specifications
   - Uses `ProductSpecification` Pydantic model for validation
   - Processes sheet_2.csv → sheet_2_output.csv
   - Searches manufacturer websites and distributor catalogs

3. **BatteryInfoExtractor** (`src/sheet_3_schema.py`):
   - Extracts battery-related information (presence, type, chemistry, etc.)
   - Uses `BatteryInformation` Pydantic model with complex validation
   - Processes sheet_3.csv → sheet_3_output.csv
   - Includes comprehensive logging to sheet_3_processing.log

### Data Models

- **ProductSpecification**: weight_kg, dimensions (L/W/H in cm), reference_sources
- **BatteryInformation**: contains_battery, battery_count, weight, type, chemistry, rechargeability, integration status

### Data Flow

1. CSV input files in `data/` directory
2. Row-by-row processing with manufacturer/part number/description
3. AI-powered web search for exact product specifications  
4. Structured data extraction with Pydantic validation
5. CSV output with original data + extracted specifications + source URLs

## Configuration

- **AI Model**: Uses Gemini 2.5-pro with optimized temperature settings
- **Search Strategy**: Prioritizes manufacturer websites, datasheets, authorized distributors
- **Validation**: Strict part number matching, realistic measurement ranges, URL validation
- **Error Handling**: Graceful failure with empty fields for failed extractions

## Important Notes

- The system requires valid Google/Gemini API credentials (not stored in repo)
- Part number matching is strict - rejects similar but different products
- Both processors support test mode (first row only) by setting `test=True`
- Battery extraction includes detailed logging for debugging complex cases
- Empty README.md and runner.py files suggest this is a work-in-progress project