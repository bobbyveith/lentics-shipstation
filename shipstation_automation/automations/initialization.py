"""Functions for initializing ShipStation orders directly from API data."""
from typing import List, Dict, Any, Optional
from shipstation_automation.utils.output_manager import OutputManager
from shipstation_automation.schemas.shipstation.v1.shipstation_v1_schema import (
    ShipstationOrderModel
)

output = OutputManager(__name__)

def transform_order_data(raw_order: Dict[str, Any], account_name: str) -> Dict[str, Any]:
    """Transform raw ShipStation data into the structure expected by ShipstationOrderModel.
    
    Args:
        raw_order: Raw order data from ShipStation API
        account_name: Store name to associate with order
        
    Returns:
        Dict: Transformed data matching the expected model structure
    """
    # Create shipment component
    shipment_data = {
        'gift': raw_order.get('gift', False),
        'giftMessage': raw_order.get('giftMessage'),
        'weight': raw_order.get('weight'),
        'insuranceOptions': raw_order.get('insuranceOptions', {}),
        'internationalOptions': raw_order.get('internationalOptions', {}),
        'shippingAmount': raw_order.get('shippingAmount'),
        'ship_to': raw_order.get('shipTo', {})
    }
    
    # Create customer component
    customer_data = {
        'id': raw_order.get('customerId'),
        'username': raw_order.get('customerUsername'),
        'name': raw_order.get('billTo', {}).get('name'),
        'email': raw_order.get('customerEmail'),
        'notes': raw_order.get('customerNotes'),
        'bill_to': raw_order.get('billTo', {}),
        'internal_notes': raw_order.get('internalNotes'),
        'is_residential': raw_order.get('billTo', {}).get('residential', True)
    }
    
    # Create metadata component (minimal data)
    metadata_data = {
        'deliver_by_date': raw_order.get('advancedOptions', {}).get('customField1')
    }
    
    # Handle dimensions - create default if None
    dimensions = raw_order.get('dimensions')
    if dimensions is None:
        dimensions = {
            'units': 'inches',
            'length': 0.0,
            'width': 0.0,
            'height': 0.0
        }
    
    # Create the properly structured order data
    transformed_data = {
        'Shipment': shipment_data,
        'Customer': customer_data,
        'AdvancedOptions': raw_order.get('advancedOptions', {}),
        'Metadata': metadata_data,
        'storeName': account_name,
        'items': raw_order.get('items', []),
        'orderId': raw_order.get('orderId'),
        'orderNumber': raw_order.get('orderNumber'),
        'orderKey': raw_order.get('orderKey'),
        'orderDate': raw_order.get('orderDate'),
        'createDate': raw_order.get('createDate'),
        'modifyDate': raw_order.get('modifyDate'),
        'paymentDate': raw_order.get('paymentDate'),
        'shipByDate': raw_order.get('shipByDate'),
        'orderStatus': raw_order.get('orderStatus'),
        'orderTotal': raw_order.get('orderTotal'),
        'amountPaid': raw_order.get('amountPaid'),
        'taxAmount': raw_order.get('taxAmount'),
        'customerNotes': raw_order.get('customerNotes'),
        'internalNotes': raw_order.get('internalNotes'),
        'paymentMethod': raw_order.get('paymentMethod'),
        'requestedShippingService': raw_order.get('requestedShippingService'),
        'carrierCode': raw_order.get('carrierCode'),
        'serviceCode': raw_order.get('serviceCode'),
        'packageCode': raw_order.get('packageCode'),
        'confirmation': raw_order.get('confirmation'),
        'shipDate': raw_order.get('shipDate'),
        'holdUntilDate': raw_order.get('holdUntilDate'),
        'dimensions': dimensions,
        'tagIds': raw_order.get('tagIds'),
        'userId': raw_order.get('userId'),
        'externallyFulfilled': raw_order.get('externallyFulfilled', False),
        'externallyFulfilledBy': raw_order.get('externallyFulfilledBy'),
        'externallyFulfilledById': raw_order.get('externallyFulfilledById'),
        'externallyFulfilledByName': raw_order.get('externallyFulfilledByName'),
        'labelMessages': raw_order.get('labelMessages')
    }
    
    return transformed_data

def initialize_orders(batch_orders: List[Dict[str, Any]], 
                     account_name) -> List[ShipstationOrderModel]:
    """Initialize ShipStation order objects directly from API response data.
    
    Args:
        batch_orders: List of order data dictionaries from ShipStation API
        ss_client: ShipStation API client
        fedex_client: FedEx API client
        ups_client: UPS API client
        account_name: Store/account name to associate with orders
        
    Returns:
        List[ShipstationOrderModel]: List of validated order models
    """
    output.print_section_item("[+] Initializing order objects from JSON data...", color="green")
    
    orders = []
    for raw_order in batch_orders:
        order_id = raw_order.get('orderId', 'unknown')
        order_number = raw_order.get('orderNumber', 'unknown')
        
        output.print_section_item(f"Processing order: {order_number} (ID: {order_id})")
        output.print_section_item(f"Raw Data: {raw_order}\n")
        
        try:
            # Transform the data into the expected structure
            transformed_data = transform_order_data(raw_order, account_name)
            
            # Validate the entire structure at once using Pydantic
            order = ShipstationOrderModel.model_validate(transformed_data)
            
            # Print the entire order to see its attributes and structure
            output.print_section_item(f"Order Structure:", color="blue")
            for field_name, field_value in order.model_dump().items():
                output.print_section_item(f"  {field_name}: {field_value}", color="cyan")
            
            # Store the order in our list
            orders.append(order)
            output.print_section_item(f"[+] Initialized order: {order.order_number}", color="green")
            
        except Exception as e:
            output.print_section_item(f"[X] Error initializing order {order_number} (ID: {order_id}): {str(e)}", color="red")
            continue
    
    output.print_section_item(f"[+] Successfully initialized {len(orders)} of {len(batch_orders)} orders", color="green")
    return orders