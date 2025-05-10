"""Initialization functions for ShipStation orders using the builder pattern."""
from typing import List, Dict, Any, Optional
from shipstation_automation.utils.output_manager import OutputManager
from shipstation_automation.schemas.shipstation.v1.shipstation_v1_schema import (
    ShipstationOrderModel, 
    ShipmentModel,
    CustomerModel,
    AdvancedOptionsModel,
    MetadataModel,
    InternationalOptionsModel,
    InsuranceOptionsModel,
    DimensionsModel,
    WeightModel,
    AddressModel,
    ItemModel,
    CustomsItemModel
)

output = OutputManager(__name__)

class ShipStationOrderBuilder:
    """Builder for constructing validated ShipStation order objects."""
    
    def __init__(self, order_data: Dict[str, Any]):
        """Initialize the builder with raw order data.
        
        Args:
            order_data: Raw JSON dictionary from ShipStation API
        """
        self.order_data = order_data
        self.order = None
        
    def build_customs_items(self, customs_items_data: List[Dict[str, Any]]) -> Optional[List[CustomsItemModel]]:
        """Convert raw customs items data to validated models.
        
        Args:
            customs_items_data: List of customs item dictionaries
            
        Returns:
            List[CustomsItemModel]: Validated customs items or None if no data
        """
        if not customs_items_data:
            return None
            
        customs_items = []
        for item_data in customs_items_data:
            customs_item = CustomsItemModel.model_validate(item_data)
            customs_items.append(customs_item)
            
        return customs_items
    
    def build_international_options(self) -> InternationalOptionsModel:
        """Build international shipping options from order data.
        
        Returns:
            InternationalOptionsModel: Validated model with contents, customs items and delivery options
        """
        int_options_data = self.order_data.get('internationalOptions', {})
        if not int_options_data:
            return InternationalOptionsModel.model_validate({})
            
        customs_items_data = int_options_data.get('customsItems', [])
        customs_items = self.build_customs_items(customs_items_data) if customs_items_data else None
            
        int_options = {
            'contents': int_options_data.get('contents'),
            'customsItems': customs_items,
            'nonDelivery': int_options_data.get('nonDelivery')
        }
        
        return InternationalOptionsModel.model_validate(int_options)
    
    def build_insurance_options(self) -> InsuranceOptionsModel:
        """Build insurance options model from order data.
        
        Returns:
            InsuranceOptionsModel: Validated insurance options
        """
        insurance_data = self.order_data.get('insuranceOptions', {})
        return InsuranceOptionsModel.model_validate(insurance_data)
    
    def build_shipment(self) -> ShipmentModel:
        """Build complete shipment model with all nested components.
        
        Returns:
            ShipmentModel: Validated shipment with nested components
        """
        international_options = self.build_international_options()
        insurance_options = self.build_insurance_options()
        ship_to = AddressModel.model_validate(self.order_data.get('shipTo', {}))
        
        weight_data = self.order_data.get('weight', {})
        weight = WeightModel.model_validate(weight_data) if weight_data else None
        
        shipment_data = {
            'gift': self.order_data.get('gift', False),
            'giftMessage': self.order_data.get('giftMessage'),
            'weight': weight,
            'insuranceOptions': insurance_options,
            'internationalOptions': international_options,
            'shippingAmount': self.order_data.get('shippingAmount'),
            'ship_to': ship_to
        }
        
        return ShipmentModel.model_validate(shipment_data)
    
    def build_customer(self) -> CustomerModel:
        """Build customer model from order data.
        
        Returns:
            CustomerModel: Validated customer information
        """
        customer_data = {
            'id': self.order_data.get('customerId'),
            'username': self.order_data.get('customerUsername'),
            'name': self.order_data.get('billTo', {}).get('name'),
            'email': self.order_data.get('customerEmail'),
            'notes': self.order_data.get('customerNotes', None),
            'bill_to': AddressModel.model_validate(self.order_data.get('billTo', {})),
            'internal_notes': self.order_data.get('internalNotes', None),
            'is_residential': self.order_data.get('billTo', {}).get('residential', True)
        }
        return CustomerModel.model_validate(customer_data)
    
    def build_advanced_options(self) -> AdvancedOptionsModel:
        """Build advanced options model from order data.
        
        Returns:
            AdvancedOptionsModel: Validated advanced options settings
        """
        return AdvancedOptionsModel.model_validate(self.order_data.get('advancedOptions', {}))
    
    def build_items(self) -> List[ItemModel]:
        """Build and validate order line items with nested components.
        
        Returns:
            List[ItemModel]: Validated order items
        """
        items = []
        for item in self.order_data.get('items', []):
            # Create a copy with validated nested models
            validated_item = item.copy()
            
            # Validate weight if it exists
            if 'weight' in validated_item:
                validated_item['weight'] = WeightModel.model_validate(validated_item['weight'])
            
            items.append(ItemModel.model_validate(validated_item))
        return items
    
    def build_metadata(self):
        """Build the metadata component of the order.
    
        This method initializes the metadata object with only the data that comes from
        ShipStation's API response. All other metadata fields are left as their default
        values and will be populated by business logic later in the process.
        
        Currently only initializes:
            - deliver_by_date: From ShipStation's advancedOptions.customField1
        
        Returns:
            MetadataModel: A metadata object with ShipStation data initialized
        """
        metadata_data = {      
            'deliver_by_date': self.order_data.get('advancedOptions', {}).get('customField1')
        }
        return MetadataModel.model_validate(metadata_data)
    
    def build(self, ss_client, fedex_client, ups_client, account_name) -> Optional[ShipstationOrderModel]:
        """Build complete ShipStation order with all components.
        
        Args:
            ss_client: ShipStation API client
            fedex_client: FedEx API client
            ups_client: UPS API client
            account_name: Store/account name to associate with order
            
        Returns:
            ShipstationOrderModel: Fully validated order or None if validation fails
            
        Raises:
            No exceptions - errors are logged and None is returned
        """
        try:
            # Build all components
            shipment = self.build_shipment()
            customer = self.build_customer()
            advanced_options = self.build_advanced_options()
            metadata = self.build_metadata()
            items = self.build_items()
            
            # Create the main order object
            order_data = {
                'Shipment': shipment,
                'Customer': customer,
                'AdvancedOptions': advanced_options,
                'Metadata': metadata,
                'storeName': account_name,
                'items': items,
                'orderId': self.order_data.get('orderId'),
                'orderNumber': self.order_data.get('orderNumber'),
                'orderKey': self.order_data.get('orderKey'),
                'orderDate': self.order_data.get('orderDate'),
                'createDate': self.order_data.get('createDate'),
                'modifyDate': self.order_data.get('modifyDate'),
                'paymentDate': self.order_data.get('paymentDate'),
                'shipByDate': self.order_data.get('shipByDate'),
                'orderStatus': self.order_data.get('orderStatus'),
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
                'dimensions': DimensionsModel.model_validate(self.order_data.get('dimensions')),
                'tagIds': self.order_data.get('tagIds'),
                'userId': self.order_data.get('userId'),
                'externallyFulfilled': self.order_data.get('externallyFulfilled'),
                'externallyFulfilledBy': self.order_data.get('externallyFulfilledBy'),
                'externallyFulfilledById': self.order_data.get('externallyFulfilledById'),
                'externallyFulfilledByName': self.order_data.get('externallyFulfilledByName'),
                'labelMessages': self.order_data.get('labelMessages')
            }
            
            self.order = ShipstationOrderModel.model_validate(order_data)
            
            # # Add API clients
            # setattr(self.order, 'shipstation_client', ss_client)
            # setattr(self.order, 'fedex_client', fedex_client)
            # setattr(self.order, 'ups_client', ups_client)
            
            return self.order
            
        except Exception as e:
            output.print_section_item(f"[X] Error building order: {str(e)}", color="red")
            return None

def initialize_orders(batch_orders: List[Dict[str, Any]], 
                     ss_client, 
                     fedex_client, 
                     ups_client,
                     account_name) -> List[ShipstationOrderModel]:
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
        output.print_section_item(f"Raw Data: {order_data}\n")
        try:
            # Use the builder to construct the order
            builder = ShipStationOrderBuilder(order_data)
            order = builder.build(ss_client, fedex_client, ups_client, account_name)

            # Print the entire order to see its attributes and structure
            output.print_section_item(f"Order Structure:", color="blue")
            for field_name, field_value in order.model_dump().items():
                output.print_section_item(f"  {field_name}: {field_value}", color="cyan")
            
            if order:
                orders.append(order)
                output.print_section_item(f"[+] Initialized order: {order.order_number}", color="green")
            
        except Exception as e:
            output.print_section_item(f"[X] Error initializing order: {str(e)}", color="red")
            continue
    
    output.print_section_item(f"[+] Successfully initialized {len(orders)} orders", color="green")
    return orders