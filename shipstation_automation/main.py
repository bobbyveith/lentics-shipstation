import functions
import ups_api
from usps_api import get_usps_best_rate
from fedex_api import get_fedex_best_rate
from utils.utils import list_account_tags
import customer_log as cl


__author__ = ["Rafael Malcervelli", "Bobby Veith"]
__company__ = "Lentics, Inc."

def initial_setup():
    # Print the banner
    functions.print_banner()

    print("======= Starting Initial Setup =======")
    # Connect to the ShipStation API
    dict_of_ss_clients = functions.connect_to_api()
    print("[+] Connected to the ShipStation API!\n\n")

    # # Used for debugging only
    # functions.fetch_order(dict_of_ss_clients['lentics'], "111-3451647-5934633")
    # raise RuntimeError("Quitting...")

    print("[+] Refreshing Stores & Fetching orders on all SS_Accounts...\n\n")
    # Fetch orders from the ShipStation API for both accounts
    dict_of_response_orders = functions.fetch_orders_with_retry(dict_of_ss_clients)
    print("[+] Fetched orders from the ShipStation API!\n")


    print("[+] Instantiating Orders into Class Objects...\n")
    # Get list of json objects, 1 object for each order
    list_of_order_objects = functions.decode_response(dict_of_response_orders)

    print("======= Finished Initial Setup =======")

    return list_of_order_objects

# =================== GLOBAL VARIABLES =========================
# For orders that failed the process on their first attemp
retry_list = []

# =================== CORE PROGRAM FUNCTIONS =============================

def initialize_order(order):
    print(f"[+] Starting Initialization for order: {order.order_key} | {order.store_name}")
    print("\n")
    # Multi Orders have unique conditions for setting the Dimensions
    if order.is_multi_order or order.is_double_order:
        print("This is multi order") 
        successful = functions.set_dims_for_multi_order(order)
        if not successful:
            functions.tag_order(order, "No-Dims")
            functions.print_yellow("[!] Warning: No dims for multi order products, skipping..\n")
            return False

    if not order.deliver_by_date:
        failure = (order, "No-DeliveryDate")
        retry_list.append(failure)
        return False
    
    # Get rates for all carriers from ShipStation
    print("\n[+] Getting Shipstation rates for all carriers...")
    # Function fails if not dimenstions for order, function tags order with "No_Dims"
    if not functions.get_rates_for_all_carriers(order):
        functions.print_yellow("[!] Warning: Could not get carrier rates for order, skipping\n")
        failure = (order, "No SS Carrier Rates") # Can be added in addition to "No-Dims Tag"
        retry_list.append(failure)
        return False
    
    return True



def set_winning_rate(order):
            
            print("[+] Getting API Rates from all carriers...")
            # When delivery to a PO Box, must use USPS shipping only
            if functions.is_po_box_delivery(order):
                order.winning_rate =  get_usps_best_rate(order)
                return True

            # Get winning UPS rate
            ups_best = ups_api.get_ups_best_rate(order)
            if ups_best is False:
                failure = (order, "No UPS Rate")
                retry_list.append(failure)
                return False
            print(f"[+] UPS best rate: {ups_best}")


            # Get winning USPS rate
            usps_best = get_usps_best_rate(order)
            if usps_best is False:
                failure = (order, "No USPS Rate")
                retry_list.append(failure)
                return False
            print(f"[+] USPS best rate: {usps_best}")
            

            # Get winning FedEx rate
            fedex_best = get_fedex_best_rate(order)
            if fedex_best is False:
                failure = (order, "No Fedex Rate")
                retry_list.append(failure)
                return False
            print(f"[+] FedEx best rate: {fedex_best}")


            # Compare all the winning rates against each other and update winniner to order.winning_rate
            functions.get_champion_rate(order, ups_best=ups_best, fedex_best=fedex_best, usps_best=usps_best)
            print(f"[+] Champion rate: {order.winning_rate}")
            return True



def set_shipping_for_order(order):
    print("\n---------- Setting shipping for orders ----------")
        # Set the shipping for the order
    print("\n[+] Setting shipping for order: ", order.order_key)
    success = functions.create_or_update_order(order)
    if success:
        functions.tag_order(order, "Ready")
        functions.print_green("[+] Successfully Updated Carrier on Shipstation")
    else:
        functions.print_red(f"[X] Order shipping update not successful {order.order_key}")
        failure = (order, "Shipping not set")
        retry_list.append(failure)

    print("------------next order---------------------\n\n")
    return True



def main():
    global retry_list
    retry_list = []

    def full_program(order):
        if not initialize_order(order):
            return False
        
        if not set_winning_rate(order):
            return False
        
        if not set_shipping_for_order(order):
            return False
        return True
    
    def half_program(order):   
        if not set_winning_rate(order):
            return False
        
        if not set_shipping_for_order(order):
            return False
        return True

# =======   START OF MAIN LOOP   ========
    # Set up the progam and get the list of orders and csv for customer logging
    list_of_order_objects = initial_setup()

    # List of dictionaries containing customer data to be logged
    customer_data_log = []

    for order in list_of_order_objects:
        if order:
            # Small requirement to PUT certain info for criteria
            if not order.is_multi_order and order.Shipment.item_sku.startswith("P1xxc"):
                functions.set_order_warehouse_location(order)
            # If issue with any order, retry_list.append(order, reason) and continue to next order
            if not full_program(order):
                continue
            
            # Since the order was successful, log the customer data
            customer_data = cl.parse_customer_data(order)
            customer_data_log.append(customer_data)      

    # Orders added to retry_list within the core functions
    if retry_list: # Global var
        reattempt_list = retry_list.copy()
        retry_list = []
        # If orders fail on second attempt, tag them and give up
        for order, reason in reattempt_list: # list of tuples
            functions.print_yellow(f"[!] Retrying Order: {order.order_key} because {reason}")
            if reason == "No-DeliveryDate" or reason == "No SS Carrier Rates":
                successful = full_program(order)
                if not successful:
                    if functions.tag_order(order, reason):
                        functions.print_yellow("[!] Order tagged..")
                else:
                    # Process was successful, add Customer data to the log
                    customer_data = cl.parse_customer_data(order)
                    customer_data_log.append(customer_data)   
            
            if reason == "No UPS Rate" or reason == "No USPS Rate" or reason == "No Fedex Rate":
                successful = half_program(order)
                if not successful:
                    if functions.tag_order(order, reason):
                        functions.print_yellow("[!] Order tagged..")
                else:
                    # Process was successful, add Customer data to the log
                    customer_data = cl.parse_customer_data(order)
                    customer_data_log.append(customer_data)  
            
            if reason == "Shipping not set":
                successful = set_shipping_for_order(order)
                if not successful:
                    if functions.tag_order(order, reason):
                        functions.print_yellow("[!] Order tagged..")
                else:
                    # Process was successful, add Customer data to the log
                    customer_data = cl.parse_customer_data(order)
                    customer_data_log.append(customer_data)  

    # Log customer data for all successful order processes
    print("Logging Customer info...")
    success = cl.log_customer_data(customer_data_log)
    if not success:
        functions.print_yellow('[!] Warning: Customer Data not Logged!')

if __name__ == "__main__":
    try:
        main()

    except Exception as e:
        print(e)
        quit(1)