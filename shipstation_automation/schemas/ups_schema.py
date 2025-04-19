# ups_schema.py
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime

@dataclass
class UPSAuthCredentials:
    """UPS OAuth credentials data model"""
    client_id: str
    client_secret: str

@dataclass
class UPSAuthResponse:
    """UPS OAuth response data model"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 0
    
@dataclass
class ShipmentOrigin:
    """Shipment origin location data"""
    country_code: str = "US"
    state_province: str = ""
    city_name: str = ""
    town_name: str = ""
    postal_code: str = ""
    
@dataclass
class ShipmentDestination:
    """Shipment destination location data"""
    country_code: str = "US"
    state_province: str = ""
    city_name: str = ""
    town_name: str = ""
    postal_code: str = ""
    
@dataclass
class TransitTimeRequest:
    """UPS transit time request payload model"""
    origin: ShipmentOrigin
    destination: ShipmentDestination
    weight: str = "5"
    weight_unit_of_measure: str = "KGS"
    shipment_contents_value: str = ""
    shipment_contents_currency_code: str = "USD"
    bill_type: str = "03"  # 02-Document, 03-Non Document, 04-WWEF (Pallet)
    ship_date: str = ""
    ship_time: str = ""
    residential_indicator: str = "02"  # 01-Residential, 02-Commercial
    avv_flag: bool = True
    number_of_packages: str = "1"
    return_unfiltered_services: bool = False
    
    def to_payload(self) -> Dict[str, Any]:
        """Convert to API request payload format"""
        return {
            "originCountryCode": self.origin.country_code,
            "originStateProvince": self.origin.state_province,
            "originCityName": self.origin.city_name,
            "originTownName": self.origin.town_name,
            "originPostalCode": self.origin.postal_code,
            "destinationCountryCode": self.destination.country_code,
            "destinationStateProvince": self.destination.state_province,
            "destinationCityName": self.destination.city_name,
            "destinationTownName": self.destination.town_name,
            "destinationPostalCode": self.destination.postal_code,
            "weight": self.weight,
            "weightUnitOfMeasure": self.weight_unit_of_measure,
            "shipmentContentsValue": self.shipment_contents_value,
            "shipmentContentsCurrencyCode": self.shipment_contents_currency_code,
            "billType": self.bill_type,
            "shipDate": self.ship_date,
            "shipTime": self.ship_time,
            "residentialIndicator": self.residential_indicator,
            "avvFlag": self.avv_flag,
            "numberOfPackages": self.number_of_packages,
            "returnUnfilterdServices": self.return_unfiltered_services
        }

@dataclass
class UPSServiceOption:
    """UPS shipping service option model"""
    service_level: str
    service_level_description: str
    guaranteed: bool
    business_transit_days: int
    delivery_date: datetime
    delivery_day_of_week: str
    
    @classmethod
    def from_api_response(cls, service_data: Dict[str, Any]) -> 'UPSServiceOption':
        """Create a UPSServiceOption instance from API response data"""
        delivery_date = datetime.strptime(service_data['deliveryDate'], '%Y-%m-%d') \
            if isinstance(service_data['deliveryDate'], str) else service_data['deliveryDate']
            
        return cls(
            service_level=service_data['serviceLevel'],
            service_level_description=service_data['serviceLevelDescription'],
            guaranteed=service_data.get('guaranteed', False),
            business_transit_days=service_data['businessTransitDays'],
            delivery_date=delivery_date,
            delivery_day_of_week=service_data['deliveryDayOfWeek']
        )

@dataclass
class TransitTimeResponse:
    """UPS transit time API response model"""
    services: List[UPSServiceOption] = field(default_factory=list)
    
    @classmethod
    def from_api_response(cls, response_data: Dict[str, Any]) -> 'TransitTimeResponse':
        """Create a TransitTimeResponse instance from API response data"""
        services = []
        for service_data in response_data.get("emsResponse", {}).get("services", []):
            services.append(UPSServiceOption.from_api_response(service_data))
        
        return cls(services=services)

@dataclass
class ShippingRate:
    """Shipping rate information"""
    carrier_code: str
    service_code: str
    price: float
    delivery_date: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ShippingRate':
        """Create a ShippingRate instance from dictionary data"""
        return cls(
            carrier_code=data['carrierCode'],
            service_code=data['serviceCode'],
            price=data['price'],
            delivery_date=data.get('deliveryDate')
        )
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        result = {
            'carrierCode': self.carrier_code,
            'serviceCode': self.service_code,
            'price': self.price
        }
        if self.delivery_date:
            result['deliveryDate'] = self.delivery_date
        return result