from .classes import ShipStation
from dotenv import load_dotenv
import os
from shipstation_automation.utils.output_manager import OutputManager

output = OutputManager(__name__)

def get_secret(account_name):
    """
    Retrieves API credentials from environment variables.
    
    Args:
        account_name (str): The name of the account to get credentials for
        
    Returns:
        tuple: (api_key, api_secret)
        
    Raises:
        ValueError: If account_name is empty or credentials aren't found
    """
    try:
        load_dotenv()

        if not account_name:
            error_msg = "Account name cannot be empty"
            output.print_section_item(f"[X] Error: {error_msg}", color="red")
            raise ValueError(error_msg)
        
        # Safeguard for the account name
        account_name = account_name.upper()

        api_key = os.getenv("API_KEY_" + account_name)
        api_secret = os.getenv("API_SECRET_" + account_name)

        if not api_key or not api_secret:
            error_msg = f"API credentials not found for account: {account_name}"
            output.print_section_item(f"[X] Error: {error_msg}", color="red")
            raise ValueError(error_msg)
        
        return api_key, api_secret
    except Exception as e:
        output.print_section_item(f"[X] Unexpected error getting credentials: {str(e)}", color="red")
        raise



def connect_to_api(account_name):
    """
        Connect to the ShipStation API using the API keys retrieved from Secrets Manager.

        Args:
            uniqueID
        Return:
            object: A ShipStation connection objects.
    """

    # Account Credentials
    api_key, api_secret = get_secret(account_name)

    # Connect to the ShipStation API
    ss_client = ShipStation(key=api_key, secret=api_secret)
    return ss_client
