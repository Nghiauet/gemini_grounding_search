from pydantic import BaseModel, Field, field_validator
from typing import List
import re


class ProductSpecification(BaseModel):
    weight_kg: float = Field(..., description="Product weight in kilograms")
    length_cm: float = Field(..., description="Product length in centimeters")
    width_cm: float = Field(..., description="Product width in centimeters")
    height_cm: float = Field(..., description="Product height in centimeters")
    reference_sources: List[str] = Field(..., min_length=1, max_length=5, description="Reference source URLs")
    
    @field_validator('weight_kg', 'length_cm', 'width_cm', 'height_cm')
    @classmethod
    def validate_positive(cls, v):
        if v <= 0:
            raise ValueError(f"Value must be greater than 0, got {v}")
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


def convert_specs_to_imperial(specs: ProductSpecification) -> dict:
    """Convert metric specifications to imperial units"""
    return {
        'weight_lbs': specs.weight_kg * 2.20462,
        'length_in': specs.length_cm * 0.393701,
        'width_in': specs.width_cm * 0.393701,
        'height_in': specs.height_cm * 0.393701
    }