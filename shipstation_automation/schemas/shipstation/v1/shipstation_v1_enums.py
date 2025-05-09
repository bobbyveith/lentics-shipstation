from enum import Enum
from typing import List, Tuple

class WeightUnit(str, Enum):
    OUNCES = "ounces"
    POUNDS = "pounds"
    GRAMS = "grams"
    KILOGRAMS = "kilograms"

class DimensionsUnit(str, Enum):
    INCHES = "inches"
    CENTIMETERS = "centimeters"

class OrderStatus(str, Enum):
    AWAITING_PAYMENT = "awaiting_payment" 
    AWAITING_SHIPMENT = "awaiting_shipment"
    SHIPPED = "shipped"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"

class ConfirmationType(str, Enum):
    NONE = "none"
    DELIVERY = "delivery"
    SIGNATURE = "signature"
    ADULT_SIGNATURE = "adult_signature"
    DIRECT_SIGNATURE = "direct_signature"

class Contents(str, Enum):
    MERCHANDISE = "merchandise"
    DOCUMENTS = "documents"
    GIFT = "gift"
    RETURNED_GOODS = "returned_goods"
    SAMPLE = "sample"

class NonDeliveryOption(str, Enum):
    RETURN_TO_SENDER = "return_to_sender"
    TREAT_AS_ABANDONED = "treat_as_abandoned"

class WebhookEvent(str, Enum):
    ORDER_NOTIFY = "ORDER_NOTIFY"
    ITEM_ORDER_NOTIFY = "ITEM_ORDER_NOTIFY"
    SHIP_NOTIFY = "SHIP_NOTIFY"
    ITEM_SHIP_NOTIFY = "ITEM_SHIP_NOTIFY"

# Parameter sets - useful for validating API requests
class ParameterSets:
    ORDER_LIST: Tuple[str, ...] = (
        "customer_name", "item_keyword", "create_date_start", "create_date_end",
        "modify_date_start", "modify_date_end", "order_date_start", "order_date_end",
        "order_number", "order_status", "payment_date_start", "payment_date_end",
        "store_id", "sort_by", "sort_dir", "page", "page_size"
    )
    
    CUSTOMER_LIST: Tuple[str, ...] = (
        "state_code", "country_code", "marketplace_id", "tag_id",
        "sort_by", "sort_dir", "page_size"
    )
    
    FULFILLMENT_LIST: Tuple[str, ...] = (
        "fulfillment_id", "order_id", "order_number", "tracking_number",
        "recipient_name", "create_date_start", "create_date_end",
        "ship_date_start", "ship_date_end", "sort_by", "sort_dir", "page", "page_size"
    )
    
    SHIPMENT_LIST: Tuple[str, ...] = (
        "recipient_name", "recipient_country_code", "order_number", "order_id",
        "carrier_code", "service_code", "tracking_number", "create_date_start",
        "create_date_end", "ship_date_start", "ship_date_end", "void_date_start",
        "void_date_end", "store_id", "include_shipment_items", "sort_by",
        "sort_dir", "page", "page_size"
    )
    
    CREATE_SHIPMENT_LABEL: Tuple[str, ...] = (
        "carrier_code", "service_code", "package_code", "confirmation",
        "ship_date", "weight", "dimensions", "ship_from", "ship_to",
        "insurance_options", "international_options", "advanced_options", "test_label"
    )
    
    GET_RATE: Tuple[str, ...] = (
        "carrier_code", "from_postal_code", "to_state", "to_country",
        "to_postal_code", "weight", "service_code", "package_code",
        "to_city", "dimensions", "confirmation", "residential"
    )
    
    REQUIRED_RATE: Tuple[str, ...] = (
        "carrier_code", "from_postal_code", "to_state", "to_country",
        "to_postal_code", "weight"
    )
    
    UPDATE_STORE: Tuple[str, ...] = (
        "store_id", "store_name", "marketplace_id", "marketplace_name",
        "account_name", "email", "integration_url", "active", "company_name",
        "phone", "public_email", "website", "refresh_date", "last_refresh_attempt",
        "create_date", "modify_date", "auto_refresh", "status_mappings"
    )
    
    SUBSCRIBE_TO_WEBHOOK: Tuple[str, ...] = (
        "target_url", "event", "store_id", "friendly_name"
    )