from rtree import index
from overpass_client import OverpassClient, RoutePoint, Route, POI 
from route_storage import RouteStorage 
import pytest
import responses

def test_overpass_client_creation():
    """Test OverpassClient initialization with a valid route."""
    route_storage = RouteStorage()
    route_id = route_storage.store([RoutePoint(-2,-2), RoutePoint(-1,3), RoutePoint(2,2)])
    route = route_storage.get(route_id)
    o = OverpassClient(route) # type: ignore
    assert isinstance(o, OverpassClient)
    assert "http://overpass-api.de/api/interpreter" in o.overpass_urls

def test_get_route_bounding_box():
    """
    Test Overpass Requirement 1: BBox calculation < 1 second.
    
    Verifies correct bounding box calculation for route points.
    """
    route_storage = RouteStorage()
    route_id = route_storage.store([RoutePoint(-2,-2), RoutePoint(-1,3), RoutePoint(2,2)])
    route = route_storage.get(route_id)
    o = OverpassClient(route) # type: ignore
    bbox = o.get_route_bounding_box(buffer_km=0.0)
    assert bbox == {            
            "south": -2.0,
            "north": 2.0,
            "west": -2.0,
            "east": 3.0}
    
def test_filter_pois():
    """
    Test Overpass Requirement 3: POI filtering < 3 seconds.
    
    Filters POIs based on maximum distance from route.
    """
    route_storage = RouteStorage()
    route_id = route_storage.store([RoutePoint(0,0), RoutePoint(0,1), RoutePoint(1,1)])
    route = route_storage.get(route_id)
    o = OverpassClient(route) # type: ignore
    
    overpass_data = {
        "elements": [
            {"type": "node", "id": 1, "lat": 0.001, "lon": 0.001, "tags": {"amenity": "fuel", "name": "Gas Station 1"}},
            {"type": "node", "id": 2, "lat": 5.0, "lon": 5.0, "tags": {"amenity": "fuel", "name": "Gas Station 2"}},
        ]
    }
    
    filtered_pois = o.filter_pois(overpass_data, "gas_stations", max_distance_to_route_km=2.0)
    
    assert len(filtered_pois) == 1
    assert filtered_pois[0].lat == 0.001
    assert filtered_pois[0].lon == 0.001
    assert filtered_pois[0].name == "Gas Station 1"

@pytest.fixture
def overpass_client():
    """ Provide a minimal valid Route object for testing """
    idx = index.Index()
    points = [RoutePoint(0, 0)]
    for i, point in enumerate(points):
        idx.insert(i, (point.lon, point.lat, point.lon, point.lat))
    
    return OverpassClient(route=Route(points=points, id="test", rtree=idx))
@pytest.fixture
def bbox():
    return {
        "south": 47.3700,
        "north": 47.3850,
        "west": 8.5300,
        "east": 8.5600
    }

@responses.activate
def test_sucessfull(overpass_client , bbox):
    """
    Test Overpass Requirement 2: Successful API query < 5 seconds.
    
    Mocks successful Overpass API response with gas station data.
    """
    # Mock all possible Overpass API URLs
    for url in ["https://overpass-api.de/api/interpreter", "http://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]:
        responses.post(url,
                       json={
                           "elements" : [
                                {
                                    "type": "node",
                                    "id": 123456,
                                    "lat": 47.3769,
                                    "lon": 8.5417,
                                    "tags": {
                                        "amenity": "fuel",
                                        "name": "Shell",
                                        "operator": "Shell"
                                    }
                                },
                                {
                                    "type": "node",
                                    "id": 789012,
                                    "lat": 47.3800,
                                    "lon": 8.5450,
                                    "tags": {
                                        "amenity": "fuel",
                                        "name": "BP"
                                    }
                                }
                           ]
                           },
                        status = 200
                        )

    results = overpass_client.query_poi_type(bbox, "gas_stations")
    assert "elements" in results
    assert len(results["elements"]) == 2


@responses.activate
def test_rate_limiting_error(overpass_client, bbox):
    """Test proper handling of Overpass API rate limit (429) errors."""
    # Mock all possible Overpass API URLs to return 429
    for url in ["https://overpass-api.de/api/interpreter", "http://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]:
        responses.post(
            url,
            json = {"error" : "Rate limit exceed"},
            status = 429
        )
    with pytest.raises(ConnectionError, match="Overpass API rate limit exceeded."):
        overpass_client.query_poi_type(bbox, "gas_stations")
        
@responses.activate
def test_empty_results(overpass_client, bbox):
    """Test handling of valid API response with no results."""
    # Mock all possible Overpass API URLs
    for url in ["https://overpass-api.de/api/interpreter", "http://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]:
        responses.post(
            url,
            json={"elements" : []},
            status=200        
        )
    results = overpass_client.query_poi_type(bbox, "gas_stations")
    assert results["elements"] == []

@responses.activate 
def test_invalid_json(overpass_client, bbox):
    """Test error handling for malformed JSON responses."""
    # Mock all possible Overpass API URLs
    for url in ["https://overpass-api.de/api/interpreter", "http://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]:
        responses.post(
            url,
            body='{"invalid":',
            status = 200)
    with pytest.raises(ValueError):
        overpass_client.query_poi_type(bbox, "gas_stations")