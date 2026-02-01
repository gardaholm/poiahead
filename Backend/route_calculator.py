from Backend.route_storage import RoutePoint, Route
from haversine import haversine

class RouteCalculator:
    """
    Helpers for route calculations such as distance an nearest point. 
    """
    def haversine_distance(self, point1: RoutePoint, point2: RoutePoint) -> float:
        """
        Calculate the Haversine distance between two RoutePoints with the harversine libary.
        Args: 
            point1 (RoutePoint): The first route point.
            point2 (RoutePoint): The second route point. 
        Returns: 
            float: Distance in kilometers.
        """
        return haversine((point1.lat, point1.lon), (point2.lat, point2.lon))

    def find_nearest_route_point_index(self, route: Route, poi_point: RoutePoint) -> int:
        """
        Find the nearest point on the route to the poi point.
        Args:
            route (Route): Route object containing route points.
            poi_point (RoutePoint): The target point.
        Returns:
            int: Index of the nearest route point
        """
        nearest_index = route.rtree.nearest((poi_point.lon, poi_point.lat, poi_point.lon, poi_point.lat), 1)
        return next(nearest_index)
    
    def calculate_distance_on_route(self, route: Route, point: RoutePoint) -> float:
        """
        Calculate the distance along the route to the specified point.
        Args:
            route (Route): Route object containing route points.
            point (RoutePoint): The target point.
        Returns: 
            float: Distance on route in kilometers.
        """
        index = self.find_nearest_route_point_index(route, point)
        distance = 0.0
        for i in range(index):
            distance += self.haversine_distance(route.points[i], route.points[i + 1])
        return distance
    
