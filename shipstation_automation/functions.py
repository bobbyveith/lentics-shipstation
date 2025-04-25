from dotenv import load_dotenv
import json, os, time, pyfiglet, requests
from shipstation_automation.integrations.shipstation.v1.api import *
from shipstation_automation.classes import Order
from shipstation_automation.integrations.ups.ups_api import UPSAPIClient
from shipstation_automation.services.ups_service import UPSService
from shipstation_automation.fedex_api import create_fedex_session
from shipstation_automation.customer_log import create_s3_client_session
from shipstation_automation.utils.output_manager import OutputManager

output = OutputManager(__name__)

__author__ = ["Rafael Malcervelli", "Bobby Veith"]
__company__ = "Lentics, Inc."


def print_banner():
    """
        Print the banner for the ShipStation Automation script.

        Args:
            None
        Return:
            None
    """
    banner = "ShipStation Automation"
    ascii_banner = pyfiglet.figlet_format(banner)
    print(ascii_banner)


def print_green(text):
    """
    Prints the given text in green color.

    Parameters:
    - text (str): The text to be printed.

    Returns:
    - None
    """
    # ANSI escape code for green color
    green_color_code = '\033[92m'
    
    # ANSI escape code to reset color back to default
    reset_color_code = '\033[0m'
    
    # Print the text in green color
    print(f"{green_color_code}{text}{reset_color_code}")

def print_red(text):
    """
    Prints the given text in red color.

    Parameters:
    - text (str): The text to be printed.

    Returns:
    - None
    """
    # ANSI escape code for red color
    red_color_code = '\033[91m'
    
    # ANSI escape code to reset color back to default
    reset_color_code = '\033[0m'
    
    # Print the text in red color
    print(f"{red_color_code}{text}{reset_color_code}")




def print_yellow(text):
    """
    Prints the given text in yellow color.

    Parameters:
    - text (str): The text to be printed.

    Returns:
    - None
    """
    # ANSI escape code for yellow color
    yellow_color_code = '\033[93m'
    
    # ANSI escape code to reset color back to default
    reset_color_code = '\033[0m'
    
    # Print the text in yellow color
    print(f"{yellow_color_code}{text}{reset_color_code}")




def get_store_ids(name_of_store):
    '''
        Gets the store_ids related to the shipstation account.
        Uncomment to use Shipstation API to get new list of store_ids

        Args:
            Shipstation Connection object
        Return:
            dict_of_store_ids (dict) : Keys = Store Name : Values = Store_ids

    '''
    # try:
    #     response = shipstation.get(endpoint="/stores?showInactive=false")
    #     response.raise_for_status()
    #     list_of_stores = response.json()
    #     # These stores are active but we still want to ignore them
    #     ignore_list = ['Manual Orders', 'Pop Creations', '3D Art Co Ebay']

    #     dict_of_store_ids = {}
    #     for store in list_of_stores:
    #         store_name = store["storeName"]
    #         if store_name in ignore_list:
    #             continue
    #         dict_of_store_ids[store_name] = store["storeId"]

    if name_of_store == 'nuveau':
        dict_of_store_ids = {'HHB - WorX of Art': 335780, 'Nuveau': 165397, 'Nuveau Ebay': 317090, 'Nuveau Etsy': 165604}
        return dict_of_store_ids
    elif name_of_store == 'lentics':
        dict_of_store_ids = {'3D Art Co Amazon': 399784, '3D Art Co Etsy': 399729, 'Gift Haven - Amazon': 399912}
        return dict_of_store_ids

    # except Exception as e:
    #     print("[X] Error getting the list of store_ids!")
    #     print(e)
    #     return None



def refresh_stores(name_of_store, shipstation):
    """
    Refreshes all active stores on the shipstation account to ensure all new orders are loaded on Shipstations end.

    Args:
        shipstation (object): Shipstaion connection object
    
    Return: No return
    
    """
    dict_of_store_ids = get_store_ids(name_of_store) # Can pass shipstation client instead to get newly generated list of store_ids

    for store_name, store_id in dict_of_store_ids.items():
        try:
            output.print_section_item(f"[+] Refreshing store: {store_name}", color="green")
            output.print_section_item(f"[+] Shipstation: {shipstation}", color="green")

            response = shipstation.post(endpoint=f"/stores/refreshstore?storeId={store_id}")
            response_json = response.json()
            output.print_section_item(f"[+] Response: {response_json}", color="green")
            response.raise_for_status()

            response_json = response.json()
            if response_json["success"] != 'true':
                raise RuntimeError(f"200 Code but not able to refresh {store_name}")
            time.sleep(0.5)
            
        except requests.exceptions.HTTPError as e:
            print(f"[X] Error: Unable to refresh store {store_name}")
            print(response.status_code)
            print(e)


# Used for Debugging Only
def fetch_order(client, order_Id):
    response = client.fetch_orders(parameters={'order_number': order_Id})
    if response.status_code == 200:
        response_json = response.json()

        pretty_json = json.dumps(response_json, indent=4)
        print(pretty_json)
    else:
        print("[X] Error getting order")
        print(response.status_code)
        print(response.text)



def fetch_orders_with_retry(dict_of_shipstation_clients, max_retries=10, delay=5):
    """
        Attempts to fetch orders with a specified number of retries.

        Args:
            dict_of_shipstation_clients (dict): Keys = name_of_store : Values =  The ShipStation connection object.
            max_retries (int): Maximum number of retries.
            delay (int): Delay between retries in seconds.

        Return:
            response (requests.models.Response): The response object from the ShipStation API.
    """
    # Attempt to fetch orders with retries
    for attempt in range(max_retries):
        try:
            for name_of_store, client_shipstation in dict_of_shipstation_clients.items():
                refresh_stores(name_of_store, client_shipstation)

                list_of_orders = []
                dict_of_shipstation_clients[name_of_store] = (list_of_orders, client_shipstation)
                list_of_orders.append(client_shipstation.fetch_orders(parameters={'order_status': 'awaiting_shipment'}))
                # Sleep before switching shipstation_clients to avoid refresh_stores() timeout error
                time.sleep(1.5)
            return dict_of_shipstation_clients
        except Exception as e:
            print(f"[X] Attempt {attempt+1} failed with error: {e}")
            time.sleep(delay)  # Wait before retrying
    return None




def connect_to_api():
    """
        Connect to the ShipStation API using the API keys stored in the .env file.

        Args:
            None
        Return:
            list: A list of ShipStation connection objects.
    """
    # Load API keys from .env file
    load_dotenv()

    # ======== ACCOUNTS =================
    # Nuveau account
    nuveau_api_key     = os.getenv("API_KEY_NUVEAU_SHIPSTATION")
    nuveau_api_secret  = os.getenv("API_SECRET_NUVEAU_SHIPSTATION")
    # Lentics account
    lentics_api_key    = os.getenv("API_KEY_LENTICS_SHIPSTATION")
    lentics_api_secret = os.getenv("API_SECRET_LENTICS_SHIPSTATION")
    # ===================================

    # Connect to the ShipStation API
    # Nuveau account
    ss_nuveau = ShipStation(key=nuveau_api_key, secret=nuveau_api_secret)

    # Lentics account
    ss_lentics = ShipStation(key=lentics_api_key, secret=lentics_api_secret)

    return {"nuveau": ss_nuveau, "lentics": ss_lentics}




def get_tag_id(order_object, tag_reason: str):
    """
    Returns the tag_id corresponding to the specified tag reason for the given order.

    Tags are created on the front end of each ShipStation account and are automatically assigned
    a unique tag_id. This function retrieves the tag_id based on the order's store name and the
    specified tag reason.

    Parameters:
    - order_object: The order object containing information about the order, including the store name.
    - tag_reason (str): The reason for applying the tag, such as "Multi-Order".

    Returns:
    - int or None: The tag_id corresponding to the specified tag reason and store name. Returns None
    if the tag_id is not available for the given store name and tag reason combination.
    """

    # Keys are shipstation accounts and secondary keys are tag_reasons
    account_tag_id_mapping = {
        "nuveau": {
            "Multi-Order"           : 52943,
            "No-Dims"               : 52944,
            "Ready"                 : 52987,
            "No-DeliveryDate"       : 52992,
            "No API Keys"           : 53068,
            "No SS Carrier Rates"   : 53339,
            "No UPS Rate"           : 53341,
            "No USPS Rate"          : 53342,
            "No Fedex Rate"         : 53343,
            "Shipping not set"      : 53344,
            "Double-Order"          : 53526
        },
        "lentics": {
            "Multi-Order"           : 166210,
            "No-Dims"               : 166211,
            "Ready"                 : 166212,
            "No-DeliveryDate"       : 166703,
            "No API Keys"           : 166471,
            "No SS Carrier Rates"   : 166704,
            "No UPS Rate"           : 166702,
            "No USPS Rate"          : 166701,
            "No Fedex Rate"         : 166700,
            "Shipping not set"      : 166699,
            "Double-Order"          : 166945,
        }
    }

    # Name of the ss_acount for the order
    ss_account = order_object.store_name

    tag_id = account_tag_id_mapping[ss_account][tag_reason]

    return tag_id




def tag_order(order_object, tag_reason: str):
    """
    Tags a specific order with a specified message to be seen on ShipStation's front end

    Params: 

    Valid Reasons List:
        "Multi-Order" : Use when multiple items are in one order
    """

    # Returns the specific tag ID for the relevant SS account & reason
    tag_id = get_tag_id(order_object, tag_reason)

    # Set the payload
    payload = {
        "orderId": order_object.order_id,
        "tagId": tag_id
    }

    try:
        # URL & Headers are included in the shipstation_client session
        response = order_object.shipstation_client.post(endpoint="/orders/addtag", data=json.dumps(payload))
        response.raise_for_status()

        response_json = response.json()
        # If code in 200 range, but not successful
        if response_json["success"] == False:
            raise requests.HTTPError(f'Request in 200 but Success = False')
        
        return True

    except Exception as e:
        print_yellow("[!] Warning: Could not tag order! ")
        print(response.status_code)
        print(response.text)
        print(e)

        return False




def multi_dims_lentics(order):
    '''
    Sets weight and demensions for multi-orders from Lentics Shipstation account
    '''
    def list_box_sizes(order):
        """
        Determine list of box sizes based on the quantity and box size of each item in an order.

        Parameters:
        - order: Order object containing shipment information.

        Returns:
        - list_of_box_sizes: A list of box sizes determined based on the order's items.

        Algorithm:
        1. Iterate through the items in the order.
        2. Determine the size (dirived from warehouse location) and qunatity for each item.
        3. Use the `get_box_sizes` function to calculate box sizes based on the location and quantity.
        4. Append the calculated box sizes to the list_of_box_sizes.

        Note: The `get_box_sizes` function retrieves size information from predefined mappings for Stallion and Lentics products.

        """
        def get_box_sizes(quantity, warehouse_location):
            """
            Get list of box sizes based on the quantity and size of an item.

            Parameters:
            - quantity: The quantity of the item.
            - warehouse_location: The warehouse location information, repuposed to pass size information from shipstation api

            Returns:
            - box_sizes: A list of dictionaries containing box dimensions and weight information.

            Algorithm:
            1. Determine the type of product based on the warehouse location prefix ('ST' for Stallion, others for Lentics).
            2. Extract the size code from the warehouse location.
            3. Check if the size code exists in the corresponding mapping (stallion_mapping for Stallion, lentics_mapping for Lentics).
            4. If the size code is found, append the corresponding size information to box_sizes based on the quantity.
            5. Return the list of box sizes.

            Note: The stallion_mapping and lentics_mapping dictionaries contain predefined size information for different product types.
            Note: Both multi_orders and double_orders can contain items with quantity > 1, this is why we range(quantity) within the func.

            Example Usage:
            box_sizes = get_box_sizes(2, 'ST | 2024')
            # Returns [{'L': 23, 'W': 31, 'H': 2.0, 'Ounces': 96}, {'L': 23, 'W': 31, 'H': 2.0, 'Ounces': 96}]

            """
            # Weight & dimensions info for Stallion products
            stallion_mapping = {
                "1218" : {"L" : 16, "W": 20, "H": 2.0, "Ounces": 80},
                "1620" : {"L" : 19, "W": 25, "H": 2.0, "Ounces": 96},
                "1236" : {"L" : 20, "W": 35, "H": 2.0, "Ounces": 128},
                "1823" : {"L" : 19, "W": 25, "H": 2.0, "Ounces": 96},
                "1824" : {"L" : 19, "W": 25, "H": 2.0, "Ounces": 96},
                "2024" : {"L" : 23, "W": 31, "H": 2.0, "Ounces": 96},
                "2026" : {"L" : 23, "W": 31, "H": 2.0, "Ounces": 96},
                "2228" : {"L" : 23, "W": 31, "H": 2.0, "Ounces": 96},
                "2325" : {"L" : 23, "W": 31, "H": 2.0, "Ounces": 96},
                "2329" : {"L" : 23, "W": 31, "H": 2.0, "Ounces": 96},
                "2335" : {"L" : 26, "W": 38, "H": 2.0, "Ounces": 128},
                "2430" : {"L" : 26, "W": 28, "H": 2.0, "Ounces": 128},
                "2435" : {"L" : 26, "W": 28, "H": 2.0, "Ounces": 128},
                "2436" : {"L" : 26, "W": 28, "H": 2.0, "Ounces": 128},
                "2638" : {"L" : 41, "W": 29, "H": 2.0, "Ounces": 128},
                "2739" : {"L" : 41, "W": 29, "H": 2.0, "Ounces": 128},
                "2839" : {"L" : 41, "W": 29, "H": 2.0, "Ounces": 128},
                "2531" : {"L" : 26, "W": 28, "H": 2.0, "Ounces": 128},
                "0810" : {"L" : 13, "W": 13, "H": 1.0, "Ounces": 32},
            }

            # Weight & dimensions info for Lentics products
            lentics_mapping = {
                "F1" : {"L" : 20, "W": 16, "H": 1.5, "Ounces": 32},
                "P1" : {"L" : 13, "W": 18, "H": 0.1, "Ounces": 8},
                "P3" : {"L" : 17, "W": 17, "H": 0.1, "Ounces": 8},
                "F2" : {"L" : 28, "W": 24, "H": 2.0, "Ounces": 96},
                "O2" : {"L" : 19, "W": 19, "H": 1.5, "Ounces": 38}
            }

            # Initiate target variable
            box_sizes = []

            if warehouse_location.startswith("ST"): # this is Stallion product
                size_code = warehouse_location[5:]
                if size_code in stallion_mapping:
                    for _ in range(quantity):
                        box_sizes.append(stallion_mapping.get(size_code, None))
            else: # Lentics Product
                size_code = (lambda text: text[text.find('|') + 2:])(warehouse_location)
                if size_code in lentics_mapping:
                    for _ in range(quantity):
                        box_sizes.append(lentics_mapping.get(size_code, None))
            return box_sizes


        # Initialize target variable
        list_of_box_sizes = []

        # Items in order are dict with multiple items, each with their own quantity
        if order.is_multi_order:
            # Value (product_info) is a dictionary
            for item , product_info in order.Shipment.items_dict.items():
                # Multi orders skip this during Order() initiation, so must initiate this attribute here
                sku = product_info['sku']
                order.Shipment.item_sku = sku

                # Main business logic
                quantity = product_info['quantity']
                warehouse_location = product_info['warehouseLocation']  # This shipstation field is repurposed to carry hidden message about product size
                box_sizes = get_box_sizes(quantity, warehouse_location)

                # Handles for when quantity of product > 1
                for box_size in box_sizes:
                    list_of_box_sizes.append(box_size)

        # Items in order are a list, one item with quantity > 1
        elif order.is_double_order:
            items_list = order.Shipment.items_list
            # Main business logic
            quantity = items_list[0]['quantity']
            warehouse_location = items_list[0]['warehouseLocation']  # This field is repurposed to carry hidden message about product size
            list_of_box_sizes = get_box_sizes(quantity, warehouse_location)
        

        return list_of_box_sizes


    # Every item in the order has a box size
    list_of_box_sizes = list_box_sizes(order)
    
    # If any product is missing size info, False is used as a warning
    if None in list_of_box_sizes:
        return False
    
    # Calculate total size and weight
    biggest_box = max(list_of_box_sizes, key=lambda x: x["L"] + x["W"])
    total_weight = sum(box["Ounces"] for box in list_of_box_sizes)
    total_height = sum(box["H"] for box in list_of_box_sizes)

    # Update the Order Object attributes
    order.Shipment.length = biggest_box["L"]
    order.Shipment.width =  biggest_box["W"]
    order.Shipment.height = total_height
    order.Shipment.weight = {'WeightUnits': 1, 'units': 'ounces', 'value': total_weight}
    
    return True



def multi_dims_nuveau(order):
    '''
    Sets weight and demensions for multi-orders from Nuveau Shipstation account
    '''
    def list_box_sizes(order):
        """
        Calculate box sizes based on SKU and quantity for items in an order.

        Parameters:
        - order: An object representing an order, containing information about items and quantities.

        Returns:
        - list_of_box_sizes: A list of dictionaries containing box dimensions and weight information for the items in the order.

        Algorithm:
        1. Define a mapping between SKU names and their corresponding dimensions and weights.
        2. Define a list of specific SKU names for Billy Bass products.
        3. Implement the get_box_sizes function to calculate box sizes based on SKU and quantity.
        4. Iterate through the items in the order:
        - For multi-order items, calculate box sizes based on each prodcuts SKU and quantity using get_box_sizes.
        - For double-order items, calculate box sizes based on the first item's SKU and quantity using get_box_sizes.
        - Raise a RuntimeError if neither multi-order nor double-order criteria are met.

        Note: This function assumes certain attributes and structures within the order object, such as 'is_multi_order', 'is_double_order', 'Shipment', 'items_dict', and 'items_list'.

        Example Usage:
        order = ...
        box_sizes = list_box_sizes(order)
        # Returns [{'L': 13, 'W': 18, 'H': 0.1, 'Weight': 8}] or similar list of box size dictionaries.

        """

        def get_box_sizes(sku, quantity):
            """
            Calculate box sizes based on SKU and quantity.

            Parameters:
            - sku: str
                The SKU (Stock Keeping Unit) of the product.
            - quantity: int
                The quantity of the product.

            Returns:
            - list
                A list of dictionaries containing box dimensions and weight information.

            Description:
            This function calculates the box sizes based on the given SKU and quantity. It uses predefined mappings between SKUs and their corresponding dimensions and weights. If the SKU is not in the list of specific Billy Bass SKUs, it calculates the box sizes based on the SKU prefix using the dimensions_to_sku_mapping. If the SKU is in the list of Billy Bass SKUs, it uses predefined dimensions for Billy Bass products.

            Example:
            sku = 'P1'
            quantity = 5
            box_sizes = get_box_sizes(sku, quantity)
            # Returns [{'L': 13, 'W': 18, 'H': 0.1, 'Weight': 8}, ...] or a similar list of dictionaries with box size information.
            """

            list_of_billyBass_skus = ['M-BBass 2', 'Billy Bass 02', 'Gemmy01', 'Gemmy03', 'Gemmy Big Mouth Billy Bass 3', 
                                    'Gemmy BBass3', 'M-BBass', 'Billy Bass Original', 'L-BBass1', 'L-BBass2', 'L-BBass3']

            list_of_fresh_stools = ['Gel Replacment 8 Pack', 'FS-Black', 'FS- White + 4 Gels', 'FS- White', 'FS- Pink', 'FS- Gray', 
                                    'FS- Blue', 'FS- Black', 'FS - White', 'FS - Pink + 4 Gels', 'FS - Pink', 'FS - Gray + 4 Gels', 
                                    'FS - Gray', 'FS - Blue + 4 Gels', 'FS - Blue', 'FS - Black']
            # Establish SKU/Dimensions Mapping --> keys: (Lenght/in, Width/in, Height/in, Weight/lbs) -> Values: sku names
            dimensions_to_sku_mapping = {
                'P1': (13, 18, 0.1, 8),
                'P2': (13, 18, 0.1, 8),
                'F1': (22, 15, 1.5, 40),
                'T1': (22, 16.5, 1.5, 50),
                'F2': (28, 22, 1.5, 80),
                'T2': (28, 22, 1.5, 80),
                'F3': (41, 29, 2.0, 176),
                'T3': (41, 29, 2.0, 192),
                'O2': (21, 20, 1.5, 48),
                'O3': (28, 27, 1.5, 96),
                'O4': (21, 29, 1.5, 136),
                'BB': (12.5, 8.5, 4.5, 32),
                'FS': (15.75, 8.75, 3.25, 32)
            }

            # Initiate target varaible
            box_sizes = []

            if sku in list_of_billyBass_skus:
                for _ in range(quantity):
                    box_sizes.append(dimensions_to_sku_mapping['BB'])

            if sku in list_of_fresh_stools:
                dims = dimensions_to_sku_mapping['FS']
                # If the skus includes 4 Gels then add 16oz to the weight
                if '+' in sku:
                    dims[3] += 16
                box_sizes.append(dims)

            else:
                for _ in range(quantity):
                    box_sizes.append(dimensions_to_sku_mapping.get(sku[:2], None))
            return box_sizes

        # Initiate target variable
        list_of_box_sizes = []

        if order.is_multi_order:
            for _ , product_dict in order.Shipment.items_dict.items():
                quantity = product_dict['quantity']
                #Multi orders skip this during Order() initiation, so must initiate this attribute here
                sku = product_dict['sku']
                order.Shipment.item_sku = sku

                box_sizes = get_box_sizes(sku, quantity)

                # Handles for when quantity of product > 1
                for box_size in box_sizes:
                    list_of_box_sizes.append(box_size)

        elif order.is_double_order:
            items_list = order.Shipment.items_list
            quantity = items_list[0]["quantity"]
            sku = items_list[0]["sku"]

            list_of_box_sizes = get_box_sizes(sku, quantity)

        else:
            # If neither criteria are true, then something is wrong
            raise RuntimeError("[X] Class attributes not set correctly for munti_dims_nuveau() !")

        return list_of_box_sizes

    # Initialize target variable
    list_of_box_sizes = list_box_sizes(order)


    # If any product is missing size info, False is used as a warning
    if None in list_of_box_sizes:
        return False
    
    # Calculate new sizes
    biggest_box = max(list_of_box_sizes, key=lambda x: x[0])
    total_weight = sum(index[-1] for index in list_of_box_sizes)
    total_height = sum(index[-2] for index in list_of_box_sizes)

    # Update Order Attributes
    length = biggest_box[0]
    width = biggest_box[1]
    height = total_height
    weight = total_weight

    # Update Order Attributes or Return Values
    order.Shipment.length = length
    order.Shipment.width = width
    order.Shipment.height = height
    order.Shipment.units = "ounces"
    # Need to set as dict to match aatribute value format of non-multi orders
    order.Shipment.weight = {'WeightUnits': 1, 'units': 'ounces', 'value': weight}

    return True




def set_dims_for_multi_order(order):
    '''
    Routes Order to the correct dims setting function depending on orders' SS_account
    '''
    if order.store_name == "nuveau":
        success = multi_dims_nuveau(order)
        return success
    elif order.store_name == "lentics":
        success = multi_dims_lentics(order)
        return success
    else:
        raise RuntimeError(f"[X] Multi-Order object has no dimension setting function for it's storename {order.store_name}")
    



def check_if_multi_order(order_object):

    # Handles scenario when 2 items of same and/or different skus are ordered
    if len(order_object.Shipment.items_list) > 1:
        order_object.is_multi_order = True
        tag_order(order_object, "Multi-Order")

    # Handles scenario when 2 or more of the same items are ordered (only same sku)
    item_quantity = order_object.Shipment.items_list[0]['quantity']
    if item_quantity > 1:
        order_object.is_double_order = True
        tag_order(order_object, "Double-Order")


def decode_response(dict_of_order_responses):
    """
        Decode the response from the ShipStation API and print the order details.

        Args:
            list_of_order_responses (list): The list of responses from the ShipStation API.
        Return:
            None
    """

    # Create a single UPS client session for all orders
    ups_client = UPSAPIClient()
    
    # Create a UPS service that uses this client
    ups_service = UPSService(ups_client)
    fedex_client_session = create_fedex_session()
    list_of_objects = []
    for store_name, response in dict_of_order_responses.items():
        for res in response[0]:
            if int(res.status_code) == 200:
                # Decode bytes to string
                response_str = res.content.decode('utf-8')

                # Parse string to Python object
                response_json = json.loads(response_str)

                if response_json["orders"] != []:
                    try:
                        for order in response_json["orders"]:
                            # Manually created orders
                            bad_stores = [165349, 203468, 325291, 433937]
                            if order['advancedOptions']['storeId'] in bad_stores:
                                continue

                            # Pop Creations Order
                            if order['advancedOptions']['warehouseId'] == 779978:
                                continue

                            # Issue with order in Shipstation
                            if order['orderTotal'] == 0.0:
                                continue


                            # Initiate orders into class
                            order_object = Order(order, store_name)
                            order_object.shipstation_client = response[1]
                            set_order_shipfrom_location(order_object)
                            order_object.ups_service = ups_service
                            order_object.fedex_client = fedex_client_session


                            # Skip orders shipping to Puerto Rico
                            if order_object.Customer.state.upper() == "PR":
                                continue

                            # Handles extra initiation logic when order is multi-order
                            check_if_multi_order(order_object)

                            list_of_objects.append(order_object)

                    except Exception as e:
                        print(f"[X] Failed to decode response. Error: {e}")
                        import pprint
                        pprint.pprint(order, indent=4)
                else:
                    # There are no orders for this store, continue to next Shipstation Account
                    print(f"[X] No orders with order_status of awaiting_shipment found this store: {store_name}")
                    continue
                
            else:
                print(f"[X] Failed to fetch orders. Status code: {response.status_code}")

    return list_of_objects




def set_order_shipfrom_location(order):
    '''
    Initializes shipfrom attributes for Order Object based on warehouseID
    '''
    michigan_warehouse_ids = [486100, 98792, 1097041, 505774, 857645, 1097039]
    stallion_warehouse_ids = [1097040, 665600]

    if order.order_warehouseId in michigan_warehouse_ids:
        order.Shipment.from_postal_code = "49022"
        order.Shipment.from_city = "Benton Harbor"
        order.Shipment.from_state = "MI"
        order.Shipment.from_country = "US"
        order.Shipment.from_address = "3329 Territorial Rd"
        order.Shipment.from_name = "Shipping Department"

    elif order.order_warehouseId in stallion_warehouse_ids:
        order.Shipment.from_postal_code = "46203"
        order.Shipment.from_city = "Indianapolis"
        order.Shipment.from_state = "IN"
        order.Shipment.from_country = "US"
        order.Shipment.from_address = "1435 E Naomi St"
        order.Shipment.from_name = "Shipping Department"

    else:
        info_statement = f"ID = {order.order_key}\n Warehouse = {order.order_warehouseId}\n SS_account = {order.store_name}"
        raise RuntimeError(f"No Ship From Location for Order -> {info_statement}")
    
    return None

def set_order_warehouse_location(order):

    product_Id = str(order.Shipment.productId)
    payload = { 
                    "aliases": None,
                    "productId": product_Id,
                    "sku": order.Shipment.item_sku,
                    "name": order.Shipment.item_name,
                    "price": order.Shipment.item_unit_price,
                    "defaultCost": None,
                    "length": order.Shipment.length,
                    "width": order.Shipment.width,
                    "height": order.Shipment.height,
                    "weightOz": order.Shipment.weight['value'],
                    "internalNotes": None,
                    "fulfillmentSku": None,
                    "active": True,
                    "productCategory": None,
                    "productType": None,
                    "warehouseLocation": 'CANVAS',
                    "defaultCarrierCode": None,
                    "defaultServiceCode": None,
                    "defaultPackageCode": None,
                    "defaultIntlCarrierCode": None,
                    "defaultIntlServiceCode": None,
                    "defaultIntlPackageCode": None,
                    "defaultConfirmation": None,
                    "defaultIntlConfirmation": None,
                    "customsDescription": None,
                    "customsValue": None,
                    "customsTariffNo": None,
                    "customsCountryCode": None,
                    "noCustoms": None,
                    "tags": None
                    }

    try:
        response = order.shipstation_client.put(endpoint=f"/products/{product_Id}", data=json.dumps(payload))
        response.raise_for_status()
        print(response.status_code)

    except Exception as e:
        print(f"Could not set Warhouse Location for order: {order.order_number}")
        print(e)
    return None


def is_po_box_delivery(order):
    """
    Checks if order is being delivered to a PO Box Address

    Args:
        order (object): The order object from Order()

    Return:
        (bool) True is order is delivering to PO Box: else False
    """
    customer_address = order.Customer.address1

    if "PO Box".upper() in customer_address.upper():
        return True
    return False




def list_packages(dict_of_shipstation_clients):
    '''
    Retrieves a list of Shipstation packageCodes for the specified carrier.
    Used for Development only

    Args: 
        (dict) : Keys = SS_stores, 
    '''
    print(dict_of_shipstation_clients)
    
    list_of_carriers = ["ups", "fedex", "ups_walleted", "stamps_com"]

    package_codes = {}
    for store_name, ss_client in dict_of_shipstation_clients.items():
        package_codes[store_name] = {}  # Initialize package_codes[store_name] here
        for carrierCode in list_of_carriers:
            try:
                response = ss_client.get(endpoint=f"/carriers/listpackages?carrierCode={carrierCode}")
                response.raise_for_status()  # Raise exception for non-200 status codes
                package_codes[store_name][carrierCode] = response.json()
            except Exception as e:
                print(f"Error fetching package codes for {store_name} and {carrierCode}: {e}")
    
    return package_codes


    

def set_payload_for_rates(order, carrier):
    '''
    Sets payload for each carrier and handles edge case conditions

    Args: 
        order (object): the order object
        carrier (str): The name of the carrier we are setting the payload for

    Return:
        payload (dict): Returns the correct payload for each condition
    '''
    payload = {
                    "carrierCode": carrier,
                    "serviceCode": None,
                    "packageCode": "package",
                    "fromPostalCode": order.Shipment.from_postal_code,
                    "fromcity": order.Shipment.from_city,
                    "fromState": order.Shipment.from_state.upper(),
                    "fromWarehouseId": order.order_warehouseId,
                    "toState": order.Customer.state.title(),
                    "toCountry": order.Customer.country if order.Customer.country in ["US", "CA"] else 'US',
                    "toPostalCode": order.Customer.postal_code,
                    "toCity": order.Customer.city.title(),
                    "weight": {
                        "value": order.Shipment.weight["value"],
                        "units": "ounces"
                    },
                    "dimensions": {
                        "units": "inches",
                        "length": int(order.Shipment.length),
                        "width": int(order.Shipment.width),
                        "height": int(order.Shipment.height)
                    },
                    "confirmation": order.confirmation,
                    "residential": order.Customer.is_residential
                }

    list_of_billy_bass_skus = ["M-BBass 2", "Billy Bass 02", "Gemmy03", "Gemmy01", 
                            "Gemmy Big Mouth Billy Bass 3", "Gemmy BBass3", "M-BBass", 
                            "Billy Bass Original", "L-BBass1", "L-BBass2", "L-BBass3"]


    item_sku = order.Shipment.item_sku
    # Billy Bass skus have unique height measurements for stamps_com
    if carrier == "stamps_com" and item_sku in list_of_billy_bass_skus:
            payload["dimensions"]["height"] = int(1)

    # Orders going to PR usually have country set to US, this causes error with shipping carrier APIs
    if order.Customer.state.upper() == "PR": # Used as state code
        order.Customer.country = "PR" # Two letter code for country happens to be the same

    return payload



def get_rates_for_all_carriers(order_object):
    """
        Fetch the list of carriers and services from the ShipStation API.

        Args:
            shipstation (ShipStation): The ShipStation connection object.
        Return:
            None
    """
    list_of_carriers = ["ups", "fedex", "ups_walleted", "stamps_com"]
    try: 
        for carrier in list_of_carriers:
            try: 
                payload = set_payload_for_rates(order_object, carrier)

            # Usually raised when dimensions info is not provided for the order object --> TypeError for int() cannot take NoneType
            except TypeError as e:
                print(e)
                tag_order(order_object, "No-Dims")
                return False

            try:
                response = order_object.shipstation_client.post(endpoint="/shipments/getrates", data=json.dumps(payload))
                # Usually raised when package details aren't valid for specific carrier
                if response.status_code == 500:
                    continue
                response.raise_for_status()  # Raises a HTTPError if the status is 4xx, 5xx

                # If the request is successful, no exception is raised
                response_json = response.json()
                for service in response_json:
                    order_object.mapping_services[service['serviceName']] = service['serviceCode']
                    total_cost = round(service['shipmentCost'] + service['otherCost'], 2)
                    service_tuple = (service['serviceName'], total_cost)

                    if carrier in order_object.rates:
                        order_object.rates[carrier].append(service_tuple)
                    else:
                        order_object.rates[carrier] = [service_tuple]

            
            except requests.exceptions.RequestException as e:
                print(f"An error occurred: {e}")
                return False
        
        # If rates obtained for all carriers
        return True
    
    except Exception as e:
        print(e)
        return False
    



def set_payload_for_update_order(order_object):

    # Handling an Edge case for certain product
    if order_object.winning_rate["carrierCode"] == "stamps_com":
        list_of_billy_bass_skus = ["M-BBass 2", "Billy Bass 02", "Gemmy03", "Gemmy01", "Gemmy Big Mouth Billy Bass 3", 
                                "Gemmy BBass3", "M-BBass", "Billy Bass Original", "L-BBass1", "L-BBass2", "L-BBass3"]
        if order_object.Shipment.item_sku in list_of_billy_bass_skus:
            order_object.Shipment.height = int(1)
            order_object.package_code = 'package'



    shipping_provider_id_mapping = {
        "nuveau" : {
            "stamps_com"    : 139051,
            "ups"           : 659748,
            "fedex"         : 203639,
            "ups_walleted"  : 139292
        },
        "lentics" : {
            "stamps_com"    : 89042,
            "ups"           : 1227452,
            "fedex"         : 465570,
            "ups_walleted"  : 465647
        }
    }

    # Update the Shipping Account Billing info based on the winning carrier
    winning_carrier_code = order_object.winning_rate["carrierCode"]
    shipping_provider_Id = shipping_provider_id_mapping[order_object.store_name][winning_carrier_code]
    order_object.advanced_options['billToParty'] = 'my_other_account'
    order_object.advanced_options['billToMyOtherAccount'] = shipping_provider_Id

    # Write SmartPost delivery date to field
    order_object.advanced_options['customField2'] = order_object.Shipment.smart_post_date


    if not order_object.order_warehouseId:
        raise Exception("Order does not have a warehouse ID / ship from location")

    payload = {
        "orderNumber": order_object.order_number,
        "orderKey": order_object.order_key,
        "orderDate": order_object.order_date,
        "paymentDate": order_object.payment_date,
        "shipByDate": order_object.shipByDate,
        "orderStatus": order_object.order_status,
        "customerId": order_object.Customer.id,
        "customerUsername": order_object.Customer.username,
        "customerEmail": order_object.Customer.email,
        "billTo": order_object.Customer.billToDict,
        "shipTo": order_object.Customer.shipToDict,
        "items": order_object.Shipment.items_list,
        "amountPaid": order_object.amount_paid,
        "taxAmount": order_object.tax_amount,
        "shippingAmount": order_object.Shipment.shipping_amount,
        "customerNotes": order_object.Customer.notes,
        "internalNotes": order_object.Customer.internal_notes,
        "gift": order_object.is_gift,
        "giftMessage": order_object.gift_message,
        "paymentMethod": order_object.payment_method,
        "requestedShippingService": order_object.winning_rate["serviceCode"],
        "carrierCode": order_object.winning_rate["carrierCode"],
        "serviceCode": order_object.mapping_services[order_object.winning_rate["serviceCode"]],
        "packageCode": order_object.package_code,
        "confirmation": order_object.confirmation,
        "shipDate": order_object.ship_date,
        "weight": order_object.Shipment.weight,
        "dimensions": {
            "length": order_object.Shipment.length, 
            "width": order_object.Shipment.width,
            "height": order_object.Shipment.height,
            "units": "inches"
            },
        "insuranceOptions": order_object.Shipment.insurance_options,
        "internationalOptions": order_object.Shipment.internal_options,
        "advancedOptions": order_object.advanced_options,
        "tagIds": order_object.tag_ids,
    }


    return payload




def create_or_update_order(order_object: Order) -> bool:  
    """
    Create or update an order in ShipStation.

    Args:
        order_object (Order): The Order object containing all necessary data.
    Return:
        bool: True if the request is successful, False otherwise.
    """
    payload = set_payload_for_update_order(order_object)

    try:
        # URL & Headers are included in the shipstation_client Session
        response = order_object.shipstation_client.post(endpoint="/orders/createorder", data=json.dumps(payload))
        response.raise_for_status()  # Raises an exception for HTTP error codes
        # Optionally, process the response or return True to indicate success
        #print("Order created or updated successfully:", response.json())
        return True
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return False




def hold_order(order):
    """
    Determines whether an order should be placed on hold and proceeds to move the order to the "on hold" status if the specified criteria are met.
    Adjust function as needed to detmerin hold criteria
    """

    hold_order = False
    hold_list = ["F3", "T3", "O4", "F2BFpM"]

    for string in hold_list:
        if order.Shipment.item_sku.startswith(string):
            hold_order = True

    if hold_order:
        payload = {
            'orderId'       : int(order.order_id),
            'holdUntilDate' : "2024-05-03"
        }

        try:
            # URL & Headers are included in the shipstation_client Session
            response = order.shipstation_client.post(endpoint="/orders/holduntil", data=json.dumps(payload))
            response.raise_for_status()  # Raises an exception for HTTP error codes

            return True
        except requests.exceptions.RequestException as e:
            print(f"[X] Error, could not 'Hold Order' on shipstation: {e}")
    
    else:
        return False



def get_champion_rate(order, ups_best: tuple = None, usps_best: tuple = None, fedex_best: tuple = None):
    """
    Finds the overall best shipping rate among multiple carriers based on the winning rates.

    Parameters:
    - order (Order object): An object representing the order details.
    - ups_best (tuple or None): A tuple containing UPS's best rate information or None if UPS rate is not available.
    - usps_best (tuple or None): A tuple containing USPS's best rate information or None if USPS rate is not available.
    - fedex_best (tuple or None): A tuple containing FedEx's best rate information or None if FedEx rate is not available.

    Returns:
    - None: The function updates the order object's winning_rate attribute with the champion rate.

    This function takes the winning rates of all the carriers and compares them against each other to find the overall best rate.
    It considers the warehouse ID of the order to determine which carriers to include in the comparison.
    If the order is not from Stallion's warehouse, it includes rates from UPS, USPS, and FedEx (if available).
    If the order is from Stallion's warehouse, it includes rates from UPS and USPS only (FedEx rate is excluded).
    The function then selects the champion rate based on the lowest price among the eligible rates and updates the order object with this rate.
    """
    stallion_warehouse_ids = [665600, 1097040]

    if order.order_warehouseId not in stallion_warehouse_ids:
        list_of_rates = [rate for rate in [ups_best, usps_best, fedex_best] if rate is not None]
    else: # Order ships from Stallion Warehouse & they do not ship Fedex
        list_of_rates = [rate for rate in [ups_best, usps_best] if rate is not None]

    champion_rate = min(list_of_rates, key=lambda x: x["price"])
    order.winning_rate = champion_rate # Example:  {'carrierCode': 'ups', 'serviceCode': 'UPS® Ground', 'price': 12.62}

    return None



if __name__ == "__main__":
    print("[X] This file is not meant to be executed directly. Check for the main.py file.")
    quit(1)