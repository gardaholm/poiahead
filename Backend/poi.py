from dataclasses import dataclass
from typing import Optional

@dataclass
class POI:
    """Represents a Point of Interest (POI) 
    
    Attributes:
        lat (float): Latitude of the POI in decimal degrees.
        lon (float): Longitude of the POI in decimal degrees.
        name (str): Display name of the POI.
        distance_to_route (float): Direct perpendicular distance from POI to nearest route point in kilometers.
        distance_on_route (float): Cumulative distance along the route from start to the nearest point in kilometers.
        poi_type (str): Type of POI (e.g., 'gas_stations', 'bakeries', 'public_toilets').
        opening_hours (Optional[str]): Opening hours information from OpenStreetMap.
        url (Optional[str]): Website URL of the POI.
        google_maps_link (str): Google Maps link to the POI location.
        price_range (Optional[str]): Price range information (e.g., '€10-20', 'Free', '€50+').
        brand (Optional[str]): Brand name of the POI (e.g., 'Shell', 'McDonald's').
        operator (Optional[str]): Operator name of the POI (e.g., 'Shell', 'BP').
        wikipedia (Optional[str]): Wikipedia link or reference for the POI.
        wikidata (Optional[str]): Wikidata ID for the POI.
    """
    lat: float
    lon: float
    name: str
    distance_to_route: float
    distance_on_route: float
    poi_type: str
    opening_hours: Optional[str] = None
    url: Optional[str] = None
    google_maps_link: str = ""
    price_range: Optional[str] = None
    brand: Optional[str] = None
    operator: Optional[str] = None
    wikipedia: Optional[str] = None
    wikidata: Optional[str] = None