import boto3
from botocore.exceptions import ClientError
import json, os
from main import main
from shipstation_automation.utils.logger import setup_logging, get_logger


# Initialize AWS Secrets Manager client
session = boto3.session.Session()
secrets_client = session.client(
    service_name='secretsmanager',
    region_name='us-east-2'
)

def get_credentials(secret_name):
    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret_value = response['SecretString']
        return json.loads(secret_value)
    
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e



def set_program_credentials_to_environment():

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

    return None

# Call the function to set up credentials when the Lambda function file is loaded
set_program_credentials_to_environment()

def lambda_handler(event, context):
    """Lambda function handler"""
    # Set up logging for this run
    setup_logging()
    logger = get_logger('app')
    
    try:
        logger.info("Starting Shipstation Automation Lambda function")
        main()
        
        # Send success message to SNS Topic
        sns_client = boto3.client('sns')
        topic_arn = 'arn:aws:sns:us-east-2:768214456858:Shipstation-Automation-Runtime'
        response = sns_client.publish(
            TopicArn=topic_arn,
            Message='[+] Shipstation Automation Ran Successfuly!',
            Subject='SS_Automation Successful'
        )
        
        logger.info("Shipstation Automation completed successfully")
        # Flush any logs to S3 in production
        for handler in logger.handlers:
            if hasattr(handler, 'flush'):
                handler.flush()
                
        return {'statusCode': 200}

    except Exception as e:
        # Log the error
        logger.error(f"Shipstation Automation failed: {str(e)}", exc_info=True)
        
        # Send Error message to SNS Topic
        sns_client = boto3.client('sns')
        topic_arn = 'arn:aws:sns:us-east-2:768214456858:Shipstation-Automation-Runtime'
        response = sns_client.publish(
            TopicArn=topic_arn,
            Message=f'[X] ERROR: Shipstation Automation did not run because: {e}',
            Subject='Error on SS_Automation Lambda'
        )
        
        # Flush any logs to S3 in production
        for handler in logger.handlers:
            if hasattr(handler, 'flush'):
                handler.flush()
                
        return {'statusCode': 500}