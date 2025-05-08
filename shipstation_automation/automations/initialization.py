"""
This module contains initialization functions for ShipStation orders.
"""
from typing import List, Dict, Any
from shipstation_automation.utils.output_manager import OutputManager
from shipstation_automation.schemas.shipstation.v1.shipstation_v1_schema import (
    ShipstationOrderModel, 
    ShipmentModel,
    CustomerModel,
    AdvancedOptionsModel,
    MetadataModel
)

output = OutputManager(__name__)

class ShipStationOrderBuilder:
    """Builder for constructing ShipStation order objects."""
    
    def __init__(self, order_data: Dict[str, Any]):
        self.order_data = order_data
        self.order = None
        
    def build_shipment(self):
        """Build the shipment component of the order."""
        shipment_data = {
            'gift': self.order_data.get('gift', False),
            'giftMessage': self.order_data.get('giftMessage'),
            'weight': self.order_data.get('weight'),
            'insuranceOptions': self.order_data.get('insuranceOptions'),
            'internationalOptions': self.order_data.get('internationalOptions'),
            'shippingAmount': self.order_data.get('shippingAmount'),
            'raw_items_list': self.order_data.get('items'),
            'ship_to': self.order_data.get('shipTo')
        }
        return ShipmentModel.model_validate(shipment_data)
    
    def build_customer(self):
        """Build the customer component of the order."""
        customer_data = {
            'id': self.order_data.get('customerId'),
            'username': self.order_data.get('customerUsername'),
            'name': self.order_data.get('billTo', {}).get('name'),
            'email': self.order_data.get('customerEmail'),
            'notes': self.order_data.get('customerNotes'),
            'bill_to_dict': self.order_data.get('billTo'),
            'ship_to_dict': self.order_data.get('shipTo'),
            'internal_notes': self.order_data.get('internalNotes'),
            'is_residential': self.order_data.get('billTo', {}).get('residential')
        }
        return CustomerModel.model_validate(customer_data)
    
    def build_advanced_options(self):
        """Build the advanced options component of the order."""
        return AdvancedOptionsModel.model_validate(self.order_data.get('advancedOptions', {}))
    
    def build_metadata(self):
        """Build the metadata component of the order."""
        metadata_data = {
            'rates': None,
            'winning_rate': None,
            'mapping_services': None,
            'is_multi_order': False,
            'is_double_order': False,
            'smart_post_date': None,
            'deliver_by_date': self.order_data.get('advancedOptions', {}).get('customField1'),
            'hold_until_date': None
        }
        return MetadataModel.model_validate(metadata_data)
    
    def build(self, ss_client, fedex_client, ups_client):
        """Build the complete order object."""
        try:
            # Build all components
            shipment = self.build_shipment()
            customer = self.build_customer()
            advanced_options = self.build_advanced_options()
            metadata = self.build_metadata()
            
            # Create the main order object
            order_data = {
                'Shipment': shipment,
                'Customer': customer,
                'AdvancedOptions': advanced_options,
                'Metadata': metadata,
                'orderId': self.order_data.get('orderId'),
                'orderNumber': self.order_data.get('orderNumber'),
                'storeName': self.order_data.get('storeName'),
                'orderKey': self.order_data.get('orderKey'),
                'orderDate': self.order_data.get('orderDate'),
                'createDate': self.order_data.get('createDate'),
                'modifyDate': self.order_data.get('modifyDate'),
                'paymentDate': self.order_data.get('paymentDate'),
                'shipByDate': self.order_data.get('shipByDate'),
                'orderStatus': self.order_data.get('orderStatus'),
                'billTo': self.order_data.get('billTo'),
                'shipTo': self.order_data.get('shipTo'),
                'items': self.order_data.get('items'),
                'orderTotal': self.order_data.get('orderTotal'),
                'amountPaid': self.order_data.get('amountPaid'),
                'taxAmount': self.order_data.get('taxAmount'),
                'customerNotes': self.order_data.get('customerNotes'),
                'internalNotes': self.order_data.get('internalNotes'),
                'paymentMethod': self.order_data.get('paymentMethod'),
                'requestedShippingService': self.order_data.get('requestedShippingService'),
                'carrierCode': self.order_data.get('carrierCode'),
                'serviceCode': self.order_data.get('serviceCode'),
                'packageCode': self.order_data.get('packageCode'),
                'confirmation': self.order_data.get('confirmation'),
                'shipDate': self.order_data.get('shipDate'),
                'dimensions': self.order_data.get('dimensions'),
                'tagIds': self.order_data.get('tagIds'),
                'userId': self.order_data.get('userId'),
                'externallyFulfilled': self.order_data.get('externallyFulfilled'),
                'externallyFulfilledBy': self.order_data.get('externallyFulfilledBy'),
                'externallyFulfilledById': self.order_data.get('externallyFulfilledById'),
                'externallyFulfilledByName': self.order_data.get('externallyFulfilledByName'),
                'labelMessages': self.order_data.get('labelMessages')
            }
            
            self.order = ShipstationOrderModel.model_validate(order_data)
            
            # Add API clients
            setattr(self.order, 'shipstation_client', ss_client)
            setattr(self.order, 'fedex_client', fedex_client)
            setattr(self.order, 'ups_client', ups_client)
            
            return self.order
            
        except Exception as e:
            output.print_section_item(f"[X] Error building order: {str(e)}", color="red")
            return None

def initialize_orders(batch_orders: List[Dict[str, Any]], 
                     ss_client, 
                     fedex_client, 
                     ups_client) -> List[ShipstationOrderModel]:
    """
    Initialize ShipStation order objects from API response data using the Builder pattern.
    
    Args:
        batch_orders: List of order data dictionaries from ShipStation API
        ss_client: ShipStation API client
        fedex_client: FedEx API client
        ups_client: UPS API client
        
    Returns:
        List of initialized ShipstationOrderModel objects
    """
    output.print_section_item("[+] Initializing order objects from JSON data...", color="green")
    
    orders = []
    
    for order_data in batch_orders:
        try:
            # Use the builder to construct the order
            builder = ShipStationOrderBuilder(order_data)
            order = builder.build(ss_client, fedex_client, ups_client)
            
            if order:
                orders.append(order)
                output.print_section_item(f"[+] Initialized order: {order.orderNumber}", color="green")
            
        except Exception as e:
            output.print_section_item(f"[X] Error initializing order: {str(e)}", color="red")
            continue
    
    output.print_section_item(f"[+] Successfully initialized {len(orders)} orders", color="green")
    return orders