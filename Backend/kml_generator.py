from xml.etree import ElementTree as ET
from typing import List, Optional
import re
from Backend.route_storage import Route, RoutePoint
from Backend.poi import POI

# Mapping from POI types to KML icon styles
POI_TYPE_TO_ICON = {
    'gas_stations': {'color': 'ff4444ff', 'icon': 'http://maps.google.com/mapfiles/kml/shapes/gas_stations.png'},
    'bakeries': {'color': 'ff74a5d4', 'icon': 'http://maps.google.com/mapfiles/kml/shapes/dining.png'},
    'grocery_stores': {'color': 'ff27ae60', 'icon': 'http://maps.google.com/mapfiles/kml/shapes/grocery.png'},
    'public_toilets': {'color': 'ffe2904a', 'icon': 'http://maps.google.com/mapfiles/kml/shapes/toilets.png'},
    'water_fountains': {'color': 'ffdb9834', 'icon': 'http://maps.google.com/mapfiles/kml/shapes/water.png'},
    'bicycle_shops': {'color': 'ff503e2c', 'icon': 'http://maps.google.com/mapfiles/kml/shapes/cycling.png'},
    'bicycle_vending': {'color': 'ffb6599b', 'icon': 'http://maps.google.com/mapfiles/kml/shapes/cycling.png'},
    'vending_machines': {'color': 'ff129cf3', 'icon': 'http://maps.google.com/mapfiles/kml/shapes/convenience.png'},
    'camping_hotels': {'color': 'ff85a016', 'icon': 'http://maps.google.com/mapfiles/kml/shapes/lodging.png'},
    'sport_areas': {'color': 'ffad448e', 'icon': 'http://maps.google.com/mapfiles/kml/shapes/play.png'}
}

# Mapping from POI types to display names
POI_TYPE_TO_NAME = {
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

# Short type names for KML placemark names
POI_TYPE_SHORT = {
    'gas_stations': 'Gas',
    'bakeries': 'Bakery',
    'grocery_stores': 'Shop',
    'public_toilets': 'WC',
    'water_fountains': 'Water',
    'bicycle_shops': 'Bike',
    'bicycle_vending': 'BikeV',
    'vending_machines': 'Vending',
    'camping_hotels': 'Camp',
    'sport_areas': 'Sport'
}


def shorten_opening_hours(opening_hours: Optional[str]) -> Optional[str]:
    """
    Shorten opening hours string for display in placemark name.

    Examples:
        "24/7" -> "24/7"
        "Mo-Su 00:00-24:00" -> "24/7"
        "Mo-Fr 08:00-20:00" -> "8-20"
        "Mo-Fr 09:00-18:00; Sa 10:00-14:00" -> "9-18"
    """
    if not opening_hours:
        return None

    hours_lower = opening_hours.lower().strip()

    # Check for 24/7 patterns
    if any(p in hours_lower for p in ['24/7', '24/24', 'always open', '00:00-24:00', '24 hours']):
        return '24/7'

    # Try to extract simple time range (e.g., "08:00-20:00" -> "8-20")
    time_pattern = r'(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})'
    match = re.search(time_pattern, opening_hours)
    if match:
        start_h = int(match.group(1))
        end_h = int(match.group(3))
        return f"{start_h}-{end_h}"

    # If too complex, return None (don't show)
    return None


def generate_poi_name(poi: POI) -> str:
    """
    Generate POI name in format: KMkm - Type - Name (Hours)

    Example: "42km - Gas - Shell (24/7)"
    """
    # Distance in km (rounded to integer)
    km = int(round(poi.distance_on_route))

    # Short type name
    type_short = POI_TYPE_SHORT.get(poi.poi_type, 'POI')

    # POI name (truncate if too long)
    name = poi.name if len(poi.name) <= 20 else poi.name[:17] + '...'

    # Build base name
    base_name = f"{km}km - {type_short} - {name}"

    # Add shortened opening hours if available
    short_hours = shorten_opening_hours(poi.opening_hours)
    if short_hours:
        return f"{base_name} ({short_hours})"

    return base_name


def generate_kml_with_waypoints(
    route: Route,
    pois: List[POI],
    route_name: str = "Route"
) -> str:
    """
    Generate a KML file with route and POI placemarks.

    Args:
        route (Route): The route object with points.
        pois (List[POI]): List of POIs to add as placemarks.
        route_name (str): Name for the route.

    Returns:
        str: KML XML string.
    """
    # Create KML root
    kml = ET.Element('kml', xmlns='http://www.opengis.net/kml/2.2')
    document = ET.SubElement(kml, 'Document')

    # Add document name
    name = ET.SubElement(document, 'name')
    name.text = f"{route_name} with POIs"

    # Add styles for each POI type
    for poi_type, style_info in POI_TYPE_TO_ICON.items():
        style = ET.SubElement(document, 'Style', id=f'style_{poi_type}')
        icon_style = ET.SubElement(style, 'IconStyle')
        color = ET.SubElement(icon_style, 'color')
        color.text = style_info['color']
        scale = ET.SubElement(icon_style, 'scale')
        scale.text = '1.0'
        icon = ET.SubElement(icon_style, 'Icon')
        href = ET.SubElement(icon, 'href')
        href.text = style_info['icon']

    # Add route style
    route_style = ET.SubElement(document, 'Style', id='route_style')
    line_style = ET.SubElement(route_style, 'LineStyle')
    line_color = ET.SubElement(line_style, 'color')
    line_color.text = 'ff00b87f'  # Green color (AABBGGRR format)
    line_width = ET.SubElement(line_style, 'width')
    line_width.text = '4'

    # Add route as LineString
    route_folder = ET.SubElement(document, 'Folder')
    route_folder_name = ET.SubElement(route_folder, 'name')
    route_folder_name.text = 'Route'

    route_placemark = ET.SubElement(route_folder, 'Placemark')
    route_pm_name = ET.SubElement(route_placemark, 'name')
    route_pm_name.text = route_name
    style_url = ET.SubElement(route_placemark, 'styleUrl')
    style_url.text = '#route_style'

    line_string = ET.SubElement(route_placemark, 'LineString')
    tessellate = ET.SubElement(line_string, 'tessellate')
    tessellate.text = '1'
    coordinates = ET.SubElement(line_string, 'coordinates')

    # Build coordinates string (lon,lat,alt format for KML)
    coord_list = []
    for point in route.points:
        elevation = getattr(point, 'elevation', 0) or 0
        coord_list.append(f"{point.lon},{point.lat},{elevation}")
    coordinates.text = ' '.join(coord_list)

    # Add POIs folder
    if pois:
        poi_folder = ET.SubElement(document, 'Folder')
        poi_folder_name = ET.SubElement(poi_folder, 'name')
        poi_folder_name.text = 'Points of Interest'

        for poi in pois:
            placemark = ET.SubElement(poi_folder, 'Placemark')

            # Name in format: KM - Type - Name (Hours)
            pm_name = ET.SubElement(placemark, 'name')
            pm_name.text = generate_poi_name(poi)

            # Style
            pm_style = ET.SubElement(placemark, 'styleUrl')
            pm_style.text = f'#style_{poi.poi_type}' if poi.poi_type in POI_TYPE_TO_ICON else '#style_gas_stations'

            # Description with details
            description_parts = []
            type_name = POI_TYPE_TO_NAME.get(poi.poi_type, 'POI')
            description_parts.append(f"<b>Type:</b> {type_name}")

            distance_m = int(poi.distance_to_route * 1000)
            if distance_m > 1500:
                distance_str = f"{poi.distance_to_route:.1f} km"
            else:
                distance_str = f"{distance_m} m"
            description_parts.append(f"<b>Distance from route:</b> {distance_str}")

            if poi.opening_hours:
                description_parts.append(f"<b>Opening hours:</b> {poi.opening_hours}")

            if poi.price_range:
                description_parts.append(f"<b>Price:</b> {poi.price_range}")

            if poi.url:
                description_parts.append(f"<b>Website:</b> <a href=\"{poi.url}\">{poi.url}</a>")

            if poi.google_maps_link:
                description_parts.append(f"<a href=\"{poi.google_maps_link}\">Open in Google Maps</a>")

            pm_description = ET.SubElement(placemark, 'description')
            pm_description.text = '<br>'.join(description_parts)

            # Point coordinates
            point = ET.SubElement(placemark, 'Point')
            pm_coordinates = ET.SubElement(point, 'coordinates')
            pm_coordinates.text = f"{poi.lon},{poi.lat},0"

    # Generate XML string
    return ET.tostring(kml, encoding='unicode', xml_declaration=True)
