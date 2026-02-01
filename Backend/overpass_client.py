import requests 
import time
from typing import List, Dict, Optional, Callable
from Backend.route_storage import RoutePoint, Route
from Backend.route_calculator import RouteCalculator    
from Backend.poi import POI
from haversine import haversine

# POI type configurations mapping to Overpass query patterns
# Queries include both nodes and ways to capture all POIs (many shops are mapped as building ways)
POI_TYPE_CONFIG = {
    "public_toilets": {
        "query": 'node["amenity"="toilets"]({south},{west},{north},{east}); way["amenity"="toilets"]({south},{west},{north},{east});',
        "default_name": "Unnamed Toilet"
    },
    "bakeries": {
        "query": 'node["shop"="bakery"]({south},{west},{north},{east}); way["shop"="bakery"]({south},{west},{north},{east}); node["amenity"="bakery"]({south},{west},{north},{east}); way["amenity"="bakery"]({south},{west},{north},{east});',
        "default_name": "Unnamed Bakery"
    },
    "gas_stations": {
        "query": 'node["amenity"="fuel"]({south},{west},{north},{east}); way["amenity"="fuel"]({south},{west},{north},{east}); node["shop"="fuel"]({south},{west},{north},{east}); way["shop"="fuel"]({south},{west},{north},{east});',
        "default_name": "Unnamed Gas Station"
    },
    "grocery_stores": {
        "query": 'node["shop"~"^(supermarket|convenience|grocery)$"]({south},{west},{north},{east}); way["shop"~"^(supermarket|convenience|grocery)$"]({south},{west},{north},{east});',
        "default_name": "Unnamed Grocery Store"
    },
    "water_fountains": {
        "query": 'node["amenity"~"^(drinking_water|fountain)$"]({south},{west},{north},{east}); way["amenity"~"^(drinking_water|fountain)$"]({south},{west},{north},{east});',
        "default_name": "Unnamed Water Fountain"
    },
    "bicycle_shops": {
        "query": 'node["shop"="bicycle"]({south},{west},{north},{east}); way["shop"="bicycle"]({south},{west},{north},{east}); node["service"="bicycle_repair"]({south},{west},{north},{east}); way["service"="bicycle_repair"]({south},{west},{north},{east});',
        "default_name": "Unnamed Bicycle Shop"
    },
    "bicycle_vending": {
        "query": 'node["amenity"="bicycle_rental"]["vending"]({south},{west},{north},{east}); way["amenity"="bicycle_rental"]["vending"]({south},{west},{north},{east});',
        "default_name": "Unnamed Bicycle Vending"
    },
    "vending_machines": {
        "query": 'node["amenity"="vending_machine"]["vending"~"^(drinks|food)$"]({south},{west},{north},{east}); way["amenity"="vending_machine"]["vending"~"^(drinks|food)$"]({south},{west},{north},{east});',
        "default_name": "Unnamed Vending Machine"
    },
    "camping_hotels": {
        "query": 'node["tourism"~"^(camp_site|camping|hotel|hostel|guest_house|motel)$"]({south},{west},{north},{east}); way["tourism"~"^(camp_site|camping|hotel|hostel|guest_house|motel)$"]({south},{west},{north},{east});',
        "default_name": "Unnamed Accommodation"
    },
    "sport_areas": {
        "query": 'node["leisure"~"^(sports_centre|stadium|recreation_ground)$"]({south},{west},{north},{east}); way["leisure"~"^(sports_centre|stadium|recreation_ground)$"]({south},{west},{north},{east});',
        "default_name": "Unnamed Sport Area"
    }
}

class OverpassClient:
    """ 
    Client to interact with the Overpass API for querying POIs along a route. 
    
        Attributes:
            overpass_url (str): The URL of the Overpass API endpoint.  
            route (Route): The route for which to query POIs.
            route_calculator (Route Calculator): Utility for route calculations.
 
        Methods:
            get_route_bounding_box(buffer_km: float) -> dict:
                Calculate a bounding box around the route with optional buffer.    
            query_poi_type(bbox: dict, poi_type: str, max_retries: int = 3) -> dict:
                Query the Overpass API for a specific POI type within the given bounding box.
            query_all_poi_types(bbox: dict, delay_seconds: float = 0.75) -> List[POI]:
                Query all POI types sequentially to avoid timeouts.
            filter_pois(overpass_poi_data: dict, poi_type: str, max_distance_to_route_km: float = 1.0) -> List[POI]:
                Filter POIs based on their distance to the route. 
    """

    def __init__(self, route: Route):
        # Try multiple Overpass API instances for better reliability
        self.overpass_urls = [
            "https://overpass-api.de/api/interpreter",  # Primary (HTTPS)
            "http://overpass-api.de/api/interpreter",  # Fallback (HTTP)
            "https://overpass.kumi.systems/api/interpreter",  # Alternative instance
        ]
        self.route = route
        self.route_calculator = RouteCalculator()

    def get_route_bounding_box(self, buffer_km: float = 1.0) -> dict:
        """ 
        Calculate a bounding box around the route with optional buffer. 

            Args:
                buffer_km (float): Buffer distance in kilometers to expand the bounding box. Default is 1.0 km. 
            Returns:
                dict: A dictionary representing the bounding box with keys 'south', 'north', 'west', 'east'.
        """
        min_lat = min(point.lat for point in self.route.points)
        max_lat = max(point.lat for point in self.route.points)
        min_lon = min(point.lon for point in self.route.points)
        max_lon = max(point.lon for point in self.route.points)
        conversion_factor = 111.0  # Approximate conversion from km to degrees
        buffer_deg = buffer_km / conversion_factor
        return {
            "south": min_lat - buffer_deg,
            "north": max_lat + buffer_deg,
            "west": min_lon - buffer_deg,
            "east": max_lon + buffer_deg
        }

    def query_poi_type(self, bbox: dict, poi_type: str, max_retries: int = 3):
        """
        Query the Overpass API for a specific POI type within the given bounding box.
        Tries multiple API instances and retries with exponential backoff.
            Args:
                bbox (dict): A dictionary representing the bounding box with keys 'south', 'north', 'west', 'east'.
                poi_type (str): The type of POI to query (must be a key in POI_TYPE_CONFIG).
                max_retries (int): Maximum number of retry attempts. Default is 3.
            Returns:
                dict: The JSON response from the Overpass API containing POI data.
            Raises:
                ValueError: If poi_type is not in POI_TYPE_CONFIG.
                ConnectionError: If all API instances and retries fail.
         """
        if poi_type not in POI_TYPE_CONFIG:
            raise ValueError(f"Unknown POI type: {poi_type}. Must be one of {list(POI_TYPE_CONFIG.keys())}")
        
        config = POI_TYPE_CONFIG[poi_type]
        query_pattern = config["query"]
        # Format the query pattern with bounding box coordinates
        formatted_query = query_pattern.format(
            south=bbox['south'],
            west=bbox['west'],
            north=bbox['north'],
            east=bbox['east']
        )
        
        overpass_query = f"""
        [out:json][timeout:60];
        (
        {formatted_query}
        );
        out center;
        """
        
        last_error = None
        
        # Try each Overpass API instance
        for overpass_url in self.overpass_urls:
            # Retry logic with exponential backoff
            for attempt in range(max_retries):
                try:
                    # Increase timeout for each retry attempt
                    timeout = 45 + (attempt * 15)  # 45s, 60s, 75s
                    
                    response = requests.post(
                        overpass_url, 
                        data={"data": overpass_query}, 
                        timeout=timeout
                    )
                    response.raise_for_status()
                    return response.json()
                    
                except requests.exceptions.Timeout:
                    last_error = TimeoutError(f"Overpass API request timed out after {timeout}s (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        # Exponential backoff: wait 2^attempt seconds
                        wait_time = 2 ** attempt
                        time.sleep(wait_time)
                        continue
                    else:
                        # Try next API instance
                        break
                        
                except requests.exceptions.HTTPError as e:
                    status_code = e.response.status_code
                    if status_code == 429:
                        last_error = ConnectionError("Overpass API rate limit exceeded.")
                        # Wait longer for rate limit, then try next instance
                        if attempt < max_retries - 1:
                            time.sleep(5)
                            continue
                        break
                    elif status_code == 400: 
                        last_error = ValueError(f"Bad request to Overpass API: {str(e)}")
                        # Don't retry bad requests
                        break
                    elif status_code >= 500 and status_code < 600:
                        last_error = ConnectionError(f"Overpass API server error: {str(e)}")
                        if attempt < max_retries - 1:
                            time.sleep(2 ** attempt)
                            continue
                        break
                    else: 
                        last_error = ConnectionError(f"Overpass API HTTP error {status_code}: {str(e)}")
                        break
                        
                except requests.exceptions.JSONDecodeError as e:
                    last_error = ValueError(f"Invalid JSON response from Overpass API: {str(e)}")
                    # Don't retry JSON decode errors
                    break
                    
                except requests.exceptions.ConnectionError as e:
                    last_error = ConnectionError(f"Overpass API connection error: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    break
                    
                except requests.exceptions.RequestException as e:
                    last_error = ConnectionError(f"Overpass API request failed: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    break
        
        # All attempts failed
        raise last_error if last_error else ConnectionError("Failed to query Overpass API after all retry attempts.")

    def query_all_poi_types(self, bbox: dict, delay_seconds: float = 0.75, max_distance_to_route_km: float = 1.0, selected_poi_types: Optional[List[str]] = None, progress_callback: Optional[Callable[[str, int, int], None]] = None, batch_callback: Optional[Callable[[str, List[POI]], None]] = None, deduplication_radius_km: float = 1.0, poi_settings: Optional[Dict[str, Dict[str, float]]] = None) -> List[POI]:
        """
        Query all POI types sequentially to avoid Overpass API timeouts.
            Args:
                bbox (dict): A dictionary representing the bounding box with keys 'south', 'north', 'west', 'east'.
                delay_seconds (float): Delay in seconds between queries. Default is 0.75 seconds.
                max_distance_to_route_km (float): Maximum distance in kilometers from the route to include a POI. Default is 1.0 km.
                selected_poi_types (Optional[List[str]]): List of POI types to query. If None, queries all types.
                progress_callback (callable): Optional callback function(poi_type: str, current: int, total: int) called for each POI type.
                deduplication_radius_km (float): Radius in kilometers for deduplication. Default is 1.0 km. Used as fallback if poi_settings not provided.
                poi_settings (Optional[Dict[str, Dict[str, float]]]): Dictionary mapping POI type to settings dict with 'max_deviation_km' and 'deduplication_radius_km'.
            Returns:
                List[POI]: A list of all filtered POIs from all types, sorted by distance along route.
        """
        all_pois = []
        # Use selected POI types if provided, otherwise use all types
        if selected_poi_types:
            # Validate that all selected types exist
            invalid_types = [t for t in selected_poi_types if t not in POI_TYPE_CONFIG]
            if invalid_types:
                raise ValueError(f"Unknown POI types: {invalid_types}. Must be one of {list(POI_TYPE_CONFIG.keys())}")
            poi_types = selected_poi_types
        else:
            poi_types = list(POI_TYPE_CONFIG.keys())
        total_types = len(poi_types)
        
        for index, poi_type in enumerate(poi_types, start=1):
            try:
                # Report progress
                if progress_callback:
                    progress_callback(poi_type, index, total_types)
                
                # Get settings for this POI type (use per-POI settings if available, otherwise fallback to defaults)
                if poi_settings and poi_type in poi_settings:
                    poi_max_distance = poi_settings[poi_type].get('max_deviation_km', max_distance_to_route_km)
                else:
                    poi_max_distance = max_distance_to_route_km
                
                # Query this POI type
                overpass_data = self.query_poi_type(bbox, poi_type)
                
                # Filter and add POI type information
                filtered_pois = self.filter_pois(overpass_data, poi_type, poi_max_distance)
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"POI type '{poi_type}': Found {len(overpass_data.get('elements', []))} raw elements, filtered to {len(filtered_pois)} within {poi_max_distance}km of route")
                
                # Apply deduplication for this POI type (with per-POI-type settings if available)
                deduplicated_pois = self.deduplicate_pois(filtered_pois, deduplication_radius_km, poi_settings)
                logger.info(f"POI type '{poi_type}': Deduplicated from {len(filtered_pois)} to {len(deduplicated_pois)} POIs")
                
                all_pois.extend(deduplicated_pois)
                
                # Send batch callback with deduplicated POIs for this type
                if batch_callback:
                    batch_callback(poi_type, deduplicated_pois)
                
                # Add delay between queries to prevent rate limiting (except after last query)
                if poi_type != poi_types[-1]:
                    time.sleep(delay_seconds)
                    
            except Exception as e:
                # Log error but continue with next POI type
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to query POI type '{poi_type}': {str(e)}. Continuing with other types.")
                continue
        
        # Sort all POIs by distance along route
        all_pois.sort(key=lambda poi: poi.distance_on_route)
        return all_pois

    def filter_pois(self, overpass_poi_data: dict, poi_type: str, max_distance_to_route_km: float = 1.0) -> List[POI]:
        """
        Filter POIs based on their distance to the route. 
            
            Args:
                overpass_poi_data (dict): The JSON response from the Overpass API containing POI data.
                poi_type (str): The type of POI being filtered (used for default name).
                max_distance_to_route_km (float): Maximum distance in kilometers from the route to include a POI. Default is 1.0 km.
            Returns:
                List[POI]: A list of filtered POIs with their details and distances.
        """
        if poi_type not in POI_TYPE_CONFIG:
            raise ValueError(f"Unknown POI type: {poi_type}")
        
        default_name = POI_TYPE_CONFIG[poi_type]["default_name"]
        filtered_pois = []
        for element in overpass_poi_data.get("elements", []):
            # Process both nodes and ways
            # Nodes have direct lat/lon, ways have center point when using 'out center'
            lat = None
            lon = None
            
            if element.get("type") == "node":
                if "lat" in element and "lon" in element:
                    lat = element['lat']
                    lon = element['lon']
            elif element.get("type") == "way":
                # Ways have center coordinates when using 'out center'
                if "center" in element:
                    center = element["center"]
                    if "lat" in center and "lon" in center:
                        lat = center['lat']
                        lon = center['lon']
                # Fallback: try to get lat/lon directly (some APIs return it differently)
                elif "lat" in element and "lon" in element:
                    lat = element['lat']
                    lon = element['lon']
            
            if lat is None or lon is None:
                continue
                
            try:
                poi_point = RoutePoint(lat=lat, lon=lon)
                # find the nearest point on route relative to the poi
                nearest_point_on_route_index = self.route_calculator.find_nearest_route_point_index(self.route, poi_point)
                nearest_route_point = self.route.points[nearest_point_on_route_index]
                # calculate direct distance to route
                distance_to_route_km = self.route_calculator.haversine_distance(poi_point, nearest_route_point)
                # only include poi if within max distance
                if distance_to_route_km <= max_distance_to_route_km:
                    distance_along_route = self.route_calculator.calculate_distance_on_route(self.route, nearest_route_point)
                    tags = element.get("tags", {})
                    name = tags.get("name")
                    
                    # Extract additional information from tags
                    opening_hours = tags.get("opening_hours")
                    url = tags.get("website") or tags.get("url")
                    
                    # Extract importance indicators
                    brand = tags.get("brand")
                    operator = tags.get("operator")
                    wikipedia = tags.get("wikipedia")
                    wikidata = tags.get("wikidata")
                    
                    # Extract price range for camping/hotels
                    price_range = None
                    if poi_type == "camping_hotels":
                        price_range = self.extract_price_range(tags)
                    
                    # Generate Google Maps link
                    google_maps_link = f"https://www.google.com/maps?q={lat},{lon}"
                    
                    poi = POI(
                        lat=lat,
                        lon=lon,
                        name=name if name else default_name,
                        distance_to_route=distance_to_route_km,
                        distance_on_route=distance_along_route,
                        poi_type=poi_type,
                        opening_hours=opening_hours,
                        url=url,
                        google_maps_link=google_maps_link,
                        price_range=price_range,
                        brand=brand,
                        operator=operator,
                        wikipedia=wikipedia,
                        wikidata=wikidata
                    )
                    filtered_pois.append(poi)
            except (KeyError, IndexError, ValueError) as e:
                # Skip elements that can't be processed
                continue
        # sort the pois by distance along the route
        filtered_pois.sort(key=lambda poi: poi.distance_on_route)
        return filtered_pois
    
    def extract_price_range(self, tags: dict) -> Optional[str]:
        """
        Extract and format price range from OSM tags.
        Checks for common price-related tags: fee, charge, price, fee:yes/no, etc.
        Also extracts per-person, per-night, per-tent, per-car pricing.
        Provides accommodation type-based indicators when explicit pricing is not available.
            Args:
                tags (dict): OSM tags dictionary.
            Returns:
                Optional[str]: Formatted price range string (e.g., '€15-25 per night', '€10 per person', 'Free', 'Budget') or None.
        """
        import re
        
        # Helper function to extract currency symbol and normalize
        def extract_currency_and_amount(price_str: str) -> tuple:
            """Extract currency symbol and numeric amount from price string."""
            # Common currency symbols
            currency_match = re.search(r'[€$£¥]', price_str)
            currency = currency_match.group(0) if currency_match else '€'
            
            # Extract numbers
            nums = re.findall(r'\d+(?:\.\d+)?', price_str)
            return currency, nums
        
        # Helper function to format price with currency
        def format_price(amount: str, currency: str = '€', unit: str = '') -> str:
            """Format price string with currency and optional unit."""
            unit_str = f" {unit}" if unit else ""
            try:
                # Try to format as integer if it's a whole number
                if '.' in amount:
                    return f"{currency}{amount}{unit_str}"
                else:
                    return f"{currency}{int(float(amount))}{unit_str}"
            except (ValueError, TypeError):
                return f"{currency}{amount}{unit_str}"
        
        # Priority 1: Check for per-unit pricing (most specific)
        per_unit_prices = []
        
        # Per person pricing
        for tag_key in ['fee:per_person', 'charge:per_person', 'price:per_person']:
            if tag_key in tags:
                price_val = str(tags[tag_key]).strip()
                currency, nums = extract_currency_and_amount(price_val)
                if nums:
                    per_unit_prices.append(format_price(nums[0], currency, "per person"))
        
        # Per night pricing
        for tag_key in ['fee:per_night', 'charge:per_night', 'price:per_night']:
            if tag_key in tags:
                price_val = str(tags[tag_key]).strip()
                currency, nums = extract_currency_and_amount(price_val)
                if nums:
                    per_unit_prices.append(format_price(nums[0], currency, "per night"))
        
        # Per tent pricing (camping)
        for tag_key in ['fee:per_tent', 'charge:per_tent', 'price:per_tent']:
            if tag_key in tags:
                price_val = str(tags[tag_key]).strip()
                currency, nums = extract_currency_and_amount(price_val)
                if nums:
                    per_unit_prices.append(format_price(nums[0], currency, "per tent"))
        
        # Per car pricing (camping)
        for tag_key in ['fee:per_car', 'charge:per_car', 'price:per_car']:
            if tag_key in tags:
                price_val = str(tags[tag_key]).strip()
                currency, nums = extract_currency_and_amount(price_val)
                if nums:
                    per_unit_prices.append(format_price(nums[0], currency, "per car"))
        
        if per_unit_prices:
            return ", ".join(per_unit_prices)
        
        # Priority 2: Check for explicit price tags with amounts
        price = tags.get("price") or tags.get("fee") or tags.get("charge")
        if price:
            price_str = str(price).strip()
            fee_lower = price_str.lower()
            
            # Check for free indicators first
            if fee_lower in ['no', 'free', 'gratis', '0']:
                return "Free"
            
            # Skip "yes" as it's not a price amount
            if fee_lower == 'yes':
                pass  # Will be handled later
            else:
                try:
                    currency, nums = extract_currency_and_amount(price_str)
                    
                    # Check if it's a range (e.g., "10-20" or "€10-€20")
                    if '-' in price_str and len(nums) >= 2:
                        return f"{currency}{nums[0]}-{nums[1]}"
                    elif len(nums) >= 1:
                        # Single price - try to infer unit based on tourism type
                        tourism_type = tags.get("tourism", "").lower()
                        unit = "per night" if tourism_type in ['hotel', 'hostel', 'guest_house', 'motel', 'camp_site', 'camping'] else ""
                        return format_price(nums[0], currency, unit)
                    else:
                        # Return as-is if already formatted
                        return price_str
                except (ValueError, AttributeError, IndexError):
                    # If parsing fails, return as-is
                    return price_str
        
        # Priority 3: Check for tourism-specific tags and accommodation type indicators
        tourism_type = tags.get("tourism", "").lower()
        
        # For camping sites
        if tourism_type in ['camp_site', 'camping']:
            fee = tags.get("fee")
            if fee:
                fee_str = str(fee).lower()
                if fee_str in ['no', 'free']:
                    return "Free"
                elif fee_str == 'yes':
                    return "Fee required"
            
            # Check for price_range tag
            price_range = tags.get("price_range") or tags.get("price:range")
            if price_range:
                currency, nums = extract_currency_and_amount(str(price_range))
                if nums and len(nums) >= 2:
                    return f"{currency}{nums[0]}-{nums[1]} per tent"
                elif nums:
                    return format_price(nums[0], currency, "per tent")
                return str(price_range)
        
        # For accommodation (hotels, hostels, etc.)
        if tourism_type in ['hotel', 'hostel', 'guest_house', 'motel']:
            # Check for explicit price_range tag
            price_range = tags.get("price_range") or tags.get("price:range")
            if price_range:
                currency, nums = extract_currency_and_amount(str(price_range))
                if nums and len(nums) >= 2:
                    return f"{currency}{nums[0]}-{nums[1]} per night"
                elif nums:
                    return format_price(nums[0], currency, "per night")
                return str(price_range)
            
            # Check for budget indicators
            budget = tags.get("budget")
            if budget:
                budget_str = str(budget).lower()
                if budget_str == 'yes':
                    return "Budget"
            
            # Check for stars rating (hotels) - can indicate price range
            stars = tags.get("stars")
            if stars:
                try:
                    star_count = int(float(stars))
                    if star_count >= 4:
                        return "Expensive"
                    elif star_count >= 3:
                        return "Mid-range"
                    elif star_count >= 1:
                        return "Budget"
                except (ValueError, TypeError):
                    pass
            
            # Use accommodation type as price indicator when no explicit pricing
            if tourism_type == 'hostel':
                return "Budget"
            elif tourism_type == 'motel':
                return "Mid-range"
            # Hotels vary widely, so don't provide default indicator
        
        # Priority 4: Check for fee indicators (yes/no)
        fee = tags.get("fee")
        if fee:
            fee_str = str(fee).lower()
            if fee_str in ['no', 'free', 'gratis']:
                return "Free"
            elif fee_str == 'yes':
                return "Fee required"
        
        return None
    
    def is_24_7(self, opening_hours: Optional[str]) -> bool:
        """
        Check if opening hours indicate 24/7 availability.
            Args:
                opening_hours (Optional[str]): Opening hours string from OSM.
            Returns:
                bool: True if the POI appears to be open 24/7.
        """
        if not opening_hours:
            return False
        
        opening_hours_lower = opening_hours.lower()
        # Check for common 24/7 patterns
        patterns = ["24/7", "24/24", "always open", "mo-su 00:00-24:00", "24 hours", "24h"]
        return any(pattern in opening_hours_lower for pattern in patterns)
    
    def calculate_opening_hours_duration(self, opening_hours: Optional[str]) -> float:
        """
        Calculate total hours per week from opening hours string.
        Uses heuristics to parse common OSM opening_hours patterns.
            Args:
                opening_hours (Optional[str]): Opening hours string from OSM.
            Returns:
                float: Total hours per week (0-168). Returns 0 if missing or unparseable.
        """
        if not opening_hours:
            return 0.0
        
        opening_hours_lower = opening_hours.lower().strip()
        
        # Check for 24/7 patterns first
        if self.is_24_7(opening_hours):
            return 168.0  # 24 hours × 7 days
        
        # Try to parse simple day range patterns like "Mo-Fr 09:00-17:00"
        import re
        
        # Pattern: Mo-Fr 09:00-17:00 or Mo-Su 10:00-20:00
        # Match day ranges and time ranges
        day_patterns = {
            'mo': 1, 'tu': 2, 'we': 3, 'th': 4, 'fr': 5, 'sa': 6, 'su': 7
        }
        
        # Try to find day ranges with time ranges
        # Pattern: "Mo-Fr 09:00-17:00" or "Mo-Su 10:00-22:00"
        simple_pattern = r'([a-z]{2})-([a-z]{2})\s+(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})'
        match = re.search(simple_pattern, opening_hours_lower)
        
        if match:
            try:
                start_day = day_patterns.get(match.group(1)[:2], 0)
                end_day = day_patterns.get(match.group(2)[:2], 0)
                start_hour = int(match.group(3))
                start_min = int(match.group(4))
                end_hour = int(match.group(5))
                end_min = int(match.group(6))
                
                if start_day > 0 and end_day > 0:
                    # Calculate number of days
                    if end_day >= start_day:
                        num_days = end_day - start_day + 1
                    else:
                        # Wrap around week (e.g., Fr-Mo)
                        num_days = (7 - start_day + 1) + end_day
                    
                    # Calculate hours per day
                    start_time = start_hour + start_min / 60.0
                    end_time = end_hour + end_min / 60.0
                    
                    # Handle overnight hours (e.g., 22:00-02:00)
                    if end_time < start_time:
                        hours_per_day = (24.0 - start_time) + end_time
                    else:
                        hours_per_day = end_time - start_time
                    
                    return num_days * hours_per_day
            except (ValueError, IndexError):
                pass
        
        # Try to find multiple day ranges (e.g., "Mo-Fr 09:00-17:00; Sa 10:00-14:00")
        # Split by semicolon and sum up hours
        parts = opening_hours_lower.split(';')
        total_hours = 0.0
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Try simple pattern on each part
            match = re.search(simple_pattern, part)
            if match:
                try:
                    start_day = day_patterns.get(match.group(1)[:2], 0)
                    end_day = day_patterns.get(match.group(2)[:2], 0)
                    start_hour = int(match.group(3))
                    start_min = int(match.group(4))
                    end_hour = int(match.group(5))
                    end_min = int(match.group(6))
                    
                    if start_day > 0 and end_day > 0:
                        if end_day >= start_day:
                            num_days = end_day - start_day + 1
                        else:
                            num_days = (7 - start_day + 1) + end_day
                        
                        start_time = start_hour + start_min / 60.0
                        end_time = end_hour + end_min / 60.0
                        
                        if end_time < start_time:
                            hours_per_day = (24.0 - start_time) + end_time
                        else:
                            hours_per_day = end_time - start_time
                        
                        total_hours += num_days * hours_per_day
                except (ValueError, IndexError):
                    continue
        
        # If we found any hours, return them
        if total_hours > 0:
            return min(total_hours, 168.0)  # Cap at 168 hours/week
        
        # If we can't parse it, return 0
        return 0.0
    
    def deduplicate_pois(self, pois: List[POI], deduplication_radius_km: float = 1.0, poi_settings: Optional[Dict[str, Dict[str, float]]] = None) -> List[POI]:
        """
        Remove duplicate POIs within specified radius, preferring 24/7 options on-route.
        For toilets, groceries, and bakeries: keep only one POI within the specified radius.
        Always keep all water fountains.
            Args:
                pois (List[POI]): List of POIs to deduplicate.
                deduplication_radius_km (float): Radius in kilometers for deduplication. Default is 1.0 km. Used as fallback if poi_settings not provided.
                poi_settings (Optional[Dict[str, Dict[str, float]]]): Dictionary mapping POI type to settings dict with 'deduplication_radius_km'.
            Returns:
                List[POI]: Deduplicated list of POIs.
        """
        # Types that should be deduplicated
        deduplicate_types = {"public_toilets", "grocery_stores", "bakeries", "water_fountains", "bicycle_shops", "camping_hotels", "gas_stations", "sport_areas"}
        
        # Group POIs by type
        pois_by_type: Dict[str, List[POI]] = {}
        for poi in pois:
            if poi.poi_type not in pois_by_type:
                pois_by_type[poi.poi_type] = []
            pois_by_type[poi.poi_type].append(poi)
        
        result = []
        
        for poi_type, type_pois in pois_by_type.items():
            # For types that need deduplication
            if poi_type in deduplicate_types:
                # Get deduplication radius for this POI type
                if poi_settings and poi_type in poi_settings:
                    poi_dedup_radius = poi_settings[poi_type].get('deduplication_radius_km', deduplication_radius_km)
                else:
                    poi_dedup_radius = deduplication_radius_km
                
                # Sort by preference: closest to route, longest opening hours, then importance indicators
                type_pois.sort(key=lambda p: (
                    p.distance_to_route,  # Closest first (primary)
                    -self.calculate_opening_hours_duration(p.opening_hours),  # Longest first (secondary, negative for descending)
                    not bool(p.brand or p.operator),  # Prefer branded/chain POIs (tertiary)
                    not bool(p.wikipedia or p.wikidata),  # Prefer notable POIs (quaternary)
                    not bool(p.url),  # Prefer POIs with URLs (quinary)
                    not bool(p.name)  # Prefer named POIs (senary)
                ))
                
                # Keep POIs that are not within the deduplication radius of a better POI
                kept_pois = []
                for poi in type_pois:
                    # Check if this POI is within the deduplication radius of any already kept POI
                    too_close = False
                    for kept_poi in kept_pois:
                        distance_km = haversine((poi.lat, poi.lon), (kept_poi.lat, kept_poi.lon))
                        if distance_km < poi_dedup_radius:
                            too_close = True
                            break
                    
                    if not too_close:
                        kept_pois.append(poi)
                
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Deduplication for '{poi_type}': {len(type_pois)} POIs before, {len(kept_pois)} after (radius: {poi_dedup_radius}km)")
                result.extend(kept_pois)
            else:
                # For other types, keep all
                result.extend(type_pois)
        
        return result
    
    