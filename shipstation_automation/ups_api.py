import requests
from urllib.parse import quote_plus
import base64
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time
import os
import copy

def initiate_oauth_flow(session):
    load_dotenv()
    # Constants for UPS OAuth flow
    CLIENT_ID_UPS = os.getenv('API_KEY_LENTICS_UPS')
    CLIENT_SECRET_UPS = os.getenv('API_SECRET_LENTICS_UPS')
    auth_value = f"{quote_plus(CLIENT_ID_UPS)}:{quote_plus(CLIENT_SECRET_UPS)}"
    encoded_credentials = base64.b64encode(auth_value.encode('utf-8')).decode('utf-8')

    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': '*/*',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Origin': 'https://developer.ups.com',
        'User-Agent': 'Python requests library'  # Changed from Safari for authenticity
    }

    data = {
        'grant_type': 'client_credentials'  # Common grant type for client authentication
    }

    max_retries = 3  # Maximum number of retries
    retry_count = 0

    while retry_count < max_retries:
        response = session.post('https://wwwcie.ups.com/security/v1/oauth/token', headers=headers, data=data)

        # Check if the request was successful
        if response.status_code == 200:
            print("[+] UPS OAuth token request successful!")
            # Extract and print the token information
            token_info = response.json()
            return token_info.get('access_token')
        else:
            print(f"[X] Token request failed: {response.text}")
            retry_count += 1
            print(f"Retrying... ({retry_count}/{max_retries})")
            time.sleep(1)  # Wait for 1 second before retrying

    print("[X] Failed to get UPS OAuth token after retries.")
    return None



def create_ups_session():
    
    session = requests.Session()

    access_token = initiate_oauth_flow(session)

    if access_token:
        header = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'Authorization': f'Bearer {access_token}',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Host': 'wwwcie.ups.com',
            'Origin': 'https://developer.ups.com',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'transactionSrc': 'testing', # Default:  testing / Identifies the clients/source application that is calling. Length 512
            'transId': '12345612345612345612345612345612', #An identifier unique to the request. Length 32
            'User-Agent': 'Python requests library',
        }

        session.headers.update(header)

        return session
    
    else:
        print(f"[X] Failed to get UPS Access Token")
        return None
    


def get_delivery_times(order):
    # API DOCS --> https://developer.ups.com/api/reference?loc=en_US#tag/TimeInTransit_other
    # The URL for the API request
    url = 'https://wwwcie.ups.com/api/shipments/v1/transittimes'

    # Headers are included in the order.ups_client Session

    # The body of the request
    payload = {
        "originCountryCode": "US", # REQUIRED -> The country code of the origin shipment. Valid Values: Must conform to the ISO-defined, two-letter country or territory codes. Refer to Country or Territory Codes in the Appendix above for valid values.
        "originStateProvince": "", # The shipment origin state or province. For U.S. addresses, the value must be a valid 2-character value (per U.S. Mail standards) For non-U.S. addresses the full State or Province name should be provided.
        "originCityName": order.Shipment.from_city, # The shipment origin city. Required for International requests for those countries that do not utilize postal codes.
        "originTownName": "", # The shipment origin town. Town is a subdivision of city.
        "originPostalCode": order.Shipment.from_postal_code, # Required for Domestic requests. The shipment origin postal code. Either the 5, or 9-digit US zip codes must be used for U.S. addresses. For non-U.S. addresses, this is recommended for all countries that utilize postal codes.
        "destinationCountryCode": order.Customer.country if order.Customer.country in ["US", "CA"] else 'US', # The country code of the destination. Valid values: Must conform to ISO-defined country codes.
        "destinationStateProvince": order.Customer.state, # The shipment destination state or province. For U.S. addresses, the value must be a valid 2-character value (per U.S. Mail standards). For non-U.S. addresses the full State or Province name should be provided.
        "destinationCityName": order.Customer.city, # The shipment destination city. Required for International Requests for those countries that do not utilize postal codes.
        "destinationTownName": "", # The shipment destination town. Town is a subdivision of city.
        "destinationPostalCode": order.Customer.postal_code.replace("-", ""), # The shipment destination postal code. Required for Domestic requests. Either 5, or 9-digit U.S. zip codes must be used for U.S. addresses. For non-U.S. addresses, this is recommended for all countries that utilize postal codes.
        "weight": str(0.028 * order.Shipment.weight["value"]) if order.Shipment.weight["units"] == "ounces" else "5", # The weight of the shipment. Required for International requests. Note: If decimal values are used, valid values will be rounded to the tenths. Note: Maximum value is 70 kilograms or 150 pounds.
        "weightUnitOfMeasure": "KGS", # Required for International requests and when weight value is provided. Valid Values: "LBS", "KGS".
        "shipmentContentsValue": "", # The monetary value of shipment contents. Required when origin country does not equal destination country and BillType is 03 (non-documented) or 04 (WWEF). Required when origin country does not equal destination country, and destination country = CA, and BillType = 02 (document).vNote: If decimal values are used, valid values will be rounded to the tenths.
        "shipmentContentsCurrencyCode": "USD", # The unit of currency used for values. Required if ShipmentContentsValue is populated. Valid value: must conform to ISO standards.
        "billType": "03", # Required for International Requests. Valid values: "02","03","04" 02 - Document 03 - Non Document 04 - WWEF (Pallet)
        "shipDate": order.ship_date, # The date the shipment is tendered to UPS for shipping (can be dropped off at UPS or picked up by UPS). Allowed range is up to 60 days in future and 35 days in past. This date may or may not be the UPS business date. Format is YYYY-MM-DD. YYYY = 4 digit year; MM = 2 digit month, valid values 01-12; DD = 2 digit day of month, valid values 01-31 If no value is provided, defaults to current system date.
        "shipTime": "", # The time the shipment is tendered to UPS for shipping (can be dropped off at UPS or picked up by UPS). Format is HH:MM:SS. Defaults to current time if not provided.
        "residentialIndicator": (lambda condition: "01" if condition else "02")(order.Customer.is_residential), # Indicates if address is residential or commercial. Required for Domestic requests. Valid values: "01", "02" -> 01 = Residential 02 = Commercial. Defaults to commercial for International Requests.
        "avvFlag": True, # Used to bypass address validation when the address has already been validated by the calling application. Valid values: true, false. Defaults to true Note: not to be exposed to external customers.
        "numberOfPackages": "1",
        'returnUnfilterdServices' : False # Sets the number of packages in shipment. Default value is 1.
    }

    try:
        # Making the POST request
        response = order.ups_client.post(url, json=payload)

        # Check if the request was successful
        if response.status_code == 200:
            # Convert the response to JSON format
            data = response.json()
            return data
        
        else:
            print("[X] Failed to get delivery times for UPS:", response.status_code, response.text)
            print(f"{payload['destinationCountryCode']}")
    except Exception as e:
        print("[X] Failed to get delivery times exception:", e)
        print(order)




def add_ground_saver_to_list(service_list): 
    """
    Determines if Ground Saver is applicable for the order and adds it to the service list based on UPS Ground service object.

    Parameters:
    - service_list (list of dicts): A list of service objects, each represented as a dictionary.

    Returns:
    - list of dicts: Updated service list with Ground Saver service added if applicable.

    This function checks each service in the service list. If a service corresponds to 'UPS Ground' and is not scheduled for delivery on Friday or Saturday (weekend), 
    it adds a Ground Saver service to the list with modified attributes. The modified attributes include service level ('GNS' for Ground Saver), 
    service description ('UPS Saver'), incremented business transit days, and adjusted delivery date and day of the week based on adding one day to the original delivery date.

    Note: The input service_list is modified in-place, and the updated list is returned.
    """
    def add_days(delivery_date, number_of_days):
        '''
        Determines the next day and the next day of the week abbreviation

        Parameters:
        - delivery_date (datetime object): Date representing the delivery date for the respective service
        - number of days (int): The number of days to be added to the current delivery date

        Returns:
        next_day (datetime object): The new delivery date after the number_of_days has been added
        day_of_week_abbr (str): The new delivery date represented as an abbrviation -> 'TUE'
        '''

        next_day = delivery_date + timedelta(days=number_of_days)  # Add one day
        day_of_week_abbr = next_day.strftime('%a')

        return next_day, day_of_week_abbr.upper()


    ground_saver = {}
    for service in service_list:
        if service['serviceLevelDescription'] == 'UPS Ground':
            delivery_day = service['deliveryDayOfWeek']
            # Set Ground Saver equal to UPS Ground, and then make the changes we need
            ground_saver = copy.deepcopy(service)
            ground_saver['serviceLevel'] = 'GNS'
            ground_saver['serviceLevelDescription'] = 'UPS Ground Saver'
            if delivery_day != "SAT": # For Ground Saver to be valid, it cannot arrive on sunday
                ground_saver['businessTransitDays'] = service['businessTransitDays'] + 1
                next_day, next_day_of_week = add_days(service['deliveryDate'], 1)
                ground_saver['deliveryDate'] = next_day
                ground_saver['deliveryDayOfWeek'] = next_day_of_week

            elif delivery_day == "SAT": # Skip sunday and calculate for Monday delivery
                ground_saver['businessTransitDays'] = service['businessTransitDays'] + 2
                next_day, next_day_of_week = add_days(service['deliveryDate'], 2)
                ground_saver['deliveryDate'] = next_day
                ground_saver['deliveryDayOfWeek'] = next_day_of_week

        else: 
            ground_saver = None

    if ground_saver != None:
        service_list.append(ground_saver)

    return service_list


def get_valid_services(order, services):
    """
    Filter and return a list of services that will arrive on or before the latest delivery date.

    This function takes an order and a list of services, then checks each service's delivery date
    to determine if it is on or before the order's deliver-by date. Only services that meet this 
    criterion are included in the returned list.

    Args:
        order (object): An object representing the order, which has an attribute 
                        `deliver_by_date` containing the latest delivery date as a string.
                        The date format is "%m/%d/%Y %H:%M:%S".
        services (dict): A dictionary containing the services under the key "emsResponse".
                        Each service has a 'deliveryDate' key with the date as a string 
                        in the format "%Y-%m-%d".

    Returns:
        list: A list of services that will arrive on or before the latest delivery date.
    """
    valid_services = []
    for service in services["emsResponse"]["services"]:
        # Convert the deliveryDate to a datetime object
        delivery_date = datetime.strptime(service['deliveryDate'], '%Y-%m-%d')
        # Redefine this value to datetime object for later use and comparison
        service['deliveryDate'] = delivery_date

        # Convert the string to a datetime object
        date_format = "%m/%d/%Y %H:%M:%S"  # Old Format = "%Y-%m-%dT%H:%M:%SZ"
        latest_time_datetime = datetime.strptime(order.deliver_by_date, date_format)
        # Check if the delivery date is within the desired deadline.
        if delivery_date <= latest_time_datetime:
            valid_services.append(service)
    return valid_services



def get_valid_rates(order, valid_services):
    """
    Calculate and return a list of valid rates for given services based on ShipStation data.

    This function takes an order and a list of valid services, then checks each service's rate 
    from the order.rate data (Shipstation Data). It handles specific cases for UPS Ground to account for a naming 
    anomaly and applies an upcharge for certain carrier accounts.

    Args:
        order (object): An object representing the order, which must have an attribute `rates` 
                        containing the price rate information for different carriers.
        valid_services (list): A list of valid services, each service being a dictionary with keys 
                            'serviceLevelDescription' and 'deliveryDate'.

    Returns:
        list: A list of dictionaries containing the carrier, service code, price, and delivery date 
            for services that have valid rates.
            Ex: {'carrier: 'ups_walleted', 'service': 'UPS® Ground', 'rate': 6.72, 'deliveryDate': *datetime_object*}
    """
    valid_rates = []
    for service in valid_services:
        for carrier in ["ups", "ups_walleted"]:
            # If it's UPS Ground, handle spelling mismatch
            if service['serviceLevelDescription'] == "UPS Ground": 
                rate = dict(order.rates[carrier]).get('UPS® Ground') # Handling spelling anamole with the name of this one service not having the little 'R' symbol
                if rate != None and carrier == 'ups_walleted':
                    valid_rates.append({'carrierCode' : carrier, 'serviceCode': 'UPS® Ground', 'price': rate, 'deliveryDate':service['deliveryDate']})

                elif rate != None and carrier == 'ups':
                    valid_rates.append({'carrierCode' : carrier, 'serviceCode': 'UPS® Ground', 'price': round(rate * 1.03, 2), 'deliveryDate':service['deliveryDate']}) # Add 3% upcharge for 'ups' account

            # If it's any other service
            else:
                rate = dict(order.rates[carrier]).get(service['serviceLevelDescription'])
                if rate != None and carrier == 'ups_walleted':
                    valid_rates.append({'carrierCode': carrier, 'serviceCode': service['serviceLevelDescription'], 'price': rate, 'deliveryDate':service['deliveryDate']})

                elif rate != None and carrier == 'ups':
                    valid_rates.append({'carrierCode': carrier, 'serviceCode': service['serviceLevelDescription'], 'price':  round(rate * 1.03, 2), 'deliveryDate':service['deliveryDate']}) # Add 3% upcharge for 'ups' account

    return valid_rates # EX: {'carrier: 'ups_walleted', 'service': 'UPS® Ground', 'rate': 6.72, 'deliveryDate': *datetime_object*}



def filter_best_option(sorted_options):
    """
    Filters and determines the best shipping option based on delivery date, price, and service code.

    This function processes a sorted list of shipping options to find the best option 
    according to specified business logic. It includes additional logic to handle 
    "UPS Ground Saver" service code by removing it if other options are less than $0.30 
    more expensive and return earlier.

    Parameters:
    sorted_options (list): A list of dictionaries representing the shipping options,
                        sorted by price in ascending order. Each dictionary must
                        contain the keys 'serviceCode', 'price', and 'deliveryDate', 
                        where 'deliveryDate' is a datetime object.

    Returns:
    dict: The best shipping option based on the specified business logic.

    Helper Functions:
    find_best_option(sorted_options): Finds the best shipping option based on delivery date and price.
    
    remove_unviable_ground_saver(sorted_options): Filters out UPS Ground Saver options that do not 
                                                meet the specified criteria.
    """

    # Helper function to determine if Ground Saver is viable
    def remove_unviable_ground_saver(sorted_options):
        """
        Filters out UPS Ground Saver options that do not meet the specified criteria.

        This function iterates through a sorted list of shipping options and removes 
        any UPS Ground Saver options if there are other non-Ground Saver options that 
        are less than $0.30 more expensive. It returns the filtered list of options.

        Parameters:
        sorted_options (list): A list of dictionaries representing the shipping options,
                            sorted by price in ascending order. Each dictionary must
                            contain the keys 'serviceCode' and 'price'.

        Returns:
        list: A filtered list of shipping options with unviable UPS Ground Saver options removed.
        """
        winning_index = 0
        #print(sorted_options)
        # If Ground Saver isn't saving at least $0.30 than don't use it
        for index, option in enumerate(sorted_options):
            if option['serviceCode'] == "UPS Ground Saver":
                # Continue checking the next elements as long as the conditions are met
                if sorted_options[index + 1]['price'] - cheapest_option['price'] < 0.30:
                    index += 1
                    winning_index = index  # Set the next index after the current one

        if winning_index:  # Check if a winning index was found
            index = winning_index
            sorted_options = sorted_options[index:]

        return sorted_options
    

    cheapest_option = sorted_options[0]
    better_options = [option for option in sorted_options if 0 < option['price'] - cheapest_option['price'] < 0.35]
    #print(f"better_options = {better_options}")
    
    if better_options and cheapest_option['serviceCode'] == "UPS Ground Saver":
        filtered_options = remove_unviable_ground_saver(better_options)
        best_option = min(filtered_options, key=lambda x: x['deliveryDate'])

    elif better_options:
        best_option = min(better_options, key=lambda x: x['deliveryDate'])
    else:
        best_option = cheapest_option

    return best_option




def get_ups_best_rate(order: object):
    """
    Determine and return the best UPS shipping rate for a given order.

    This function serves as the entry point for the main module, executing all necessary functions
    within its module to return the desired result. It calculates the best shipping rate based on 
    delivery times, customer type (residential or commercial), and pricing data from the ShipStation API.

    Args:
        order (object): An object representing the order, which must include:
                        - `Customer.is_residential` (bool): Whether the customer is residential.
                        - `deliver_by_date` (str): The latest delivery date for the order.
                        - `rates` (dict): The rate information for different carriers.

    Returns:
        dict: A dictionary containing the best UPS shipping rate with keys 'carrierCode', 
            'serviceCode', and 'price'. Example: {'carrierCode': 'ups', 'serviceCode': 'UPS® Ground', 'price': 12.62}
            If no valid rates are found, returns None.
    """

    services = get_delivery_times(order)

    # A list of all services that will arrive on or before the latest delivery date
    valid_services = get_valid_services(order, services)

    # Ground Saver delivery estimates not provided by UPS api, add for residential orders
    if order.Customer.is_residential:
        valid_services = add_ground_saver_to_list(valid_services)


    # Ensure that rates exists for each of the UPS accounts
    list_of_carriers = [carrier for carrier in order.rates.keys() if carrier in ["ups", "ups_walleted"]]
    if not list_of_carriers:
        return None

    # A list of dictionaries representing the services AND thier true price rates based on Shipstation API Data
    valid_rates = get_valid_rates(order, valid_services)
    for service in valid_rates:
        if service["serviceCode"] == "UPS Ground Saver":
            print(service)

    sorted_options = sorted(valid_rates, key=lambda x: x['price']) if valid_rates else None
    # Apply desired business logic
    best_option = filter_best_option(sorted_options)

    if best_option:
        # No longer needed, remove to keep data clean
        best_option.pop('deliveryDate')
        ups_best_rate = best_option
    return ups_best_rate



if __name__ == '__main__':
    try:
        print("[X] This file is not meant to be executed directly. Check for the main.py file.")
    except Exception as e:
        print('Error:', e)

