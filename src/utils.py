import logging
import sys
from pathlib import Path
from typing import Optional
from .config import config


def setup_logging(
    logger_name: Optional[str] = None,
    log_file: Optional[str] = None,
    level: Optional[str] = None
) -> logging.Logger:
    """Set up logging configuration"""
    
    log_config = config.get_logging_config()
    log_level = level or log_config['level']
    log_format = log_config['format']
    
    # Create logger
    logger = logging.getLogger(logger_name or 'grounding_search')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    formatter = logging.Formatter(log_format)
    
    # Console handler
    if log_config['console_enabled']:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_config['file_enabled'] and log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def validate_file_paths(input_file: str, output_file: str) -> tuple[Path, Path]:
    """Validate and return Path objects for input and output files"""
    input_path = Path(input_file)
    output_path = Path(output_file)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    if not input_path.suffix.lower() == '.csv':
        raise ValueError(f"Input file must be a CSV file: {input_file}")
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    return input_path, output_path


def get_data_file_path(filename: str, data_dir: Optional[str] = None) -> str:
    """Get full path for data file"""
    data_config = config.get_data_config()
    data_directory = data_dir or data_config['input_dir']
    return str(Path(data_directory) / filename)


def get_output_file_path(filename: str, output_dir: Optional[str] = None) -> str:
    """Get full path for output file"""
    data_config = config.get_data_config()
    output_directory = output_dir or data_config['output_dir']
    return str(Path(output_directory) / filename)


class RetryHandler:
    """Handle retry logic for operations"""
    
    def __init__(self, max_attempts: int = None, delay: float = None):
        processing_config = config.get_processing_config()
        self.max_attempts = max_attempts or processing_config['retry_attempts']
        self.delay = delay or processing_config['retry_delay']
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def execute_with_retry(self, func, *args, **kwargs):
        """Execute function with retry logic"""
        import time
        
        last_exception = None
        
        for attempt in range(1, self.max_attempts + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                self.logger.warning(f"Attempt {attempt} failed: {e}")
                
                if attempt < self.max_attempts:
                    self.logger.info(f"Retrying in {self.delay} seconds...")
                    time.sleep(self.delay)
                else:
                    self.logger.error(f"All {self.max_attempts} attempts failed")
        
        raise last_exception