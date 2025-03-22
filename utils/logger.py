import logging
import os
import datetime
from typing import Optional


def setup_logger(name: str, log_level: int = logging.INFO, log_dir: Optional[str] = None) -> logging.Logger:
    """
    Set up a logger with file and console handlers
    
    Args:
        name: Logger name
        log_level: Logging level
        log_dir: Directory for log files
        
    Returns:
        Configured logger
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Clear existing handlers
    if logger.handlers:
        logger.handlers = []
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Create file handler if log_dir is provided
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d")
        log_file = os.path.join(log_dir, f"{name}_{timestamp}.log")
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# Create default application logger
app_logger = setup_logger(
    "brand_news_analyzer",
    log_dir=os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
)


class LoggerMixin:
    """Mixin to provide logging capabilities to a class"""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for the class"""
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        return self._logger