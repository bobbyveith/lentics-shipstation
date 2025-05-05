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
    units: str
    length: float
    width: float
    height: float


class AddressModel(ShipStationBaseModel):
    """Address information model"""
    name: str
    company: Optional[str] = None
    street1: str
    street2: Optional[str] = ""
    street3: Optional[str] = ""
    city: str
    state: str
    postal_code: str = Field(alias="postalCode")
    country: str
    phone: Optional[str] = None
    residential: Optional[bool] = None
    address_verified: Optional[str] = Field(default=None, alias="addressVerified")


class ItemOptionModel(ShipStationBaseModel):
    """Item option model"""
    name: str
    value: str


class ItemModel(ShipStationBaseModel):
    """Order item model"""
    order_item_id: int
    line_item_key: str
    sku: str
    name: str
    image_url: Optional[str] = None
    weight: Optional[WeightModel] = None
    quantity: int
    unit_price: float
    tax_amount: float
    shipping_amount: float
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
    order_store_id: int = Field(alias="order_storeId")  # Preserving existing field name
    custom_field1: Optional[str] = Field(default=None, alias="customField1")
    custom_field2: Optional[str] = Field(default=None, alias="customField2")
    custom_field3: Optional[str] = Field(default=None, alias="customField3")
    source: str
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
    shipping_amount: float
    raw_items_list = None
    ship_to = AddressModel


class CustomerModel(ShipStationBaseModel):
    id: int
    username: str
    name: str
    email: str
    notes: str
    bill_to_dict: AddressModel
    ship_to_dict: AddressModel
    internal_notes: str
    is_residential: Optional[bool] = Field(default=True, alias="isResidential")


class MetadataModel(ShipStationBaseModel):
    """Metadata model"""
    rates: Optional[List[RateModel]] = None
    winning_rate: Optional[RateModel] = None
    mapping_services: Optional[List[MappingServiceModel]] = None
    is_multi_order: bool = False
    is_double_order: bool = False
    smart_post_date = None
    deliver_by_date: Optional[str] = None # set to custom field 1 in advanced options, if none set 5 days from now %m/%d/%Y %H:%M:%S
    hold_until_date: Optional[str] = None


class ShipstationOrderModel(ShipStationBaseModel):
    """Main Shipstation order model that represents the full API response"""
    shipment: ShipmentModel = Field(alias="Shipment")
    customer: CustomerModel = Field(alias="Customer")
    advanced_options: AdvancedOptionsModel = Field(alias="AdvancedOptions")
    metadata: MetadataModel = Field(alias="Metadata")
    order_id: int
    order_number: str
    store_name: str
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
    order_total: float
    amount_paid: float
    tax_amount: float
    customer_notes: Optional[str] = None
    internal_notes: Optional[str] = None
    payment_method: str
    requested_shipping_service: str
    carrier_code: str
    service_code: str
    package_code: str
    confirmation: str
    ship_date: Optional[str] = None
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
