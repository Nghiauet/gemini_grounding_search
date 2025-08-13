"""
Grounding Search Package

A Python package for extracting product information using Google's Gemini AI
with grounded search capabilities.
"""

from .gemini_grounding_search import GeminiSearch
from .models import ProductSpecification, BatteryInformation, convert_specs_to_imperial
from .product_specs_extractor import ProductSpecsExtractor
from .battery_info_extractor import BatteryInfoExtractor
from .config import config
from .utils import setup_logging

__version__ = "0.1.0"
__author__ = "Grounding Search Team"

__all__ = [
    'GeminiSearch',
    'ProductSpecification',
    'BatteryInformation',
    'convert_specs_to_imperial',
    'ProductSpecsExtractor',
    'BatteryInfoExtractor',
    'config',
    'setup_logging'
]