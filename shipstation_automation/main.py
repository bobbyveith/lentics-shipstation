import shipstation_automation.functions as functions
#import shipstation_automation.ups_api as ups_api
from shipstation_automation.usps_api import get_usps_best_rate
from shipstation_automation.fedex_api import get_fedex_best_rate
from shipstation_automation.utils.utils import list_account_tags
import shipstation_automation.customer_log as cl
from shipstation_automation.utils.output_manager import OutputManager

__author__ = ["Bobby Veith"]
__company__ = "Lentics, Inc."


# Set up logging and output manager for this module
output = OutputManager(__name__)


def initial_setup():
    
    output.print_section_header("======= Starting Initial Setup =======")
    # Connect to the ShipStation API
    dict_of_ss_clients = functions.connect_to_api()
    output.print_section_item("[+] Connected to the ShipStation API!", color="green")

    # # Used for debugging only
    # functions.fetch_order(dict_of_ss_clients['lentics'], "111-3451647-5934633")
    # raise SystemExit("End Test")

    output.print_section_item("[+] Refreshing Stores & Fetching orders on all SS_Accounts...", color="green")
    # Fetch orders from the ShipStation API for both accounts
    dict_of_response_orders = functions.fetch_orders_with_retry(dict_of_ss_clients)
    output.print_section_item("[+] Fetched orders from the ShipStation API!", color="green")

    output.print_section_item(f"[+] Dict of response orders: {dict_of_response_orders}", color="green")
    raise SystemExit("End Test")
    # Get the first key from the dictionary
    first_key = next(iter(dict_of_response_orders))
    output.print_section_item(f"[+] First store: {first_key}, First response: {dict_of_response_orders[first_key][0]}", color="green")
    raise SystemExit("End Test")


    output.print_section_item("[+] Instantiating Orders into Class Objects...", color="green")
    # Get list of json objects, 1 object for each order
    list_of_order_objects = functions.decode_response(dict_of_response_orders)

    output.print_section_header("======= Finished Initial Setup =======")

    return list_of_order_objects

# =================== GLOBAL VARIABLES =========================
# For orders that failed the process on their first attemp
retry_list = []

# =================== CORE PROGRAM FUNCTIONS =============================

def initialize_order(order):
    output.print_section_item(f"[+] Starting Initialization for order: {order.order_key} | {order.store_name}", color="green")
    output.print_section_item("\n")
    # Multi Orders have unique conditions for setting the Dimensions
    if order.is_multi_order or order.is_double_order:
        output.print_section_item("This is multi order")
        successful = functions.set_dims_for_multi_order(order)
        if not successful:
            functions.tag_order(order, "No-Dims")
            output.print_section_item("[!] Warning: No dims for multi order products, skipping..\n", log_level="warning", color="yellow")
            return False

    if not order.deliver_by_date:
        failure = (order, "No-DeliveryDate")
        retry_list.append(failure)
        return False
    
    # Get rates for all carriers from ShipStation
    output.print_section_item("\n[+] Getting Shipstation rates for all carriers...", color="green")
    # Function fails if not dimenstions for order, function tags order with "No_Dims"
    if not functions.get_rates_for_all_carriers(order):
        output.print_section_item("[!] Warning: Could not get carrier rates for order, skipping\n", log_level="warning", color="yellow")
        failure = (order, "No SS Carrier Rates") # Can be added in addition to "No-Dims Tag"
        retry_list.append(failure)
        return False
    
    return True



def set_winning_rate(order):
            
    # output.print_section_item("[+] Getting API Rates from all carriers...", color="green")
    # # When delivery to a PO Box, must use USPS shipping only
    # if functions.is_po_box_delivery(order):
    #     order.winning_rate =  get_usps_best_rate(order)
    #     return True

    output.print_section_item(f"[+] Order: {order.order_number}", color="green")

    # Get winning UPS rate
    ups_best = order.ups_service.get_ups_best_rate(order)
    output.print_section_item(f"[+] UPS best rate: {ups_best}", color="green")
    raise SystemExit("End Test")
    if ups_best is False:
        failure = (order, "No UPS Rate")
        retry_list.append(failure)
        return False
    output.print_section_item(f"[+] UPS best rate: {ups_best}", color="green")


    # Get winning USPS rate
    usps_best = get_usps_best_rate(order)
    if usps_best is False:
        failure = (order, "No USPS Rate")
        retry_list.append(failure)
        return False
    output.print_section_item(f"[+] USPS best rate: {usps_best}", color="green")
    

    # Get winning FedEx rate
    fedex_best = get_fedex_best_rate(order)
    if fedex_best is False:
        failure = (order, "No Fedex Rate")
        retry_list.append(failure)
        return False
    output.print_section_item(f"[+] FedEx best rate: {fedex_best}", color="green")


    # Compare all the winning rates against each other and update winniner to order.winning_rate
    functions.get_champion_rate(order, ups_best=ups_best, fedex_best=fedex_best, usps_best=usps_best)
    output.print_section_item(f"[+] Champion rate: {order.winning_rate}", color="green")
    return True



def set_shipping_for_order(order):
    output.print_section_header("\n---------- Setting shipping for orders ----------")
    # Set the shipping for the order
    output.print_section_item(f"\n[+] Setting shipping for order: {order.order_key}", color="green")
    success = functions.create_or_update_order(order)
    if success:
        functions.tag_order(order, "Ready")
        output.print_section_item("[+] Successfully Updated Carrier on Shipstation", color="green")
    else:
        output.print_section_item(f"[X] Order shipping update not successful {order.order_key}", log_level="error", color="red")
        failure = (order, "Shipping not set")
        retry_list.append(failure)

    output.print_section_header("------------next order---------------------\n\n")
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
            output.print_section_item(f"[!] Retrying Order: {order.order_key} because {reason}", log_level="warning", color="yellow")
            if reason == "No-DeliveryDate" or reason == "No SS Carrier Rates":
                successful = full_program(order)
                if not successful:
                    if functions.tag_order(order, reason):
                        output.print_section_item("[!] Order tagged..", log_level="warning", color="yellow")
                else:
                    # Process was successful, add Customer data to the log
                    customer_data = cl.parse_customer_data(order)
                    customer_data_log.append(customer_data)   
            
            if reason == "No UPS Rate" or reason == "No USPS Rate" or reason == "No Fedex Rate":
                successful = half_program(order)
                if not successful:
                    if functions.tag_order(order, reason):
                        output.print_section_item("[!] Order tagged..", log_level="warning", color="yellow")
                else:
                    # Process was successful, add Customer data to the log
                    customer_data = cl.parse_customer_data(order)
                    customer_data_log.append(customer_data)  
            
            if reason == "Shipping not set":
                successful = set_shipping_for_order(order)
                if not successful:
                    if functions.tag_order(order, reason):
                        output.print_section_item("[!] Order tagged..", log_level="warning", color="yellow")
                else:
                    # Process was successful, add Customer data to the log
                    customer_data = cl.parse_customer_data(order)
                    customer_data_log.append(customer_data)  

    # Log customer data for all successful order processes
    output.print_section_item("Logging Customer info...", color="green")
    success = cl.log_customer_data(customer_data_log)
    if not success:
        output.print_section_item('[!] Warning: Customer Data not Logged!', log_level="warning", color="yellow")

if __name__ == "__main__":
    try:
        main()

    except Exception as e:
        output.print_section_item(str(e), log_level="error", color="red")
        raise SystemExit("End Test")