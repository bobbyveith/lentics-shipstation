import boto3
from botocore.exceptions import ClientError
import json, os
from shipstation_automation.new_main import main
from shipstation_automation.utils.logger import setup_logging
from shipstation_automation.utils.output_manager import OutputManager
from shipstation_automation.config.config import ENV


# Set up logging for the entire module
setup_logging()
output = OutputManager('app')
output.print_process_start("🚀 Starting Lambda Function")


# Initialize AWS Secrets Manager client
session = boto3.session.Session()
secrets_client = session.client(
    service_name='secretsmanager',
    region_name='us-east-2'
)

def get_credentials(secret_name):
    """
    Retrieve credentials from AWS Secrets Manager.
    
    Fetches and parses a secret from AWS Secrets Manager using the provided secret name.
    
    Args:
        secret_name (str): The name of the secret to retrieve from AWS Secrets Manager
        
    Returns:
        dict: The parsed JSON secret value as a dictionary
        
    Raises:
        ClientError: If there's an error retrieving the secret from AWS Secrets Manager
    """
    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret_value = response['SecretString']
        return json.loads(secret_value)
    
    except ClientError as e:
        # Log the error
        output.print_section_item(f"Error getting credentials: {str(e)}", log_level="error", color="red")
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

def set_program_credentials_to_environment():
    output.print_section_item("Setting up environment credentials", color="blue")
    # Secret_name for each set of api credentials that the program needs
    needed_api_credentials = ["Nuveau_Shipstation", "Lentics_Shipstation", "Lentics_Fedex", "Lentics_UPS", "Nuveau_USPS"]

    for secret_name in needed_api_credentials:
        credentials = get_credentials(secret_name)
        api_key = credentials.get('api_key')
        api_secret = credentials.get('api_secret')

        # Create developer friendly name for environment variable name
        api_key_name = f"API_KEY_{secret_name}".upper()
        api_secret_name = f"API_SECRET_{secret_name}".upper()

        os.environ[api_key_name] = api_key
        os.environ[api_secret_name] = api_secret
    
    output.print_section_item("Environment credentials set successfully", color="green")
    return None

# Call the function to set up credentials when the Lambda function file is loaded
set_program_credentials_to_environment()

def send_sns_notification(message, subject):
    """Send an SNS notification, but only in production mode"""
    if ENV == 'development':
        output.print_section_item("Development mode: Skipping SNS notification", color="yellow")
        output.print_section_item(f"Would have sent: {subject} - {message}", color="yellow")
        return None
    
    # In production, send the actual notification
    output.print_section_header("📨 Sending SNS Notification")
    topic_arn = 'arn:aws:sns:us-east-2:768214456858:Shipstation-Automation-Runtime'
    sns_client = boto3.client('sns')
    response = sns_client.publish(
        TopicArn=topic_arn,
        Message=message,
        Subject=subject
    )
    output.print_section_item("SNS notification sent successfully", color="green")
    return response

def lambda_handler(event, context):
    """Lambda function handler"""
    try:
        output.print_banner()
        main()
        
        # Send success message to SNS Topic
        send_sns_notification(
            '[+] Shipstation Automation Ran Successfuly!',
            'SS_Automation Successful'
        )
        
        # End the process successfully
        output.print_process_end(success=True)
        
        # Flush any logs to S3 in production
        for handler in output.logger.handlers:
            if hasattr(handler, 'flush'):
                handler.flush()
                
        return {'statusCode': 200}

    except Exception as e:
        # Log the error
        output.print_section_item(f"Error: {str(e)}", log_level="error", color="red")
        
        # Send Error message to SNS Topic
        send_sns_notification(
            f'[X] ERROR: Shipstation Automation did not run because: {e}',
            'Error on SS_Automation Lambda'
        )
        
        # End the process with error
        output.print_process_end(success=False)
        
        # Flush any logs to S3 in production
        for handler in output.logger.handlers:
            if hasattr(handler, 'flush'):
                handler.flush()
                
        return {'statusCode': 500}