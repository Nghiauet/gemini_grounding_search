import os
from typing import Dict, Any, Optional
import json
from pathlib import Path


class Config:
    """Configuration management for the grounding search application"""
    
    DEFAULT_CONFIG = {
        "gemini": {
            "model": "gemini-2.5-pro",
            "temperature": 0.1,
            "top_p": 0.8,
            "top_k": 40,
            "structured_temperature": 0.2,
            "structured_top_p": 0.9
        },
        "processing": {
            "max_sources": 3,
            "test_mode": False,
            "retry_attempts": 3,
            "retry_delay": 1.0
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file_enabled": True,
            "console_enabled": True
        },
        "data": {
            "input_dir": "data",
            "output_dir": ".",
            "encoding": "utf-8"
        }
    }
    
    def __init__(self, config_file: Optional[str] = None):
        self._config = self.DEFAULT_CONFIG.copy()
        
        if config_file and Path(config_file).exists():
            self.load_from_file(config_file)
        
        # Override with environment variables
        self._load_from_env()
    
    def load_from_file(self, config_file: str) -> None:
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                self._merge_config(file_config)
        except Exception as e:
            print(f"Warning: Could not load config from {config_file}: {e}")
    
    def _load_from_env(self) -> None:
        """Load configuration from environment variables"""
        env_mappings = {
            'GEMINI_MODEL': ('gemini', 'model'),
            'GEMINI_TEMPERATURE': ('gemini', 'temperature'),
            'GEMINI_TOP_P': ('gemini', 'top_p'),
            'GEMINI_TOP_K': ('gemini', 'top_k'),
            'LOG_LEVEL': ('logging', 'level'),
            'TEST_MODE': ('processing', 'test_mode'),
            'MAX_SOURCES': ('processing', 'max_sources'),
            'INPUT_DIR': ('data', 'input_dir'),
            'OUTPUT_DIR': ('data', 'output_dir')
        }
        
        for env_var, (section, key) in env_mappings.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                
                # Type conversion
                if key in ['temperature', 'top_p', 'retry_delay']:
                    value = float(value)
                elif key in ['top_k', 'max_sources', 'retry_attempts']:
                    value = int(value)
                elif key == 'test_mode':
                    value = value.lower() in ['true', '1', 'yes']
                
                self._config[section][key] = value
    
    def _merge_config(self, new_config: Dict[str, Any]) -> None:
        """Recursively merge new configuration into existing config"""
        for key, value in new_config.items():
            if key in self._config and isinstance(self._config[key], dict) and isinstance(value, dict):
                self._config[key].update(value)
            else:
                self._config[key] = value
    
    def get(self, section: str, key: str = None, default=None):
        """Get configuration value"""
        if key is None:
            return self._config.get(section, default)
        return self._config.get(section, {}).get(key, default)
    
    def get_gemini_config(self) -> Dict[str, Any]:
        """Get Gemini-specific configuration"""
        return self._config['gemini']
    
    def get_processing_config(self) -> Dict[str, Any]:
        """Get processing-specific configuration"""
        return self._config['processing']
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging-specific configuration"""
        return self._config['logging']
    
    def get_data_config(self) -> Dict[str, Any]:
        """Get data-specific configuration"""
        return self._config['data']
    
    def save_to_file(self, config_file: str) -> None:
        """Save current configuration to file"""
        with open(config_file, 'w') as f:
            json.dump(self._config, f, indent=2)
    
    def __repr__(self) -> str:
        return f"Config({json.dumps(self._config, indent=2)})"


# Global configuration instance
config = Config()