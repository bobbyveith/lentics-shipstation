import os
import logging
import logging.config
import yaml
from datetime import datetime
import io
from shipstation_automation.config.config import ENV, S3_LOG_BUCKET_NAME
from shipstation_automation.integrations.aws_s3 import S3BucketIntegration

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

class LambdaMemoryHandler(logging.Handler):
    """Handler that keeps logs in memory for lambda functions and uploads to S3 on shutdown"""
    
    def __init__(self, bucket_name, env):
        super().__init__()
        self.bucket_name = bucket_name
        self.env = env
        self.log_stream = io.StringIO()
        self.formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    def emit(self, record):
        msg = self.formatter.format(record) + '\n'
        self.log_stream.write(msg)
    
    def flush(self):
        """Upload logs to S3 and clear memory buffer"""
        log_content = self.log_stream.getvalue()
        if log_content:
            success = upload_logs_to_s3(self.bucket_name, self.env, log_content)
            if success:
                # Clear the buffer after successful upload
                self.log_stream = io.StringIO()
                
    def close(self):
        """Upload any remaining logs before closing"""
        self.flush()
        super().close()

def upload_logs_to_s3(bucket_name: str, env: str, log_content: str) -> bool:
    """Upload logs to S3"""
    if not log_content.strip():
        return False
        
    s3 = S3BucketIntegration(bucket_name)
    return s3.upload_log_file(env, log_content)

def setup_logging():
    """Initialize logging configuration for the appropriate environment"""
    env = ENV
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, 'config', 'logging', f'{env}.yaml')
    
    if os.path.exists(config_path):
        with open(config_path, 'rt') as f:
            config = yaml.safe_load(f)
            
            # For Lambda, ensure we have the right handlers
            if env == 'production':
                # Create a Lambda memory handler for production
                lambda_handler = {
                    'class': 'shipstation_automation.utils.logger.LambdaMemoryHandler',
                    'level': 'INFO',
                    'bucket_name': S3_LOG_BUCKET_NAME,
                    'env': env,
                    'formatter': 'detailed'
                }
                config['handlers']['lambda_memory'] = lambda_handler
                
                # Add the handler to all loggers
                for logger_name in config.get('loggers', {}):
                    config['loggers'][logger_name]['handlers'].append('lambda_memory')
            else:
                # For development ensure we have a local log file
                logs_dir = os.path.join(base_dir, 'logs')
                if not os.path.exists(logs_dir):
                    os.makedirs(logs_dir)
                    
                if 'handlers' in config and 'file' in config['handlers']:
                    config['handlers']['file']['filename'] = os.path.join(logs_dir, f'{env}.log')
        
        # Configure logging using our modified config
        logging.config.dictConfig(config)
        
        # Register a hook to flush logs on Lambda shutdown
        if env == 'production':
            import atexit
            atexit.register(lambda: logging.getLogger().handlers[0].flush())
    else:
        raise Exception(f"Logging configuration file not found at: {config_path}")

def get_logger(module_name: str) -> logging.Logger:
    """Get a logger with standardized naming"""
    if module_name.startswith('shipstation_automation.'):
        return logging.getLogger(module_name)
    return logging.getLogger(f'shipstation_automation.{module_name}')
    
def test_logger():
    """Test various logging configurations"""
    # Import here to avoid circular imports
    from shipstation_automation.utils.output_manager import get_output_manager
    
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
    
    # Flush logs to S3 if in production mode
    if ENV == 'production':
        for handler in logging.getLogger().handlers:
            if hasattr(handler, 'flush'):
                handler.flush()
    
    print(f"\nCheck logs for output ({ENV} environment)")
