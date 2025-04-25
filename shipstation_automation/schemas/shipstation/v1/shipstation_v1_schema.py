"""
    This file contains the Pydantic data models for the ShipStation API response.
"""
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field


class WeightModel(BaseModel):
    """Weight information model"""
    value: float
    units: str
    WeightUnits: Optional[int] = None


class DimensionsModel(BaseModel):
    """Dimensions information model"""
    units: str
    length: float
    width: float
    height: float


class AddressModel(BaseModel):
    """Address information model"""
    name: str
    company: Optional[str] = None
    street1: str
    street2: Optional[str] = ""
    street3: Optional[str] = ""
    city: str
    state: str
    postalCode: str
    country: str
    phone: Optional[str] = None
    residential: Optional[bool] = None
    addressVerified: Optional[str] = None


class ItemOptionModel(BaseModel):
    """Item option model"""
    name: str
    value: str


class ItemModel(BaseModel):
    """Order item model"""
    orderItemId: int
    lineItemKey: str
    sku: str
    name: str
    imageUrl: Optional[str] = None
    weight: Optional[WeightModel] = None
    quantity: int
    unitPrice: float
    taxAmount: float
    shippingAmount: float
    warehouseLocation: Optional[str] = ""
    options: List[ItemOptionModel] = []
    productId: int
    fulfillmentSku: Optional[str] = None
    adjustment: bool = False
    upc: Optional[str] = None
    createDate: str
    modifyDate: str


class InsuranceOptionsModel(BaseModel):
    """Insurance options model"""
    provider: Optional[str] = None
    insureShipment: bool = False
    insuredValue: float = 0.0


class InternationalOptionsModel(BaseModel):
    """International options model"""
    contents: Optional[str] = None
    customsItems: Optional[List[Any]] = None
    nonDelivery: Optional[str] = None


class AdvancedOptionsModel(BaseModel):
    """Advanced options model"""
    warehouseId: int
    nonMachinable: bool = False
    saturdayDelivery: bool = False
    containsAlcohol: bool = False
    mergedOrSplit: bool = False
    mergedIds: List[int] = []
    parentId: Optional[int] = None
    storeId: int
    customField1: Optional[str] = None
    customField2: Optional[str] = None
    customField3: Optional[str] = None
    source: str
    billToParty: Optional[str] = None
    billToAccount: Optional[str] = None
    billToPostalCode: Optional[str] = None
    billToCountryCode: Optional[str] = None
    billToMyOtherAccount: Optional[int] = None


class ShipmentModel(BaseModel):
    pass


class CustomerModel(BaseModel):
    id: int
    username: str
    name: str
    email: str
    notes: str
    billToDict: AddressModel
    shipToDict: AddressModel
    internalNotes: str
    is_residential: bool

    

class ShipstationOrderModel(BaseModel):
    """Main Shipstation order model that represents the full API response"""
    Customer: CustomerModel
    Shipment: ShipmentModel
    orderId: int
    orderNumber: str
    storeName: str
    orderKey: str
    orderDate: str
    createDate: str
    modifyDate: str
    paymentDate: str
    shipByDate: str
    orderStatus: str
    billTo: AddressModel
    shipTo: AddressModel
    items: List[ItemModel]
    orderTotal: float
    amountPaid: float
    taxAmount: float
    shippingAmount: float
    customerNotes: Optional[str] = None
    internalNotes: Optional[str] = None
    gift: bool = False
    giftMessage: Optional[str] = None
    paymentMethod: str
    requestedShippingService: str
    carrierCode: str
    serviceCode: str
    packageCode: str
    confirmation: str
    shipDate: Optional[str] = None
    holdUntilDate: Optional[str] = None
    weight: WeightModel
    dimensions: DimensionsModel
    insuranceOptions: InsuranceOptionsModel
    internationalOptions: InternationalOptionsModel
    advancedOptions: AdvancedOptionsModel
    tagIds: Optional[List[int]] = None
    userId: Optional[int] = None
    externallyFulfilled: bool = False
    externallyFulfilledBy: Optional[str] = None
    externallyFulfilledById: Optional[int] = None
    externallyFulfilledByName: Optional[str] = None
    labelMessages: Optional[Dict[str, Any]] = None


class ListOrderResponse(BaseModel):
    """Response model for list orders endpoint"""
    orders: List[ShipstationOrderModel]
    total: int
    page: int
    pages: int
