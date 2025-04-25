import os
import uuid
import requests
import base64
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus
from typing import Dict, Optional, Any
from dotenv import load_dotenv

from shipstation_automation.schemas.ups_schema import (
    UPSAuthCredentials, 
    UPSAuthResponse,
    TransitTimeRequest,
    TransitTimeResponse,
    UPSServiceOption
)

class TokenResponse:
    """Class to represent an OAuth token response."""
    
    def __init__(self, access_token: str, token_type: str, token_expiry: datetime):
        self.access_token = access_token
        self.token_type = token_type
        self.token_expiry = token_expiry

class UPSOAuth:
    """
    Class for handling UPS API authentication with OAuth.
    """
    
    def __init__(self):
        load_dotenv()
        self.client_id = os.getenv('API_KEY_LENTICS_UPS')
        self.client_secret = os.getenv('API_SECRET_LENTICS_UPS')
        self.token_endpoint = 'https://onlinetools.ups.com/security/v1/oauth/token'
        self.access_token: Optional[str] = None
        self.token_type: Optional[str] = None
        self.token_expiry: Optional[datetime] = None

    def get_token(self) -> TokenResponse:
        """
        Get a valid OAuth token, refreshing if necessary.
        
        Returns:
            TokenResponse: Object containing the access token, token type, and expiry
        """
        if self.access_token and self.token_expiry:
            if datetime.now(timezone.utc) < self.token_expiry:
                return TokenResponse(
                    access_token=self.access_token,
                    token_type=self.token_type,
                    token_expiry=self.token_expiry,
                )

        auth_value = f"{quote_plus(self.client_id)}:{quote_plus(self.client_secret)}"
        encoded_credentials = base64.b64encode(auth_value.encode('utf-8')).decode('utf-8')

        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
        }

        data = {'grant_type': 'client_credentials'}

        response = requests.post(self.token_endpoint, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        token_info = response.json()

        self.access_token = token_info['access_token']
        self.token_type = 'Bearer'
        expires_in = int(token_info.get('expires_in', 3600))
        self.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 60)

        return TokenResponse(
            access_token=self.access_token,
            token_type=self.token_type,
            token_expiry=self.token_expiry,
        )


class UPSAPIClient:
    """UPS API client to interact with UPS shipping services."""
    
    def __init__(self):
        """Initialize the UPS API client with OAuth authentication."""
        self.base_url = 'https://onlinetools.ups.com'
        self.oauth = UPSOAuth()
        self.session = requests.Session()

    def get_headers(self) -> Dict[str, str]:
        """
        Get headers for UPS API requests with authentication.
        
        Returns:
            Dict[str, str]: Headers for UPS API requests
        """
        token = self.oauth.get_token()
        return {
            'Authorization': f"{token.token_type} {token.access_token}",
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'transactionSrc': 'testing',
            'transId': str(uuid.uuid4()),
        }

    def make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Make a request to UPS API.
        
        Args:
            method: HTTP method ('GET', 'POST', etc.)
            endpoint: API endpoint path (without base URL)
            params: Query parameters for GET requests
            data: Request payload for POST/PUT requests
            
        Returns:
            Optional[Dict[str, Any]]: JSON response from the API or None
            
        Raises:
            requests.exceptions.RequestException: If the API request fails
        """
        url = f"{self.base_url}{endpoint}"
        headers = self.get_headers()

        try:
            response = self.session.request(method, url, headers=headers, params=params, json=data)
            response.raise_for_status()
            if response.content:
                return response.json()
            return None
        except requests.exceptions.RequestException as e:
            print(f"[X] API request failed: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
            raise

    def get_transit_times(self, request: TransitTimeRequest) -> TransitTimeResponse:
        """
        Get transit times for a shipment.
        
        Args:
            request: Transit time request data
            
        Returns:
            TransitTimeResponse: Transit time response with available services
        """
        endpoint = "/api/shipments/v1/transittimes"
        payload = request.to_payload()
        
        try:
            response_data = self.make_request('POST', endpoint, data=payload)
            return TransitTimeResponse.from_api_response(response_data)
        except Exception as e:
            print(f"[X] Failed to get transit times: {e}")
            raise


def create_ups_session() -> UPSAPIClient:
    """
    Create and return a UPS API client session that can be shared across orders
    
    Returns:
        UPSAPIClient: Initialized UPS API client with valid authentication
    """
    # Initialize the UPS API client
    ups_client = UPSAPIClient()
    
    # Force authentication to happen now (this will make a call to get a token)
    ups_client.oauth.get_token()
    
    # Return the initialized client
    return ups_client


if __name__ == '__main__':
    try:
        print("[X] This file is not meant to be executed directly. Check for the main.py file.")
    except Exception as e:
        print('Error:', e)
        raise SystemExit("End Test")