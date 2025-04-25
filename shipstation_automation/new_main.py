from shipstation_automation.utils.output_manager import OutputManager
import shipstation_automation.functions as functions
from shipstation_automation.integrations.shipstation.v1.api import connect_to_api as ShipStation
from shipstation_automation.fedex_api import create_fedex_session
from shipstation_automation.integrations.ups.ups_api import UPSAPIClient


import traceback
import time

output = OutputManager(__name__)

def check_aws_connection():
    """
    Verifies AWS credentials are available either through EC2 instance role
    or local AWS configuration. Raises SystemExit if no credentials are found.
    """
    import boto3
    from botocore.exceptions import NoCredentialsError, ClientError
    
    try:
        # This will check both EC2 role and local credentials
        boto3.client('sts').get_caller_identity()
        print("[+] AWS credentials verified")
    except (NoCredentialsError, ClientError) as e:
        raise SystemExit("[X] Program Cancelled - AWS credentials not found")
    

def create_clients(account_name="lentics"):
    '''
    This function is used to set up the program and intiated the data into python object
    '''
    # Set up the progam and get the list of orders and csv for customer logging
    functions.print_banner()

    print("======= Starting Initial Setup =======")

    # Connect to all needed API Clients
    print("Connecting to the ShipStation API...")
    ss_client = ShipStation(account_name)
    print("[+] Connected to the ShipStation API!\n\n")
    fedex_client = create_fedex_session()
    print("[+] Connected to the FedEx API!\n\n")
    ups_client = UPSAPIClient()
    print("[+] Connected to the UPS API!\n\n")
    # usps_client = USPSAPI()
    # print("[+] Connected to the USPS API!\n\n")

    # Ensure aws credentials are available
    check_aws_connection()

    return ss_client, fedex_client, ups_client


def fetch_orders_with_retry(ss_client, params, max_retries, delay=2):
    """
    Attempts to fetch all orders with a specified number of retries for each page.

    Args:
        ss_client (ShipStation): The ShipStation connection object.
        params (dict): Parameters for the fetch_orders request.
        max_retries (int): Maximum number of retries for each page.
        delay (int): Delay between retries in seconds.

    Returns:
        list: A list of all orders (parsed from the response JSON).
    """
    for attempt in range(max_retries):
        try:
            response = ss_client.fetch_orders(parameters=params)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4xx/5xx)
            break  # Exit the retry loop if the request is successful
        except Exception as e:
            print(f"[X] Attempt {attempt+1} failed with error: {e}")
            time.sleep(delay)  # Wait before retrying
    else:
        print(f"[X] Failed to fetch page after {max_retries} attempts.")
        return None  # Return None if any page fails after max retries
    return response


def fetch_all_awaiting_shipment_order_ids():
    """
    Fetches all order IDs with 'awaiting_shipment' status from ShipStation.
    
    Returns:
        set: Set of all order IDs in 'awaiting_shipment' status
    """
    try:
        output.print_section_header("🔍 Fetching all awaiting shipment order IDs")
        
        # Create ShipStation client
        ss_client = ShipStation("sporticulture")
        
        # Initialize variables
        page = 1
        page_size = 100  # Use larger page size for efficiency when just getting IDs
        all_order_ids = set()
        has_more_pages = True
        
        # First request to get total pages
        parameters = {
            'page': '1',
            'page_size': str(page_size),
            'order_status': 'awaiting_shipment',
            'sort_by': 'OrderDate',
            'sort_dir': 'ASC'
        }
        
        response = fetch_orders_with_retry(ss_client, parameters, max_retries=10, delay=5)
        
        if response.status_code != 200:
            output.print_section_item(f"[X] Error fetching orders: {response.status_code}", color="red")
            return set()
            
        page_data = response.json()
        total_pages = page_data.get('pages', 1)
        total_orders = page_data.get('total', 0)
        
        output.print_section_item(f"[+] Found {total_orders} orders across {total_pages} pages", color="green")
        
        # Process all pages to collect order IDs
        while page <= total_pages:
            output.print_section_item(f"[+] Fetching order IDs from page {page}/{total_pages}", color="green")
            
            # Skip first page fetch since we already have it
            if page > 1:
                parameters['page'] = str(page)
                response = fetch_orders_with_retry(ss_client, parameters, max_retries=10, delay=5)
                
                if response.status_code != 200:
                    output.print_section_item(f"[X] Error fetching page {page}: {response.status_code}", color="red")
                    page += 1
                    continue
                    
                page_data = response.json()
            
            # Extract order IDs from this page
            page_orders = page_data.get('orders', [])
            page_order_ids = {order.get('orderId') for order in page_orders if order.get('orderId')}
            
            # Add to our set
            all_order_ids.update(page_order_ids)
            
            output.print_section_item(f"[+] Collected {len(page_order_ids)} order IDs from page {page} (total: {len(all_order_ids)})", color="green")
            page += 1
            
        
        output.print_section_item(f"[+] Successfully collected {len(all_order_ids)} unique order IDs", color="green")
        return all_order_ids
        
    except Exception as e:
        output.print_section_item(f"[X] Error fetching order IDs: {str(e)}", color="red")
        traceback.print_exc()
        return set()


def main(account_name="lentics", batch_size=5):

    """
    Main entry point for the ShipStation processing command.
    Fetches all order IDs first, then processes each order individually.
    """
    try:
        output.print_banner()
        output.print_section_header("🚀 Running Shipstation...")
        

        # Create all the needed API Clients
        ss_client, fedex_client, ups_client = create_clients(account_name)

        # Initialize the rule engine for the specific account 
        #rule_engine = BaseRuleEngine.get_instance(account_name=account_name, account_id=1)

        # Fetch all order IDs first
        all_order_ids = list(fetch_all_awaiting_shipment_order_ids())

        output.print_section_item(f"[+] Found {len(all_order_ids)} orders to process", color="green")
        for order_id in all_order_ids:
            output.print_section_item(f"  - Order ID: {order_id}", color="green")

        raise SystemExit("End Test")

        if not all_order_ids:
            output.print_section_item("[X] No orders to process", color="red")
            return
            
        total_orders = len(all_order_ids)
        
        output.print_section_header(f"🔄 Processing {total_orders} orders")
        
        # Process orders in batches for efficiency
        processed_count = 0
        
        # Process in batches of specified size
        for batch_start in range(0, total_orders, batch_size):
            batch_end = min(batch_start + batch_size, total_orders)
            batch_ids = all_order_ids[batch_start:batch_end]
            
            output.print_section_item(f"\n[+] Processing batch {batch_start//batch_size + 1}/{(total_orders+batch_size-1)//batch_size} (orders {batch_start+1}-{batch_end} of {total_orders})", color="green")
            
            batch_orders = []
            
            # Fetch each order in the batch
            for order_id in batch_ids:
                try:
                    # Fetch order details
                    response = ss_client.get_order(order_id)
                    
                    if response.status_code != 200:
                        output.print_section_item(f"[X] Error fetching order {order_id}: {response.status_code}", color="red")
                        continue
                        
                    order_data = response.json()
                    batch_orders.append(order_data)
                    
                except Exception as e:
                    output.print_section_item(f"[X] Error fetching order {order_id}: {str(e)}", color="red")
                    continue
            
            # # Process the batch of orders
            # orders = serialization.serialize_orders(
            #     initialization.initialize_orders(
            #         batch_orders,
            #         ss_client, fedex_client, ups_client, usps_client
            #     ),
            #     rule_engine
            # )

            # # Filter for valid trading partners
            # valid_orders = [order for order in orders if order.Metainfo.trading_partner in valid_trading_partners]
            # output.print_section_item(f"[+] Found {len(valid_orders)} valid orders in this batch", color="green")

            # # Process valid orders
            # if valid_orders:
            #     process_orders(valid_orders, report)
            
            # processed_count += len(valid_orders)
            output.print_section_item(f"[+] Total processed: {processed_count}/{total_orders}", color="green")
            
            # Force garbage collection between batches
            import gc
            gc.collect()
        

        output.print_section_header(f"✅ Finished processing {processed_count} orders")

    except Exception as e:
        output.print_section_item(f"Error in main function: {str(e)}", color="red")
        traceback.print_exc()