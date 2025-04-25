"""
    This file contains the classes for the ShipStation API..
"""
from datetime import datetime, timedelta
from shipstation_automation.utils.utils import get_ship_date

class Order:
    """
        This class represents an order from the ShipStation API. It contains the order details such as shipment info, customer info, order id, order number, order status, order total, contains alcohol, order source, order store id, order warehouse id, carrier code, and create date.

        Args:
            order_dict (dict): The dictionary containing the order details.
        Return:
            None
    """
    def __init__(self, order_dict, store_name) -> None:
        self.Shipment           = Shipment(order_dict["dimensions"], order_dict["gift"], order_dict["giftMessage"], order_dict["weight"], order_dict["insuranceOptions"], order_dict["internationalOptions"], order_dict["items"], order_dict["requestedShippingService"], order_dict["serviceCode"], order_dict["shippingAmount"])
        self.Customer           = Customer(order_dict["billTo"], order_dict["shipTo"] ,order_dict["customerId"], order_dict["customerUsername"], order_dict["customerEmail"], order_dict["customerNotes"], order_dict["internalNotes"])

        self.order_dict         = order_dict
        self.order_id           = order_dict["orderId"]
        self.shipstation_client = ""
        self.ups_client         = ""
        self.fedex_client       = ""
        self.store_name         = store_name
        self.order_key          = order_dict["orderKey"]
        self.order_date         = order_dict["orderDate"]
        self.order_number       = order_dict["orderNumber"]
        self.payment_date       = order_dict["paymentDate"]
        self.order_status       = order_dict["orderStatus"]
        self.order_total        = order_dict["orderTotal"]
        self.amount_paid        = order_dict["amountPaid"]
        self.tax_amount         = order_dict["taxAmount"]
        self.confirmation       = order_dict["confirmation"]
        self.tag_ids            = order_dict["tagIds"]
        self.advanced_options   = order_dict["advancedOptions"]
        self.contains_alcohol   = order_dict["advancedOptions"]["containsAlcohol"]
        self.order_source       = order_dict["advancedOptions"]["source"]
        self.order_storeId      = order_dict["advancedOptions"]["storeId"]
        self.order_warehouseId  = order_dict["advancedOptions"]["warehouseId"]
        self.carrier_code       = order_dict["carrierCode"]
        self.create_date        = order_dict["createDate"]
        self.is_gift            = order_dict["gift"]
        self.ship_date          = get_ship_date()
        self.shipByDate         = order_dict['shipByDate']
        self.gift_message       = order_dict["giftMessage"]
        self.payment_method     = order_dict["paymentMethod"]
        self.package_code       = 'package'
        self.deliver_by_date    = order_dict["advancedOptions"]['customField1'] if order_dict["advancedOptions"]['customField1'] else (datetime.now() + timedelta(days=5)).strftime('%m/%d/%Y %H:%M:%S')
        self.is_multi_order     = False
        self.is_double_order    = False
        self.rates              = {}
        self.winning_rate       = {}
        self.mapping_services   = {}


class Shipment:
    """
        This class represents a shipment from the ShipStation API. It contains the shipment details such as shipment id.

        Args:
            shipment_dict (dict): The dictionary containing the shipment details.
        Return:
            None
    """
    def __init__(self, shipment_dict, gift, giftMessage, weight, insurance_options_dict, internal_options, raw_items_list, requestedService, serviceCode, shipping_amount) -> None:

        if shipment_dict is not None:
            self.height             = shipment_dict["height"]
            self.length             = shipment_dict["length"]
            self.units              = shipment_dict["units"]
            self.width              = shipment_dict["width"]
        else:
            self.height             = None
            self.length             = None
            self.units              = None
            self.width              = None
            
        self.gift               = gift
        self.gift_message       = giftMessage
        self.weight             = weight # Dict: {'value': 43.51, 'units': 'ounces', 'WeightUnits': 1}
        self.insurance_options  = insurance_options_dict
        self.internal_options   = internal_options
        self.insure_shipment    = insurance_options_dict["insureShipment"]
        self.insured_value      = insurance_options_dict["insuredValue"]
        self.insurance_provider = insurance_options_dict["provider"]
        self.smart_post_date    = None
        self.shipping_amount    = shipping_amount
        self.raw_items_list     = raw_items_list
        self.from_postal_code   = None
        self.from_city          = None
        self.from_state         = None
        self.from_country       = None
        self.from_address       = None
        self.from_name          = None

        items_list = [item for item in raw_items_list if item['adjustment'] == False]
        self.items_list         = items_list

        if len(items_list) < 2 and len(items_list) > 0 and items_list is not None:
            self.item_adjustment = items_list[0]["adjustment"]
            self.item_image_url = items_list[0]["imageUrl"]
            self.item_line_key = items_list[0]["lineItemKey"]
            self.item_name = items_list[0]["name"]
            self.item_id = items_list[0]["orderItemId"]
            self.productId = items_list[0]["productId"]
            self.item_quantity = items_list[0]["quantity"]
            self.item_sku = items_list[0]["sku"]
            self.item_tax_amount = items_list[0]["taxAmount"]
            self.item_unit_price = items_list[0]["unitPrice"]
            self.item_upc = items_list[0]["upc"]
        elif items_list is not None and len(items_list) > 1:
            self.items_dict = {}
            for idx in range(len(items_list)):
                # Get the item at the current index
                item = items_list[idx]
                if not item.get('adjustment', False):
                    # Create a dictionary with selected keys
                    list_of_infos_about_the_item = {
                        key: item.get(key) for key in ["imageUrl", "lineItemKey", "name", "orderItemId", "productId", "quantity", "sku", "warehouseLocation", "taxAmount", "unitPrice", "upc"]
                    }
                    self.items_dict[idx] = list_of_infos_about_the_item

        self.requested_shipping_service = requestedService
        self.shipping_service_code = serviceCode

class Customer:
    """
        This class represents a customer from the ShipStation API. It contains the customer details such as customer id, city, name, company, country, phone, postal code, state, address1, address2, and address3.
    """
    def __init__(self, customer_dict, ship_to_dict, customer_id, customer_username, customer_email, customer_notes, internal_notes) -> None:
        self.id             = customer_id
        self.billToDict     = customer_dict
        self.shipToDict     = ship_to_dict
        self.username       = customer_username
        self.email          = customer_email
        self.internal_notes = internal_notes
        self.notes          = customer_notes
        self.city           = ship_to_dict["city"]
        self.name           = ship_to_dict["name"]
        self.company        = ship_to_dict["company"]
        self.country        = ship_to_dict["country"]
        self.phone          = ship_to_dict["phone"]
        self.postal_code    = ship_to_dict["postalCode"]
        self.state          = ship_to_dict["state"]
        self.address1       = ship_to_dict["street1"]
        self.address2       = ship_to_dict["street2"] # This could be empty
        self.address3       = ship_to_dict["street3"] # This could be empty
        self.is_residential = ship_to_dict["residential"]

if __name__ == "__main__":
    print("[X] This file is not meant to be executed directly. Check for the main.py file.")
    quit(1)
