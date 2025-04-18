import base64, requests, json, os
from datetime import datetime, timedelta
import pytz


"""
This file holds few helpful utilites that might be used during development.

Most of this file is for saved functionsn that are being kept for potential future use
"""


def get_product_dimensions(order, product_id):
    '''
    Requests product info from ShipStation API using shipstation generated product ID.
    Was meant to be a means of getting the product dimensions for multi orders using the products endpoint.
    Doesn't work for nuvuea because the size info needs to be preloaded into every product.
    Can use preset Groups on Shipstation UI, but then have to assign every sku manually to the group.
    This wont work for products which have never been sold yet.

    So, the decision is to just used a hard coded mapping to determine product size.
    Nuveau products use the sku prefix to determine size
    Lentics products use a code injected into the warehouse_location field of item_dicts (multi-orders only)
    '''
    productId = str(product_id)

    url = (f"https://ssapi.shipstation.com/products/{productId}")
    api_key = order.shipstation_client.key
    api_secret = order.shipstation_client.secret
    encoded_credentials = base64.b64encode(f'{api_key}:{api_secret}'.encode('utf-8')).decode('utf-8')
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raises an exception for HTTP error codes

        response_json = response.json()

        pretty_response = json.dumps(response_json, indent=4)

        # length = response_json["length"]
        # width = response_json["width"]
        # height = response_json["height"]
        # weight = response_json["weight"]

        # dims = f"L: {length} W: {width} H: {height} Oz: {weight}"

        return pretty_response
        
    except requests.exceptions.RequestException as e:
        print(response.text)
        print(f"An error occurred: {e}")
        return False
    



def list_account_tags(order_object):
    '''
    Lists the tags availble for the given Shipstation Account
    Only Use during development to get tagID's for tag_order()

    Returns: None --> prints list to console showing the optional tags for the SS account

    Add New Tags: --> Can be added on Order page os SS Front end
    '''
    url = "https://ssapi.shipstation.com/accounts/listtags"
    api_key = order_object.shipstation_client.key
    api_secret = order_object.shipstation_client.secret
    encoded_credentials = base64.b64encode(f'{api_key}:{api_secret}'.encode('utf-8')).decode('utf-8')

    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.get(url, headers=headers)

        print(response.status_code)
        print(response.text)

    except Exception as e:
        print(e)

    return None




def find_duplicate_orders(list_of_order_objects):
    '''
    This function identifies orders that are made by a repeate customer.
    Was going to be used to find, and then merge orders, but merging is not an option through API.
    This func can still be utilized to find the orders and mark them, but this can easily be done on the UI.
    So this is being saved for a rainy day
    '''
    # Dictionary to track unique combinations and order numbers
    seen_combinations = {}

    for order in list_of_order_objects:
        # If these attributes match between two different orders, then are from a Repeat Customer
        combination = f"{order.Customer.name}-{order.Customer.address1}-{order.Customer.postal_code}-{order.order_warehouseId}"

        # Check if combination already exists
        if combination in seen_combinations:
            # Append current order number to the list of order numbers for this combination
            seen_combinations[combination].append(order.order_key)
        else:
            # Create a new entry in the dictionary
            seen_combinations[combination] = [order.order_key]

    # Filter out combinations with only one order number (non-duplicates)
    duplicate_combinations = {key: value for key, value in seen_combinations.items() if len(value) > 1}
    list_of_order_to_merge = list(duplicate_combinations.values())
    if list_of_order_to_merge:
        return list_of_order_to_merge
    else:
        return None
    


def write_fedex_response_to_file(response_json):
    '''
    This is used for testing only

    PURPOSE: writes large fedex response to JSON file for easy developer reading
    '''

    filename = './fedex_response.json'

    try: 
        # Clear existing data in the file if it exists
        if os.path.exists(filename):
            with open(filename, 'w') as file:
                file.write("")

        # Pretty print the JSON response with an indentation level of 4 spaces
        pretty_response = json.dumps(response_json, indent=4)

        # Open the file in append mode ('a') and write the pretty printed JSON response to the file
        with open(filename, 'a') as file:
            file.write(pretty_response)

        print('[+] Wrote JSON to File..')

    except Exception as e:
        print("[X] Could not write response to JSON File")
        print(f"Error: {e}")

    return None



def get_ship_date():
    """
    Calculates the shipping date based on Eastern Standard Time (EST).

    Returns:
    - str: The calculated shipping date in 'YYYY-MM-DD' format.

    This function determines the shipping date by considering the current time in Eastern Standard Time (EST).
    If the current day is Monday, Wednesday, or Friday before 5 PM EST, it returns today's date as the shipping date.
    Otherwise, it calculates and returns the date of the nearest Monday, Wednesday, or Friday in the future.
    """
    # Define the EST timezone
    est = pytz.timezone('America/New_York')
    
    # Get the current time in EST
    current_time = datetime.now(est)
    if current_time.hour > 17:
        # Warehouse closes at 5pm, calculate using next day for else block to work properly
        current_time += timedelta(days=1)
    
    # Calculate the shipping date based on the current time
    if current_time.weekday() in {0, 2, 4} and current_time.hour < 17:
        shipping_date = current_time.strftime('%Y-%m-%d')
    else:
        # Calculate the days until the next Monday, Wednesday, or Friday
        days_until_monday = (0 - current_time.weekday()) % 7
        days_until_wednesday = (2 - current_time.weekday()) % 7
        days_until_friday = (4 - current_time.weekday()) % 7
        
        # Determine the nearest weekday and calculate the shipping date
        if days_until_monday <= days_until_wednesday and days_until_monday <= days_until_friday:
            shipping_day = current_time + timedelta(days=days_until_monday)
        elif days_until_wednesday <= days_until_friday:
            shipping_day = current_time + timedelta(days=days_until_wednesday)
        else:
            shipping_day = current_time + timedelta(days=days_until_friday)
        shipping_date = shipping_day.strftime('%Y-%m-%d')
    
    return shipping_date # Output format: YYYY-MM-DD


if __name__ == "__main__":
    date = get_ship_date()

    print(date)