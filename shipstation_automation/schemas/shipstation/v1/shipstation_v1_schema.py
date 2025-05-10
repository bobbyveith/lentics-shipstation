"""
    This file contains the Pydantic data models for the ShipStation API response.
"""
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

from shipstation_automation.schemas.shipstation.v1.shipstation_v1_enums import (
    WeightUnit,
    DimensionsUnit,
    OrderStatus,
    ConfirmationType,
    Contents,
    NonDeliveryOption
)

# Helper function to generate camelCase aliases from snake_case
def to_camel(snake_str):
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

# Base model with camelCase alias config
class ShipStationBaseModel(BaseModel):
    model_config = {
        "populate_by_name": True,
        "alias_generator": to_camel,
        "allow_population_by_field_name": True,
        "extra": "forbid"
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
    units: WeightUnit = WeightUnit.OUNCES
    weight_units: Optional[int] = Field(default=1, alias="WeightUnits")  # Capital W needs explicit alias


class DimensionsModel(ShipStationBaseModel):
    """Dimensions information model"""
    units: DimensionsUnit = DimensionsUnit.INCHES
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
    options: List[Any] = Field(default_factory=list)
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


class CustomsItemModel(ShipStationBaseModel):
    """
    Customs Item model for international shipments.
    
    Represents a single line item in a customs declaration for international shipments.
    See: https://www.shipstation.com/docs/api/models/customs-item/
    """
    customs_item_id: Optional[str] = Field(default=None, alias="customsItemId")
    description: str
    quantity: float
    value: float
    harmonized_tariff_code: Optional[str] = Field(default=None, alias="harmonizedTariffCode")
    country_of_origin: str = Field(alias="countryOfOrigin")


class InternationalOptionsModel(ShipStationBaseModel):
    """International options model"""
    contents: Optional[Contents] = None
    customs_items: Optional[List[CustomsItemModel]] = None  
    non_delivery: Optional[NonDeliveryOption] = Field(default=None, alias="nonDelivery")


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
    bill_to: AddressModel
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
    order_id: int = Field(alias="orderId")
    order_number: str = Field(alias="orderNumber")
    store_name: str = Field(alias="storeName")
    order_key: str = Field(alias="orderKey")
    order_date: str = Field(alias="orderDate")
    create_date: str = Field(alias="createDate")
    modify_date: str = Field(alias="modifyDate")
    payment_date: str = Field(alias="paymentDate")
    ship_by_date: str = Field(alias="shipByDate")
    order_status: OrderStatus = Field(default=OrderStatus.AWAITING_SHIPMENT, alias="orderStatus")
    items: List[ItemModel] = Field(alias="items")
    order_total: Optional[float] = Field(default=None, alias="orderTotal")
    amount_paid: Optional[float] = Field(default=None, alias="amountPaid")
    tax_amount: Optional[float] = Field(default=None, alias="taxAmount")
    customer_notes: Optional[str] = Field(default=None, alias="customerNotes")
    internal_notes: Optional[str] = Field(default=None, alias="internalNotes")
    payment_method: Optional[str] = Field(default=None, alias="paymentMethod")
    requested_shipping_service: Optional[str] = Field(default=None, alias="requestedShippingService")
    carrier_code: Optional[str] = Field(default=None, alias="carrierCode")
    service_code: Optional[str] = Field(default=None, alias="serviceCode")
    package_code: Optional[str] = Field(default=None, alias="packageCode")
    confirmation: Optional[ConfirmationType] = Field(default=None, alias="confirmation")
    ship_date: Optional[str] = Field(default=None, alias="shipDate")
    hold_until_date: Optional[str] = Field(default=None, alias="holdUntilDate")
    dimensions: DimensionsModel = Field(alias="dimensions")
    tag_ids: Optional[List[int]] = Field(default=None, alias="tagIds")
    user_id: Optional[int] = Field(default=None, alias="userId")
    externally_fulfilled: bool = Field(default=False, alias="externallyFulfilled")
    externally_fulfilled_by: Optional[str] = Field(default=None, alias="externallyFulfilledBy")
    externally_fulfilled_by_id: Optional[int] = Field(default=None, alias="externallyFulfilledById")
    externally_fulfilled_by_name: Optional[str] = Field(default=None, alias="externallyFulfilledByName")
    label_messages: Optional[Dict[str, Any]] = Field(default=None, alias="labelMessages")


class ListOrderResponse(ShipStationBaseModel):
    """Response model for list orders endpoint"""
    orders: List[ShipstationOrderModel]
    total: int
    page: int
    pages: int
