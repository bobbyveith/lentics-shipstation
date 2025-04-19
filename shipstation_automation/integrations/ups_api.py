import requests
from urllib.parse import quote_plus
import base64
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time
import os
from typing import Dict, Optional, Any

from shipstation_automation.schemas.ups_schema import (
    UPSAuthCredentials, 
    UPSAuthResponse,
    TransitTimeRequest,
    TransitTimeResponse,
    UPSServiceOption
)

class UPSAuthToken:
    """
    Class for handling UPS API authentication.
    
    This class manages the OAuth authentication flow with UPS API,
    including token acquisition and refresh.
    """
    
    def __init__(self, credentials: Optional[UPSAuthCredentials] = None):
        """
        Initialize the UPS authentication token manager.
        
        Args:
            credentials: UPS API credentials (client_id and client_secret)
                        If None, credentials will be loaded from environment variables
        """
        load_dotenv()
        self.session = requests.Session()
        
        if credentials:
            self.credentials = credentials
        else:
            # Load credentials from environment variables
            self.credentials = UPSAuthCredentials(
                client_id=os.getenv('API_KEY_LENTICS_UPS', ''),
                client_secret=os.getenv('API_SECRET_LENTICS_UPS', '')
            )
        
        self.auth_response = None
        self.token_expiry_time = None

    def get_token(self) -> str:
        """
        Get a valid OAuth token, refreshing if necessary.
        
        Returns:
            str: The access token for UPS API authentication
        """
        # Check if token exists and is still valid
        if not self.auth_response or not self.token_expiry_time or datetime.now() >= self.token_expiry_time:
            self._refresh_token()
            
        return self.auth_response.access_token
            
    def _refresh_token(self) -> None:
        """
        Refresh the OAuth token by requesting a new one from UPS API.
        
        Raises:
            Exception: If token request fails after retries
        """
        # Prepare credentials for Basic Auth
        auth_value = f"{quote_plus(self.credentials.client_id)}:{quote_plus(self.credentials.client_secret)}"
        encoded_credentials = base64.b64encode(auth_value.encode('utf-8')).decode('utf-8')
        
        headers = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': '*/*',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Origin': 'https://developer.ups.com',
            'User-Agent': 'Python requests library'
        }
        
        data = {
            'grant_type': 'client_credentials'
        }
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            response = self.session.post(
                'https://wwwcie.ups.com/security/v1/oauth/token', 
                headers=headers, 
                data=data
            )
            
            if response.status_code == 200:
                print("[+] UPS OAuth token request successful!")
                token_info = response.json()
                self.auth_response = UPSAuthResponse(
                    access_token=token_info.get('access_token'),
                    token_type=token_info.get('token_type', 'Bearer'),
                    expires_in=token_info.get('expires_in', 3600)
                )
                # Set token expiry time (subtract 60 seconds as buffer)
                self.token_expiry_time = datetime.now() + timedelta(seconds=self.auth_response.expires_in - 60)
                return
            else:
                print(f"[X] Token request failed: {response.text}")
                retry_count += 1
                print(f"Retrying... ({retry_count}/{max_retries})")
                time.sleep(1)
        
        print("[X] Failed to get UPS OAuth token after retries.")
        raise Exception("Failed to acquire UPS OAuth token")


class UPSAPIClient:
    """
    UPS API client for interacting with UPS shipping services.
    
    This class provides methods to make authenticated requests to UPS API
    endpoints, focusing on shipping rate and transit time information.
    """
    
    BASE_URL = "https://wwwcie.ups.com"
    
    def __init__(self, auth_token: Optional[UPSAuthToken] = None):
        """
        Initialize the UPS API client.
        
        Args:
            auth_token: UPS authentication token manager
                        If None, a new UPSAuthToken instance will be created
        """
        self.auth = auth_token if auth_token else UPSAuthToken()
        self.session = requests.Session()
        
    def get_headers(self) -> Dict[str, str]:
        """
        Get headers for UPS API requests with authentication.
        
        Returns:
            Dict[str, str]: Headers for UPS API requests
        """
        return {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Authorization': f'Bearer {self.auth.get_token()}',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Host': 'wwwcie.ups.com',
            'Origin': 'https://developer.ups.com',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'transactionSrc': 'testing',
            'transId': '12345612345612345612345612345612',
            'User-Agent': 'Python requests library',
        }
        
    def make_request(
        self, 
        endpoint: str, 
        method: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a request to UPS API.
        
        Args:
            endpoint: API endpoint path (without base URL)
            method: HTTP method ('GET', 'POST', etc.)
            data: Request payload for POST/PUT requests
            params: Query parameters for GET requests
            
        Returns:
            Dict[str, Any]: JSON response from the API
            
        Raises:
            Exception: If the API request fails
        """
        url = f"{self.BASE_URL}{endpoint}"
        headers = self.get_headers()
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers, params=params)
            elif method.upper() == 'POST':
                response = self.session.post(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"[X] API request failed: {e}")
            if hasattr(e.response, 'text'):
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
            response_data = self.make_request(endpoint, method='POST', data=payload)
            return TransitTimeResponse.from_api_response(response_data)
        except Exception as e:
            print(f"[X] Failed to get delivery times: {e}")
            raise
            

if __name__ == '__main__':
    try:
        print("[X] This file is not meant to be executed directly. Check for the main.py file.")
    except Exception as e:
        print('Error:', e)
        raise SystemExit("End Test")