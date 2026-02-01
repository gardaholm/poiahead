import gpxpy
from xml.etree import ElementTree
from typing import List, Dict, Optional
from Backend.route_storage import Route, RoutePoint
from Backend.poi import POI
from Backend.route_calculator import RouteCalculator

# Mapping from POI types to GPX waypoint symbols
# Using simple names that work across Garmin Connect, RideWithGPS, etc.
# Known working: Restroom, Food, Water, Fuel
POI_TYPE_TO_SYMBOL = {
    'gas_stations': 'Fuel',
    'bakeries': 'Food',
    'grocery_stores': 'Food',
    'public_toilets': 'Restroom',
    'water_fountains': 'Water',
    'bicycle_shops': 'Bike Trail',
    'bicycle_vending': 'Bike Trail',
    'vending_machines': 'Food',
    'camping_hotels': 'Campground',
    'sport_areas': 'Stadium'
}

# Mapping from POI types to GPX waypoint types (full names for type field)
POI_TYPE_TO_TYPE = {
    'gas_stations': 'Gas Station',
    'bakeries': 'Bakery',
    'grocery_stores': 'Grocery Store',
    'public_toilets': 'Toilet',
    'water_fountains': 'Water Fountain',
    'bicycle_shops': 'Bicycle Shop',
    'bicycle_vending': 'Bicycle Vending',
    'vending_machines': 'Vending Machine',
    'camping_hotels': 'Accommodation',
    'sport_areas': 'Sport Area'
}

# Short type names for waypoint name field (to fit in 15 char limit with km)
POI_TYPE_SHORT = {
    'gas_stations': 'Gas',
    'bakeries': 'Bakery',
    'grocery_stores': 'Shop',
    'public_toilets': 'WC',
    'water_fountains': 'Water',
    'bicycle_shops': 'Bike',
    'bicycle_vending': 'BikeV',
    'vending_machines': 'Vend',
    'camping_hotels': 'Camp',
    'sport_areas': 'Sport'
}

def generate_gpx_waypoint(poi: POI, route: Route, route_calculator: RouteCalculator, mode: str = 'garmin') -> gpxpy.gpx.GPXWaypoint:
    """
    Generate a GPX waypoint from a POI.

    Args:
        poi (POI): The POI to convert to a waypoint.
        route (Route): The route object for finding nearest track point.
        route_calculator (RouteCalculator): Calculator for route operations.
        mode (str): 'garmin' to place waypoint on track, 'normal' to use original POI location.

    Returns:
        gpxpy.gpx.GPXWaypoint: The generated waypoint.
    """
    # Get symbol and type from mappings
    symbol = POI_TYPE_TO_SYMBOL.get(poi.poi_type, 'Flag')
    waypoint_type = POI_TYPE_TO_TYPE.get(poi.poi_type, 'Waypoint')
    type_short = POI_TYPE_SHORT.get(poi.poi_type, 'POI')

    # Build name: "42 WC Name" format (max 15 chars for Garmin)
    km = int(round(poi.distance_on_route))
    prefix = f"{km} {type_short} "
    remaining_chars = 15 - len(prefix)
    if remaining_chars > 0:
        truncated_name = poi.name[:remaining_chars]
        name = f"{prefix}{truncated_name}".strip()
    else:
        name = f"{km} {type_short}"[:15]
    
    # Determine coordinates based on mode
    if mode == 'garmin':
        # Find nearest point on route
        poi_point = RoutePoint(lat=poi.lat, lon=poi.lon)
        nearest_index = route_calculator.find_nearest_route_point_index(route, poi_point)
        nearest_route_point = route.points[nearest_index]
        lat = nearest_route_point.lat
        lon = nearest_route_point.lon
    else:
        # Use original POI location
        lat = poi.lat
        lon = poi.lon
    
    # Create waypoint
    w = gpxpy.gpx.GPXWaypoint(
        latitude=lat,
        longitude=lon,
        symbol=symbol,
        name=name,
        type=waypoint_type
    )
    
    # Add link if URL exists
    if poi.url:
        w.link = poi.url
    
    # Build comment with key info: km, category, full name, opening hours
    comment_parts = []
    comment_parts.append(f"km {poi.distance_on_route:.1f}")
    comment_parts.append(waypoint_type)
    comment_parts.append(poi.name)
    if poi.opening_hours:
        comment_parts.append(poi.opening_hours)
    w.comment = " | ".join(comment_parts)

    # Build description with distance from route, price, brand/operator
    description_parts = []
    distance_m = int(poi.distance_to_route * 1000)
    if distance_m > 1500:
        distance_str = f"{poi.distance_to_route:.1f} km"
    else:
        distance_str = f"{distance_m} m"
    description_parts.append(f"Away: {distance_str}")

    if poi.brand:
        description_parts.append(f"Brand: {poi.brand}")
    elif poi.operator:
        description_parts.append(f"Operator: {poi.operator}")

    if poi.price_range:
        description_parts.append(f"Price: {poi.price_range}")

    w.description = " | ".join(description_parts)

    return w

def generate_gpx_with_waypoints(
    gpx_data: bytes,
    route: Route,
    pois: List[POI],
    route_calculator: RouteCalculator,
    mode: str = 'garmin'
) -> str:
    """
    Generate a GPX file with waypoints added from POIs.
    
    Args:
        gpx_data (bytes): Original GPX file data.
        route (Route): The route object.
        pois (List[POI]): List of POIs to add as waypoints.
        route_calculator (RouteCalculator): Calculator for route operations.
        mode (str): 'garmin' to place waypoints on track, 'normal' to use original POI locations.
        
    Returns:
        str: GPX XML string with waypoints added.
    """
    # Parse original GPX file
    gpx = gpxpy.parse(gpx_data.decode('utf-8'))
    
    # Add osmand namespace for compatibility
    if 'osmand' not in gpx.nsmap:
        gpx.nsmap['osmand'] = "https://osmand.net/docs/technical/osmand-file-formats/osmand-gpx"
    
    # Generate waypoints for each POI
    for poi in pois:
        waypoint = generate_gpx_waypoint(poi, route, route_calculator, mode=mode)
        gpx.waypoints.append(waypoint)
    
    return gpx.to_xml()

