import os
import logging
import logging.config
import yaml
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

def _configure_log_directory():
    """Create and return the logs directory path"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Always use /tmp for logs when running in containers or Lambda
    logs_dir = '/tmp/logs'
    
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        
    return base_dir, logs_dir

def _load_logging_config(config_path):
    """Load the logging configuration from YAML file"""
    if not os.path.exists(config_path):
        raise Exception(f"Logging configuration file not found at: {config_path}")
        
    with open(config_path, 'rt') as f:
        return yaml.safe_load(f)

def _configure_dev_logging(config):
    """Configure development-specific logging settings"""
    # Remove file handler if it exists
    if 'file' in config['handlers']:
        del config['handlers']['file']
    
    # Remove file handler from all loggers
    for logger_name in config.get('loggers', {}):
        handlers = config['loggers'][logger_name].get('handlers', [])
        if 'file' in handlers:
            handlers.remove('file')
            config['loggers'][logger_name]['handlers'] = handlers
    
    # Remove from root logger too
    if 'root' in config and 'handlers' in config['root']:
        handlers = config['root']['handlers']
        if 'file' in handlers:
            handlers.remove('file')
            config['root']['handlers'] = handlers
    
    return config

def _configure_prod_logging(config):
    """Configure production-specific logging settings"""
    # Add S3 upload handler
    config['handlers']['lambda_memory'] = {
        'class': 'shipstation_automation.utils.logger.LambdaMemoryHandler',
        'level': 'INFO',
        'bucket_name': S3_LOG_BUCKET_NAME,
        'env': ENV,
        'formatter': 'standard'
    }
    
    # Add handler to all loggers
    for logger_name in config.get('loggers', {}):
        config['loggers'][logger_name]['handlers'].append('lambda_memory')
    config['root']['handlers'].append('lambda_memory')
    
    return config

def setup_logging():
    """Initialize logging configuration for the current environment"""
    # Get directory paths
    base_dir, logs_dir = _configure_log_directory()
    
    # Load config file
    config_path = os.path.join(base_dir, 'config', 'logging', 'logging.yaml')
    config = _load_logging_config(config_path)
    
    # Apply environment-specific configuration
    if ENV == 'development':
        # In development, remove file handler
        config = _configure_dev_logging(config)
    elif ENV == 'production':
        # In production, configure file and S3 logging
        log_file_path = os.path.join(logs_dir, f'{ENV}.log')
        config['handlers']['file']['filename'] = log_file_path
        config = _configure_prod_logging(config)
    
    # Configure logging
    logging.config.dictConfig(config)
    
    # Register hook for production
    if ENV == 'production':
        import atexit
        atexit.register(lambda: logging.getLogger().handlers[0].flush())

def get_logger(module_name: str) -> logging.Logger:
    """Get a logger with standardized naming"""
    if module_name.startswith('shipstation_automation.'):
        return logging.getLogger(module_name)
    return logging.getLogger(f'shipstation_automation.{module_name}')
    
def test_logger():
    """Test various logging configurations"""
    # Import here to avoid circular imports
    from shipstation_automation.utils.output_manager import OutputManager
    
    # Create output managers for different modules
    scheduler_output = OutputManager('scheduler')
    debug_output = OutputManager('debug')
    app_output = OutputManager('core')

    # Test process start/end
    app_output.print_process_start("OUTPUT MANAGER TEST")
    
    # Test section headers and items
    app_output.print_section_header("📊 Testing Different Output Types")
    
    # Test regular logging
    scheduler_output.logger.info("Testing scheduler logger - INFO message (file only)")
    scheduler_output.logger.error("Testing scheduler logger - ERROR message (file only)")
    scheduler_output.logger.debug("Testing scheduler logger - DEBUG message (file only)")

    # Test console output
    debug_output.print_section_item("Testing debug output - INFO level", "info")
    debug_output.print_section_item("Testing debug output - WARNING level", "warning")
    debug_output.print_section_item("Testing debug output - ERROR level", "error")

    # Test specialized formatters
    app_output.print_section_header("📈 Testing Specialized Formatters")
    
    # Check if these methods exist in your OutputManager
    if hasattr(app_output, 'print_report_item'):
        app_output.print_report_item("TestGroup", 10, 5)
    else:
        app_output.print_section_item("Report: TestGroup - 10/5 items processed", color="green")
        
    if hasattr(app_output, 'print_drive_upload_item'):
        app_output.print_drive_upload_item(1, 3, "test_file.pdf")
    else:
        app_output.print_section_item(f"Upload: test_file.pdf (1/3)", color="blue")
    
    app_output.print_process_end()
    
    # Flush logs to S3 if in production mode
    if ENV == 'production':
        for handler in logging.getLogger().handlers:
            if hasattr(handler, 'flush'):
                handler.flush()
    
    print(f"\nCheck logs for output ({ENV} environment)")
