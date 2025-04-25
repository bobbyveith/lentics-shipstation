from .classes import ShipStation
from dotenv import load_dotenv
import os




def get_secret(account_name):
    load_dotenv()

    if not account_name:
        raise ValueError("Account name cannot be empty")

    account_name = account_name.lower()  # Normalize input
    
    accounts = {
        'sporticulture': ('SPORTICULTURE_SHIPSTATION_API_KEY', 'SPORTICULTURE_SHIPSTATION_API_SECRET'),
        'winningstreak': ('WINNINGSTREAK_SHIPSTATION_API_KEY', 'WINNINGSTREAK_SHIPSTATION_API_SECRET'),
        'stallion': ('STALLION_SHIPSTATION_API_KEY', 'STALLION_SHIPSTATION_API_SECRET')
    }
    
    if account_name not in accounts:
        raise ValueError(f"Invalid account name: {account_name}")
    
    key_env, secret_env = accounts[account_name]
    api_key = os.getenv(key_env)
    api_secret = os.getenv(secret_env)
    
    if not api_key or not api_secret:
        raise ValueError(f"API credentials not found for account: {account_name}")
    
    return api_key, api_secret




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
