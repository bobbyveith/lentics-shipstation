# Python standard library
import base64
import json
import pprint
import time

# Third-party packages
import requests

# Local module imports
from .constants import *  # Consider replacing with specific imports
from .models import *    # Consider replacing with specific imports


class ShipStation(ShipStationBase):
    """
    Handles the details of connecting to and querying a ShipStation account.
    """

    def __init__(self, key=None, secret=None, debug=False):
        """
        Connecting to ShipStation required an account and a
        :return:
        """

        if key is None:
            raise AttributeError("Key must be supplied.")
        if secret is None:
            raise AttributeError("Secret must be supplied.")

        self.url = "https://ssapi.shipstation.com"

        self.key = key
        self.secret = secret
        self.orders = []
        self.timeout = 115.0
        self.debug = debug
        self.session = requests.Session()

        encoded_credentials = base64.b64encode(f'{self.key}:{self.secret}'.encode('utf-8')).decode('utf-8')
        header = {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/json'
        }

        self.session.headers.update(header)
        self.session.hooks["response"] = self.api_calls
    
    def api_calls(self, r, *args, **kwargs):
        """
        Handle API rate limiting and response validation for ShipStation API calls.
        Implements exponential backoff when rate limits are hit.
        """
        calls_left = r.headers.get('X-Rate-Limit-Remaining')
        time_left = r.headers.get('X-Rate-Limit-Reset')

        # Check if response is valid JSON before proceeding
        try:
            r.json()
        except:
            # If not JSON, likely a rate limit or server error
            print(f"Non-JSON response received. Headers: {r.headers}")
            print(f"Status code: {r.status_code}")
            print(f"Response text: {r.text}")
            time.sleep(5)  # Base delay for non-JSON responses
            return r

        # Handle rate limiting
        if calls_left is not None:
            calls_left = int(calls_left)
            if calls_left <= 2:
                sleep_time = 5 if time_left is None else int(time_left)
                print(f"Rate limit approaching. Calls left: {calls_left}. Sleeping for {sleep_time} seconds")
                time.sleep(sleep_time)
        else:
            # If headers are missing, implement a conservative delay
            print("Rate limit headers missing. Using default delay")
            time.sleep(2)

        return r


    def add_order(self, order):
        self.require_type(order, ShipStationOrder)
        self.orders.append(order)

    def get_orders(self):
        return self.orders

    def submit_orders(self):
        for order in self.orders:
            self.post(endpoint="/orders/createorder", data=json.dumps(order.as_dict()))

    def get(self, endpoint="", payload=None):
        url = "{}{}".format(self.url, endpoint)
        r = self.session.get(
            url, auth=(self.key, self.secret), params=payload, timeout=self.timeout
        )
        if self.debug:
            pprint.PrettyPrinter(indent=4).pprint(r.json())

        return r

    def post(self, endpoint="", data=None):
        url = "{}{}".format(self.url, endpoint)
        headers = {"content-type": "application/json"}
        r = self.session.post(
            url,
            auth=(self.key, self.secret),
            data=data,
            headers=headers,
            timeout=self.timeout,
        )
        if self.debug:
            pprint.PrettyPrinter(indent=4).pprint(r.json())

        return r

    def put(self, endpoint="", data=None):
        url = "{}{}".format(self.url, endpoint)
        headers = {"content-type": "application/json"}
        r = self.session.put(
            url,
            auth=(self.key, self.secret),
            data=data,
            headers=headers,
            timeout=self.timeout,
        )
        if self.debug:
            pprint.PrettyPrinter(indent=4).pprint(r.json())

        return r
    
    def delete(self, endpoint="", data=None):
        url = "{}{}".format(self.url, endpoint)
        headers = {"content-type": "application/json"}
        r = self.session.delete(
            url,
            auth=(self.key, self.secret),
            data=data,
            headers=headers,
            timeout=self.timeout,
        )
        if self.debug:
            pprint.PrettyPrinter(indent=4).pprint(r.json())

        return r
    
    def get_order(self, order_id: str | int, from_order_number: bool = False) -> requests.Response:
        """
        Fetches an order from ShipStation using either the internal ID or order number.

        Args:
            order_id (str | int): The identifier for the order. If from_order_number is False,
                                this should be the ShipStation internal ID. If True, this should
                                be the order number.
            from_order_number (bool, optional): Flag to indicate if order_id is an order number
                                                instead of internal ID. Defaults to False.

        Returns:
            requests.Response: The API response containing the order details.

        Raises:
            IndexError: If no order is found with the given order number.
            requests.exceptions.HTTPError: If the API request fails.
        """
        if not from_order_number:
            return self.get(endpoint=f"/orders/{order_id}")

        # First fetch the internal ID using the order number
        response = self.get(endpoint=f"/orders?orderNumber={order_id}")
        response.raise_for_status()
        
        orders = response.json().get("orders", [])
        if not orders:
            raise IndexError(f"No order found with order number: {order_id}")
        
        internal_id = orders[0]["orderId"]
        return self.get(endpoint=f"/orders/{internal_id}")

    def fetch_orders(self, parameters={}):
        """
            Query, fetch, and return existing orders from entire ShipStation account

            Args:
                parameters (dict): Dict of filters to filter by.

            Raises:
                AttributeError: parameters not of type dict
                AttributeError: invalid key in parameters dict.

            Returns:
                A <Response [code]> object.

            Examples:
                >>> ss.fetch_orders(parameters={'order_status': 'shipped', 'page': '2'})
        """
        self.require_type(parameters, dict)
        invalid_keys = set(parameters.keys()).difference(ORDER_LIST_PARAMETERS)

        if invalid_keys:
            raise AttributeError(
                "Invalid order list parameters: {}".format(", ".join(invalid_keys))
            )

        valid_parameters = {
            self.to_camel_case(key): value for key, value in parameters.items()
        }

        return self.get(endpoint="/orders/list", payload=valid_parameters)

    def fetch_webhook(self, batch_id):
        '''
            Fetches orders based off of a webhook payload. 
            '''
        return self.get(endpoint=f"/orders?importBatch={batch_id}")
    
    
    def fetch_label(self, data=None):
        """
        Fetches the shipping label for the order using the ShipStation API.
        """
        return self.post(endpoint="/orders/createlabelfororder", data=data)
    

    def get_rates(self, data=None):
        """
        Gets the rates for an order using the ShipStation API.
        """
        return self.post(endpoint="/shipments/getrates", data=data)


    def create_update_order(self, data=None):
        """
        Creates or updates an order using the ShipStation API.
        """
        return self.post(endpoint="/orders/createorder", data=data)


    def add_tag(self, data=None):
        """
        Adds a tag to an order using the ShipStation API.
        """
        return self.post(endpoint="/orders/addtag", data=data)
    
    def remove_tag(self, data=None):
        """
        Removes a tag from an order using the ShipStation API.
        """
        return self.post(endpoint="/orders/removetag", data=data)
    
    def get_shipment(self, order_id: int):
        """
        Gets a shipment using the ShipStation API.
        """
        return self.get(endpoint=f"/shipments?orderId={order_id}")
    
    def void_label(self, data=None):
        """
        Voids a shipping label using the ShipStation API.
        """
        return self.post(endpoint="/shipments/voidlabel", data=data)
    
    def add_funds(self, data=None):
        """
        Adds funds to the account using the ShipStation API.
        """
        return self.post(endpoint="/carriers/addfunds", data=data)
    
    def list_carriers(self):
        """
        Lists the carriers available in the ShipStation account.
        """
        return self.get(endpoint="/carriers")
    
    def list_orders_by_tag(
        self, 
        tag: int, 
        order_status: str | None = None, 
        page: str | None = None, 
        page_size: str | None = None
        ) -> requests.Response:
        """
        Lists the orders by tag using the ShipStation API.

        Args:
            tag (int): The tag ID to filter orders by
            order_status (str | None): Filter by order status. Valid values include:
                'awaiting_payment', 'awaiting_shipment', 'shipped', 'on_hold',
                'cancelled', or any other status supported by ShipStation.
            page (str | None): Page number for pagination
            page_size (str | None): Number of items per page (max 500)

        Returns:
            requests.Response: The API response containing the filtered orders

        Raises:
            requests.exceptions.HTTPError: If the API request fails
            ValueError: If tag is not a positive integer
        """
        # Validate tag
        if not isinstance(tag, int) or tag <= 0:
            raise ValueError("tag must be a positive integer")

        # Build parameters dictionary with camelCase keys for ShipStation API
        params = {'tagId': tag}
        
        if order_status is not None:
            params['orderStatus'] = order_status
        if page is not None:
            params['page'] = page
        if page_size is not None:
            params['pageSize'] = page_size
        
        return self.get(endpoint="/orders/listbytag", payload=params)
    
    def cancel_order(self, shipstation_order_id):
        """
        Cancels an order using the ShipStation API using order ID.
        """
        r = self.delete(endpoint=f"/orders/{shipstation_order_id}")
        r.raise_for_status()
        success = r.json().get("approved")
        if success:
            return True
        return False
    
    def list_account_tags(self):
        """
        Lists the tags available in the ShipStation account.
        """
        return self.get(endpoint="/accounts/listtags")

