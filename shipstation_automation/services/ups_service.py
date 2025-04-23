# lentics-shipstation/shipstation_automation/services/ups_service.py
import copy
from datetime import datetime, timedelta
from typing import List, Optional, Any

from integrations.ups_api import UPSAPIClient
from schemas.ups_schema import (
    ShipmentOrigin,
    ShipmentDestination,
    TransitTimeRequest,
    UPSServiceOption,
    ShippingRate
)

class UPSService:
    """
    UPS service for handling business logic related to UPS shipping.
    
    This service uses the UPS API client to interact with the UPS API
    and provides higher-level business logic for shipping operations.
    """
    
    def __init__(self, api_client: Optional[UPSAPIClient] = None):
        """
        Initialize the UPS service.
        
        Args:
            api_client: UPS API client to use for API requests
                        If None, a new UPSAPIClient instance will be created
        """
        self.api_client = api_client if api_client else UPSAPIClient()
        
    def create_transit_time_request_from_order(self, order: Any) -> TransitTimeRequest:
        """
        Create a transit time request from order data.
        
        Args:
            order: Order object with customer and shipment information
            
        Returns:
            TransitTimeRequest: Transit time request for UPS API
        """
        origin = ShipmentOrigin(
            country_code="US",
            city_name=order.Shipment.from_city,
            postal_code=order.Shipment.from_postal_code
        )
        
        destination = ShipmentDestination(
            country_code=order.Customer.country if order.Customer.country in ["US", "CA"] else 'US',
            state_province=order.Customer.state,
            city_name=order.Customer.city,
            postal_code=order.Customer.postal_code.replace("-", "")
        )
        
        # Calculate weight in KGS if provided in ounces
        weight = str(0.028 * order.Shipment.weight["value"]) if (
            hasattr(order.Shipment, 'weight') and 
            order.Shipment.weight.get("units") == "ounces"
        ) else "5"
        
        # Determine if residential
        residential_indicator = "01" if order.Customer.is_residential else "02"
        
        return TransitTimeRequest(
            origin=origin,
            destination=destination,
            weight=weight,
            ship_date=order.ship_date,
            residential_indicator=residential_indicator
        )

    def get_best_rate(self, order: Any) -> Optional[ShippingRate]:
        """
        Get the best shipping rate for an order.
        
        Args:
            order: Order object with customer and shipment information
            
        Returns:
            Optional[ShippingRate]: Best shipping rate if found, None otherwise
        """
        # Create transit time request from order
        request = self.create_transit_time_request_from_order(order)
        
        try:
            # Get transit times from UPS API
            transit_times = self.api_client.get_transit_times(request)
            
            # Filter services by delivery date
            valid_services = self._filter_valid_services(order, transit_times.services)
            
            # Add Ground Saver option for residential orders
            if order.Customer.is_residential:
                valid_services = self._add_ground_saver_to_list(valid_services)
            
            # Get valid rates for services
            valid_rates = self._get_valid_rates(order, valid_services)
            
            if not valid_rates:
                return None
                
            # Sort options by price and find the best one
            sorted_options = sorted(valid_rates, key=lambda x: x.price)
            best_option = self._filter_best_option(sorted_options)
            
            if best_option:
                # Remove delivery date before returning
                best_option.delivery_date = None
                return best_option
                
            return None
            
        except Exception as e:
            print(f"[X] Failed to get best rate: {e}")
            return None
    
    def _filter_valid_services(self, order: Any, services: List[UPSServiceOption]) -> List[UPSServiceOption]:
        """
        Filter services that will arrive on or before the latest delivery date.
        
        Args:
            order: Order with deliver_by_date
            services: List of UPS services
            
        Returns:
            List[UPSServiceOption]: Filtered list of valid services
        """
        valid_services = []
        
        # Convert the string to a datetime object
        date_format = "%m/%d/%Y %H:%M:%S"
        latest_time_datetime = datetime.strptime(order.deliver_by_date, date_format)
        
        for service in services:
            # Check if the delivery date is within the desired deadline
            if service.delivery_date <= latest_time_datetime:
                valid_services.append(service)
                
        return valid_services
    
    def _add_ground_saver_to_list(self, services: List[UPSServiceOption]) -> List[UPSServiceOption]:
        """
        Add Ground Saver service option based on UPS Ground service.
        
        Args:
            services: List of UPS services
            
        Returns:
            List[UPSServiceOption]: Updated list with Ground Saver service if applicable
        """
        # Helper function to add days to a date
        def add_days(delivery_date, number_of_days):
            next_day = delivery_date + timedelta(days=number_of_days)
            day_of_week_abbr = next_day.strftime('%a').upper()
            return next_day, day_of_week_abbr
        
        ground_saver = None
        
        for service in services:
            if service.service_level_description == 'UPS Ground':
                delivery_day = service.delivery_day_of_week
                
                # Create a copy of the Ground service
                ground_saver = copy.deepcopy(service)
                ground_saver.service_level = 'GNS'
                ground_saver.service_level_description = 'UPS Ground Saver'
                
                if delivery_day != "SAT":  # Not Saturday delivery
                    ground_saver.business_transit_days += 1
                    next_day, next_day_of_week = add_days(service.delivery_date, 1)
                    ground_saver.delivery_date = next_day
                    ground_saver.delivery_day_of_week = next_day_of_week
                    
                elif delivery_day == "SAT":  # Saturday delivery, skip Sunday
                    ground_saver.business_transit_days += 2
                    next_day, next_day_of_week = add_days(service.delivery_date, 2)
                    ground_saver.delivery_date = next_day
                    ground_saver.delivery_day_of_week = next_day_of_week
                
                break
        
        if ground_saver:
            services.append(ground_saver)
            
        return services
    
    def _get_valid_rates(self, order: Any, services: List[UPSServiceOption]) -> List[ShippingRate]:
        """
        Get valid rates for services based on ShipStation data.
        
        Args:
            order: Order with rates data
            services: List of UPS services
            
        Returns:
            List[ShippingRate]: List of valid shipping rates
        """
        valid_rates = []
        
        for service in services:
            for carrier in ["ups", "ups_walleted"]:
                # Skip if carrier not in rates
                if carrier not in order.rates:
                    continue
                    
                # Get the rate for the service
                rate = None
                
                # Handle UPS Ground with special case for naming
                if service.service_level_description == "UPS Ground":
                    rate = dict(order.rates[carrier]).get('UPS® Ground')
                else:
                    rate = dict(order.rates[carrier]).get(service.service_level_description)
                
                if rate is not None:
                    # Apply 3% upcharge for 'ups' account
                    if carrier == 'ups':
                        rate = round(rate * 1.03, 2)
                        
                    shipping_rate = ShippingRate(
                        carrier_code=carrier,
                        service_code=service.service_level_description if service.service_level_description != "UPS Ground" else "UPS® Ground",
                        price=rate,
                        delivery_date=service.delivery_date
                    )
                    valid_rates.append(shipping_rate)
        
        return valid_rates
    
    def _filter_best_option(self, sorted_options: List[ShippingRate]) -> Optional[ShippingRate]:
        """
        Filter and determine the best shipping option.
        
        Args:
            sorted_options: List of shipping rates sorted by price
            
        Returns:
            Optional[ShippingRate]: Best shipping option if found
        """
        if not sorted_options:
            return None
            
        # Helper function to check if Ground Saver is viable
        def remove_unviable_ground_saver(options):
            winning_index = 0
            cheapest_option = options[0]
            
            # If Ground Saver isn't saving at least $0.30, don't use it
            for index, option in enumerate(options):
                if option.service_code == "UPS Ground Saver":
                    # Check if next option is less than $0.30 more expensive
                    if index + 1 < len(options) and options[index + 1].price - cheapest_option.price < 0.30:
                        winning_index = index + 1
            
            if winning_index:
                return options[winning_index:]
            return options
        
        cheapest_option = sorted_options[0]
        better_options = [
            option for option in sorted_options 
            if 0 < option.price - cheapest_option.price < 0.35
        ]
        
        if better_options and cheapest_option.service_code == "UPS Ground Saver":
            filtered_options = remove_unviable_ground_saver(better_options)
            best_option = min(filtered_options, key=lambda x: x.delivery_date)
        elif better_options:
            best_option = min(better_options, key=lambda x: x.delivery_date)
        else:
            best_option = cheapest_option
            
        return best_option


# Adapter function to maintain compatibility with existing code
def get_ups_best_rate(order):
    """
    Get the best UPS shipping rate for an order (compatibility function).
    
    Args:
        order: Order object
        
    Returns:
        dict: Best UPS shipping rate or None
    """
    # Create UPS client and service
    api_client = UPSAPIClient()
    ups_service = UPSService(api_client)
    
    # Attach UPS client to order to maintain compatibility
    order.ups_client = api_client.session
    order.ups_client.headers.update(api_client.get_headers())
    
    # Get best rate
    best_rate = ups_service.get_best_rate(order)
    
    if best_rate:
        return best_rate.to_dict()
    return None


if __name__ == '__main__':
    try:
        print("[X] This file is not meant to be executed directly. Check for the main.py file.")
    except Exception as e:
        print('Error:', e)
        raise SystemExit("End Test")