import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import logging
from io import BytesIO
from datetime import datetime
import pytz
from shipstation_automation.config.config import TIMEZONE

class S3BucketIntegration:
    def __init__(self, bucket_name, region_name='us-east-2'):
        s3_config = Config(
            signature_version='s3v4',
            region_name=region_name
        )
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3', config=s3_config)
        self.logger = logging.getLogger('integrations.aws')

    def upload_log_file(self, env: str, log_content: str) -> bool:
        """Upload log file to S3, appending to existing file if present"""
        
        today = datetime.now(pytz.timezone(TIMEZONE)).strftime('%Y-%m-%d')
        s3_key = f'{env}/{today}.log'
        
        try:
            # Try to download existing log file for today
            temp_file = BytesIO()
            existing_content = ''
            
            try:
                self.s3_client.download_fileobj(self.bucket_name, s3_key, temp_file)
                temp_file.seek(0)
                existing_content = temp_file.read().decode('utf-8')
            except ClientError:
                pass  # No existing file is fine, we'll create a new one

            # Combine contents if there was an existing file
            combined_content = existing_content + log_content if existing_content else log_content

            # Upload combined content
            upload_buffer = BytesIO(combined_content.encode('utf-8'))
            self.s3_client.upload_fileobj(upload_buffer, self.bucket_name, s3_key)
            
            self.logger.info(f'Successfully uploaded {env} logs to S3: {s3_key}')
            return True

        except Exception as e:
            self.logger.error(f'Failed to upload/append logs for {env}: {str(e)}')
            return False