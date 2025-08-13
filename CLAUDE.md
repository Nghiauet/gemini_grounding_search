# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Environment

This is a Python 3.11+ project using `uv` for dependency management. The project uses Google's Gemini AI API with grounded search capabilities to extract product information from CSV files.

### Setup Commands
```bash
# Install dependencies
uv sync

# Set up environment variables (required)
export GEMINI_API_KEY="your_api_key_here"
```

### Common Commands
```bash
# Run product specifications extraction
python main.py specs -i data/sheet_2.csv

# Run battery information extraction  
python main.py battery -i data/sheet_3.csv

# Test mode (process only first row)
python main.py specs -i data/sheet_2.csv --test

# Both extractions with custom config
python main.py both -i data/products.csv --config config.json

# Debug mode with detailed logging
python main.py specs -i data/sheet_2.csv --log-level DEBUG
```

## Architecture Overview

### Core Components

**GeminiSearch** (`src/gemini_grounding_search.py`)
- Handles all Gemini AI API interactions
- Provides grounded search with Google Search integration
- Supports both structured and unstructured responses
- Includes citation extraction and response optimization

**BaseExtractor** (`src/base_extractor.py`)
- Abstract base class for all extractors
- Handles CSV file processing, error handling, and output formatting
- Provides template methods for extraction logic

**Concrete Extractors**
- `ProductSpecsExtractor` - Extracts dimensions, weight, specifications
- `BatteryInfoExtractor` - Extracts battery presence, type, chemistry, specifications

**Data Models** (`src/models.py`)
- `ProductSpecification` - Validated product dimensions and weight with URL validation
- `BatteryInformation` - Comprehensive battery data with cross-field validation
- Uses Pydantic for strict validation and realistic measurement constraints

### Key Design Patterns

- **Template Method Pattern**: BaseExtractor defines the processing flow, concrete extractors implement specific logic
- **Strategy Pattern**: Different extractors for different types of information extraction
- **Configuration-driven**: All behavior configurable via config.json and environment variables
- **Fail-safe**: Graceful degradation with empty fields for failed extractions

## Configuration

The system uses a hierarchical configuration approach:
1. Environment variables (highest priority)
2. Command-line arguments
3. config.json file
4. Built-in defaults (lowest priority)

Key configuration sections:
- `gemini`: Model settings, temperature, top_p, top_k
- `processing`: Retry logic, max sources, test mode
- `logging`: Level, format, file/console output
- `data`: Input/output directories, encoding

## Important Implementation Notes

- **Part number matching is strict**: Exact matches only, no fuzzy matching
- **URL validation**: All source URLs are validated with regex patterns
- **Retry logic**: Built-in retry with exponential backoff for API failures
- **Test mode**: Always processes only first row when --test flag is used
- **Legacy compatibility**: Old scripts (sheet_2_schema.py, sheet_3_schema.py) still work but show deprecation warnings

## API Requirements

- Requires valid Google/Gemini API credentials via GEMINI_API_KEY environment variable
- Uses Gemini 2.5-pro model by default
- Grounded search requires Google Search API access

## Data Flow

1. CSV input → BaseExtractor.process_csv_file()
2. For each row → concrete extractor.extract_info()
3. Calls GeminiSearch with structured prompts
4. Validates response against Pydantic models
5. Formats output with sources → CSV output
6. Logs all operations with configurable detail level