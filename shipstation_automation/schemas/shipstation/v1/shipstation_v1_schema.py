"""
    This file contains the Pydantic data models for the ShipStation API response.
"""
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field

# Helper function to generate camelCase aliases from snake_case
def to_camel(snake_str):
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

# Base model with camelCase alias config
class ShipStationBaseModel(BaseModel):
    model_config = {
        "populate_by_name": True,
        "alias_generator": to_camel
    }

class MappingServiceModel(ShipStationBaseModel):
    pass 

class RateModel(ShipStationBaseModel):
    pass

class WinningRateModel(ShipStationBaseModel):
    """Weight information model"""
    pass

class WeightModel(ShipStationBaseModel):
    """Weight information model"""
    value: float
    units: str = "ounces"
    weight_units: Optional[int] = Field(default=1, alias="WeightUnits")  # Capital W needs explicit alias


class DimensionsModel(ShipStationBaseModel):
    """Dimensions information model"""
    units: Optional[str] = None
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None


class AddressModel(ShipStationBaseModel):
    """Address information model"""
    name: str
    company: Optional[str] = None
    street_1: str = Field(alias="street1")
    street_2: Optional[str] = Field(default="", alias="street2")
    street_3: Optional[str] = Field(default="", alias="street3")
    city: str
    state: str
    postal_code: str = Field(alias="postalCode")
    country: str
    phone: Optional[str] = None
    residential: Optional[bool] = True
    address_verified: Optional[str] = Field(default=None, alias="addressVerified")


class ItemOptionModel(ShipStationBaseModel):
    """Item option model"""
    name: Optional[str] = None
    value: Optional[str] = None


class ItemModel(ShipStationBaseModel):
    """Order item model"""
    order_item_id: int
    line_item_key: Optional[str] = None
    sku: str
    name: str
    image_url: Optional[str] = None
    weight: Optional[WeightModel] = None
    quantity: int
    unit_price: Optional[float] = None
    tax_amount: Optional[float] = None
    shipping_amount: Optional[float] = None
    warehouse_location: Optional[str] = ""
    options: List[ItemOptionModel] = []
    product_id: int
    fulfillment_sku: Optional[str] = None
    adjustment: bool = False
    upc: Optional[str] = None
    create_date: str
    modify_date: str


class InsuranceOptionsModel(ShipStationBaseModel):
    """Insurance options model"""
    provider: Optional[str] = None
    insure_shipment: bool = False
    insured_value: float = 0.0


class InternationalOptionsModel(ShipStationBaseModel):
    """International options model"""
    contents: Optional[str] = None
    customs_items: Optional[List[Any]] = None
    non_delivery: Optional[str] = None


class AdvancedOptionsModel(ShipStationBaseModel):
    """Advanced options model"""
    warehouse_id: int = Field(alias="warehouseId")
    non_machinable: bool = Field(default=False, alias="nonMachinable")
    saturday_delivery: bool = Field(default=False, alias="saturdayDelivery")
    contains_alcohol: bool = Field(default=False, alias="containsAlcohol")
    merged_or_split: bool = Field(default=False, alias="mergedOrSplit")
    merged_ids: List[int] = Field(default=[], alias="mergedIds")
    parent_id: Optional[int] = Field(default=None, alias="parentId")
    store_id: int = Field(alias="storeId")
    custom_field1: Optional[str] = Field(default=None, alias="customField1")
    custom_field2: Optional[str] = Field(default=None, alias="customField2")
    custom_field3: Optional[str] = Field(default=None, alias="customField3")
    source: Optional[str] = None
    bill_to_party: Optional[str] = Field(default=None, alias="billToParty")
    bill_to_account: Optional[str] = Field(default=None, alias="billToAccount")
    bill_to_postal_code: Optional[str] = Field(default=None, alias="billToPostalCode")
    bill_to_country_code: Optional[str] = Field(default=None, alias="billToCountryCode")
    bill_to_my_other_account: Optional[int] = Field(default=None, alias="billToMyOtherAccount")


class ShipmentModel(ShipStationBaseModel):
    gift: bool = False
    gift_message: Optional[str] = Field(default=None, alias="giftMessage")
    weight: WeightModel
    insurance_options: InsuranceOptionsModel
    international_options: InternationalOptionsModel
    shipping_amount: Optional[float] = None
    ship_to: AddressModel


class CustomerModel(ShipStationBaseModel):
    id: int
    username: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    bill_to_dict: AddressModel
    ship_to_dict: AddressModel
    is_residential: Optional[bool] = Field(default=True, alias="isResidential")


class MetadataModel(ShipStationBaseModel):
    """Business logic metadata model for enriching ShipStation orders.
    
    This model contains fields that are populated by our business logic after the initial
    ShipStation API response. These fields are used to track shipping rates, service mappings,
    and other business-specific data that helps process the order.
    
    Attributes:
        rates: List of available shipping rates for the order
        winning_rate: The selected shipping rate for the order
        mapping_services: List of shipping service mappings
        is_multi_order: Flag indicating if this is part of a multi-order shipment
        is_double_order: Flag indicating if this is part of a double-order shipment
        smart_post_date: Delivery date for FedEx SmartPost orders
        deliver_by_date: Target delivery date from ShipStation's customField1
        hold_until_date: Date until which the order should be held
    """
    rates: Optional[List[RateModel]] = None
    winning_rate: Optional[RateModel] = None
    mapping_services: Optional[List[MappingServiceModel]] = None
    is_multi_order: bool = False
    is_double_order: bool = False
    smart_post_date: Optional[str] = None
    deliver_by_date: Optional[str] = None # set to custom field 1 in advanced options, if none set 5 days from now %m/%d/%Y %H:%M:%S


class ShipstationOrderModel(ShipStationBaseModel):
    """Main Shipstation order model that represents the full API response"""
    shipment: ShipmentModel = Field(alias="Shipment")
    customer: CustomerModel = Field(alias="Customer")
    advanced_options: AdvancedOptionsModel = Field(alias="AdvancedOptions")
    metadata: MetadataModel = Field(alias="Metadata")
    order_id: int
    order_number: str
    store_name: str = Field(alias="StoreName")
    order_key: str
    order_date: str
    create_date: str
    modify_date: str
    payment_date: str
    ship_by_date: str
    order_status: str
    bill_to: AddressModel
    ship_to: AddressModel
    items: List[ItemModel]
    order_total: Optional[float] = None
    amount_paid: Optional[float] = None
    tax_amount: Optional[float] = None
    customer_notes: Optional[str] = None
    internal_notes: Optional[str] = None
    payment_method: Optional[str] = None
    requested_shipping_service: Optional[str] = None
    carrier_code: Optional[str] = None
    service_code: Optional[str] = None
    package_code: Optional[str] = None
    confirmation: Optional[str] = None
    ship_date: Optional[str] = None
    hold_until_date: Optional[str] = None
    dimensions: DimensionsModel
    tag_ids: Optional[List[int]] = None
    user_id: Optional[int] = None
    externally_fulfilled: bool = False
    externally_fulfilled_by: Optional[str] = None
    externally_fulfilled_by_id: Optional[int] = None
    externally_fulfilled_by_name: Optional[str] = None
    label_messages: Optional[Dict[str, Any]] = None


class ListOrderResponse(ShipStationBaseModel):
    """Response model for list orders endpoint"""
    orders: List[ShipstationOrderModel]
    total: int
    page: int
    pages: int
