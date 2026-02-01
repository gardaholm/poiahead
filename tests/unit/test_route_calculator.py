from route_calculator import RouteCalculator
from route_storage import RoutePoint, RouteStorage

route_calculator = RouteCalculator()

def test_haversine_distance_1():
    """
    Test Backend Requirement 3a: Distance calculation between coordinates.
    
    Uses real-world distance Berlin-Paris (878.08 km) verified via luftlinie.org.
    """
    point1 = RoutePoint(lat=52.523403, lon=13.4114)  # Berlin
    point2 = RoutePoint(lat=48.856667, lon=2.350987)   # Paris
    distance = route_calculator.haversine_distance(point1, point2)
    assert round(distance, 2) == 878.08 # https://www.luftlinie.org/Berlin/Paris

def test_haversine_distance_2():
    """
    Test Backend Requirement 3a: Distance calculation between coordinates.
    
    Uses real-world distance LA-NYC (3935.75 km) verified via luftlinie.org.
    """
    point1 = RoutePoint(lat=34.052235, lon=-118.243683)  # Los Angeles
    point2 = RoutePoint(lat=40.712776, lon=-74.005974)   # New York
    distance = route_calculator.haversine_distance(point1, point2)
    assert round(distance, 2) == 3935.75 # https://www.luftlinie.org/Los-Angeles/New-York

def test_haversine_distance_same_point():
    """Test edge case: distance between identical points should be 0."""
    point1 = RoutePoint(lat=-5.123456, lon=42)
    point2 = RoutePoint(lat=-5.123456, lon=42)
    distance = route_calculator.haversine_distance(point1, point2)
    assert round(distance, 2) == 0.00


def test_find_nearest_route_point():
    """
    Test Backend Requirement 3b: Find nearest route point to given coordinate.
    """
    route_storage = RouteStorage()
    route_id = route_storage.store([
        RoutePoint(lat=0, lon=0),  
        RoutePoint(lat=1, lon=1), 
        RoutePoint(lat=2, lon=2),
        RoutePoint(lat=3, lon=3)])
    route = route_storage.get(route_id)

    target_point = RoutePoint(lat=1.1, lon=1.1)  
    nearest_index = route_calculator.find_nearest_route_point_index(route, target_point) # type: ignore
    assert nearest_index == 1  

def test_calculate_distance_on_route():
    """
    Test Backend Requirement 3a: Calculate cumulative distance along route.
    
    Verifies distance from start to Hamburg point (255.65 km).
    """
    route_storage = RouteStorage()
    route_id = route_storage.store([
        RoutePoint(lat=52.523403, lon=13.4114),  # Berlin
        RoutePoint(lat=53.553406, lon=9.992196),  # Hamburg
        RoutePoint(lat=52.37052, lon=9.73322)   # Hannover
    ])
    route = route_storage.get(route_id)

    distance = route_calculator.calculate_distance_on_route(route, route.points[1])  # type: ignore
    assert round(distance, 2) == 255.65  #https://www.luftlinie.org/Berlin,DEU/Hamburg,DEU

def test_find_nearest_route_point_first():
    """Test edge case: nearest point is the first route point."""
    route_storage = RouteStorage()
    route_id = route_storage.store([
        RoutePoint(lat=0, lon=0),
        RoutePoint(lat=1, lon=1),
        RoutePoint(lat=2, lon=2)])
    route = route_storage.get(route_id)
    target_point = RoutePoint(lat=-0.1, lon=-0.1)  
    nearest_index = route_calculator.find_nearest_route_point_index(route, target_point) # type: ignore
    assert nearest_index == 0
