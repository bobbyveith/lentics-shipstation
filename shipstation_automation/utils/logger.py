import os
import logging
import logging.config

class ConsoleLogger(logging.Logger):
    def console_info(self, msg, *args, **kwargs):
        """Log to both file and console"""
        kwargs['extra'] = kwargs.get('extra', {})
        kwargs['extra']['print_to_console'] = True
        self.info(msg, *args, **kwargs)

class ConsoleFilter(logging.Filter):
    def filter(self, record):
        return getattr(record, 'print_to_console', False)
    
class ColorAwareFormatter(logging.Formatter):
    """Formatter that uses colored text for console but not for files"""
    
    def format(self, record):
        # Check if this record has our special colored_text attribute
        if hasattr(record, 'colored_text'):
            # Determine if this is the console formatter (simpler format string)
            # Console formatters typically use a simpler format without timestamps
            is_console = '%(' not in self._style._fmt or len(self._style._fmt) < 30
            
            if is_console:
                # For console output, use the colored version
                original_msg = record.msg
                record.msg = record.colored_text
                result = super().format(record)
                record.msg = original_msg  # Restore for possible reuse
                return result
                
        # Use normal formatting (for file logs or non-colored messages)
        return super().format(record)

def upload_logs_to_s3(bucket_name: str, env: str, log_content: str) -> bool:
    """Upload logs to S3"""
    s3 = S3BucketIntegration(bucket_name)
    return s3.upload_log_file(env, log_content)

def setup_logging(env: str = 'development'):
    """Initialize logging configuration"""
    if env == 'default':
        env = 'development'
    
    print(f"Setting up logging for environment: {env}")
    config_path = os.path.join('app', 'config', 'logging', f'{env}.yaml')
    
    if os.path.exists(config_path):
        with open(config_path, 'rt') as f:
            config = yaml.safe_load(f)
            
            # Update log file paths to use app/logs directory
            if 'handlers' in config and 'file' in config['handlers']:
                config['handlers']['file']['filename'] = os.path.join('app', 'logs', f'{env}.log')
        
        logging.config.dictConfig(config)
    else:
        raise Exception(f"Logging configuration file not found at: {config_path}")

def get_logger(module_name: str) -> logging.Logger:
    """Get a logger with standardized naming"""
    if module_name.startswith('app.'):
        return logging.getLogger(module_name)
    return logging.getLogger(f'app.{module_name}')


    
def test_logger():
    """Test various logging configurations"""
    # Import here to avoid circular imports
    from utils.output_manager import get_output_manager
    
    # Get different output managers
    scheduler_output = get_output_manager('scheduler')
    debug_output = get_output_manager('debug')
    app_output = get_output_manager('core')

    # Test process start/end
    app_output.print_process_start("OUTPUT MANAGER TEST")
    
    # Test section headers and items
    app_output.print_section_header("📊 Testing Different Output Types")
    
    # Test regular logging
    scheduler_output.log_info("Testing scheduler logger - INFO message (file only)")
    scheduler_output.log_error("Testing scheduler logger - ERROR message (file only)")
    scheduler_output.log_debug("Testing scheduler logger - DEBUG message (file only)")

    # Test console output
    debug_output.print_section_item("Testing debug output - INFO level", "info")
    debug_output.print_section_item("Testing debug output - WARNING level", "warning")
    debug_output.print_section_item("Testing debug output - ERROR level", "error")

    # Test specialized formatters
    app_output.print_section_header("📈 Testing Specialized Formatters")
    app_output.print_report_item("TestGroup", 10, 5)
    app_output.print_drive_upload_item(1, 3, "test_file.pdf")
    
    app_output.print_process_end()
    
    print("\nCheck app/logs/development.log for file output")
