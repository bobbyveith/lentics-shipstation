from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

# Import logger functions without creating circular imports
from app.utils.logger import get_logger

class OutputManager:
    """
    Centralized manager for terminal output and logging.
    Provides consistent formatting and logging capabilities across the application.
    """
    
    def __init__(self, module_name: str, log_level: int = logging.INFO):
        """
        Initialize the output manager.
        
        Args:
            module_name: Name of the module using this manager (for logging context)
            log_level: The logging level to use
        """
        self.module_name = module_name
        # Get logger from the logger.py module
        self.logger = get_logger(module_name)
        self.logger.setLevel(log_level)
    
    # Process start/end methods
    def print_process_start(self, process_name: Optional[str] = None):
        """Print and log the start of a process with a header."""
        message = f"🚀 STARTING {process_name or 'PROCESS'}"
        self.print_section_divider()
        self.logger.info(f"\n{message}")
    
    def print_process_end(self, success: bool = True):
        """Print and log the end of a process with a footer."""
        self.print_section_divider()
        if success:
            message = "✅ PROCESS COMPLETED SUCCESSFULLY"
            self.logger.info(f"\n{message}\n")
        else:
            message = "❌ PROCESS COMPLETED WITH ERRORS"
            self.logger.error(f"\n{message}\n")
    
    # Section formatting methods
    def print_section_header(self, header_text: str):
        """Print and log a section header."""
        self.logger.info(f"\n{header_text}")
    
    def print_section_divider(self):
        """Print a divider line between sections."""
        self.logger.info("\n" + "━" * 80)
    
    def print_section_item(self, item_text: str, log_level: str = "info", color: str = None):
        """
        Print an item within a section with proper indentation and log it.
        
        Args:
            item_text: The text to print and log
            log_level: The logging level to use ("info", "warning", "error", "debug")
            color: Optional color for the text ("red", "green", "yellow", "orange", "purple")
        """
        # ANSI color codes
        color_codes = {
            "red": '\033[91m',
            "green": '\033[92m',
            "yellow": '\033[93m',
            "orange": '\033[38;2;255;165;0m',
            "purple": '\033[95m',
            "reset": '\033[0m'
        }
        
        # Create clean message for logging (without color codes)
        log_message = f"  {item_text}"
        
        # Add color with a custom attribute for the StreamHandler
        if color and color.lower() in color_codes:
            # Create a custom attribute that our filter will use
            extras = {'colored_text': f"{color_codes[color.lower()]}{log_message}{color_codes['reset']}"}
        else:
            extras = {'colored_text': log_message}
        
        # Log with appropriate level and extras
        if log_level == "warning":
            self.logger.warning(log_message, extra=extras)
        elif log_level == "error":
            self.logger.error(log_message, extra=extras)
        elif log_level == "debug":
            self.logger.debug(log_message, extra=extras)
        else:
            self.logger.info(log_message, extra=extras)