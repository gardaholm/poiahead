import gpxpy
from Backend.route_storage import RoutePoint
from typing import List, Tuple
from haversine import haversine

class GPXParser:
    """
    A class to parse GPX data and extract route points.

    Attributes: 
        gpx_data (bytes): The GPX data in bytes format.

    Methods:
        parse() -> List[RoutePoint]:
            Parse the GPX data and extract route points.

    """
    def __init__(self, gpx_data: bytes):
        self.gpx_data = gpx_data

    def parse(self) -> List[RoutePoint]:
        """
        Parse the GPX data and extract route points.

            Args: 
                gpx_data (bytes): The GPX data in bytes format.
    
            Returns:
                List[RoutePoint]: A list of RoutePoint objects extracted from the GPX data. 
        """
        try:
            # Try to decode as UTF-8, with fallback handling
            try:
                gpx_text = self.gpx_data.decode('utf-8')
            except UnicodeDecodeError as e:
                raise ValueError(f"File encoding error: The file is not valid UTF-8. {str(e)}")
            
            gpx = gpxpy.parse(gpx_text)
            route_points = []

            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        route_points.append(RoutePoint(lat=point.latitude, lon=point.longitude))
            
            if len(route_points) == 0:
                raise ValueError("The GPX file does not contain any track points. Please ensure your GPX file has track data.")
            
            return route_points
        
        except ValueError:
            # Re-raise ValueError as-is (already has proper error message)
            raise
        except Exception as e:
            raise ValueError(f"Failed to parse GPX data: {str(e)}")

    def parse_with_elevation(self) -> Tuple[List[RoutePoint], List[dict], float]:
        """
        Parse GPX data and extract route points with elevation profile.

        Returns:
            Tuple containing:
                - List[RoutePoint]: Route points
                - List[dict]: Elevation profile with {distance, elevation} for each point
                - float: Total route distance in km
        """
        try:
            try:
                gpx_text = self.gpx_data.decode('utf-8')
            except UnicodeDecodeError as e:
                raise ValueError(f"File encoding error: The file is not valid UTF-8. {str(e)}")

            gpx = gpxpy.parse(gpx_text)
            route_points = []
            elevation_profile = []
            cumulative_distance = 0.0
            prev_point = None

            for track in gpx.tracks:
                for segment in track.segments:
                    for point in segment.points:
                        route_points.append(RoutePoint(lat=point.latitude, lon=point.longitude))

                        # Calculate cumulative distance
                        if prev_point is not None:
                            dist = haversine(
                                (prev_point.latitude, prev_point.longitude),
                                (point.latitude, point.longitude)
                            )
                            cumulative_distance += dist

                        # Add elevation data point
                        elevation_profile.append({
                            "distance": round(cumulative_distance, 3),
                            "elevation": point.elevation if point.elevation is not None else 0
                        })

                        prev_point = point

            if len(route_points) == 0:
                raise ValueError("The GPX file does not contain any track points.")

            return route_points, elevation_profile, cumulative_distance

        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to parse GPX data: {str(e)}")