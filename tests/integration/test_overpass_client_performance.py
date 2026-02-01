from overpass_client import OverpassClient
from gpx_parser import GPXParser
from route_storage import RouteStorage
import time
from fastapi.testclient import TestClient
from main import app 
import os
import json

def test_performance():
    """
    Test Overpass Requirements 1, 2, 3:
    - Requirement 1: BBox calculation < 1 second
    - Requirement 2: Overpass API query < 5 seconds
    - Requirement 3: POI filtering < 3 seconds
    
    Tests 100km route. Note: Depends on Overpass API availability.
    """
    test_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    file_path = os.path.join(test_dir, 'tests', 'files', 'test_file_100km.gpx')
    with open(file_path,'rb') as file:
        gpx_byte = file.read()
    
    gpx_parser = GPXParser(gpx_byte)
    route_points = gpx_parser.parse()

    route_storage = RouteStorage()
    route_id = route_storage.store(route_points)
    route = route_storage.get(route_id)

    start_time = time.time()
    overpass_client = OverpassClient(route) # type: ignore
    bbox = overpass_client.get_route_bounding_box()
    end_time = time.time()
    end_time = end_time-start_time
    assert end_time < 1 # BBox creation time should be unter 1 sec 
    
    start_time = time.time()
    results = overpass_client.query_poi_type(bbox, "gas_stations")
    end_time = time.time()
    end_time = end_time-start_time
    assert end_time < 5 # Overpass query time should be unter 5 sec 
    
    start_time = time.time()
    filtered_pois = overpass_client.filter_pois(results, "gas_stations", max_distance_to_route_km=2.0)
    end_time = time.time()
    end_time = end_time-start_time
    assert len(filtered_pois) > 0
    assert end_time < 3 # POI filtering time should be unter 3 sec 
    # complete performence under 9 sec

client = TestClient(app)

def test_poi_data_response_time():
    """
    Test Backend Requirement 4: POI data delivery format and structure.
    
    Verifies SSE stream response contains:
    - Route kilometers (distance)
    - Distance to route (deviation)
    - POI name
    - Coordinates (lat/lon)
    
    Note: Since the endpoint collects all POI types and processes them,
    the complete response may take significant time for large routes.
    This test verifies the response format and data structure rather than
    enforcing time limits, as the TestClient blocks until the entire
    SSE stream is consumed.
    """
    test_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    file_path = os.path.join(test_dir, 'tests', 'files', 'test_file_100km.gpx')
    with open(file_path,'rb') as file:
        gpx_byte = file.read()
    
    upload_response = client.post(
        "/gpx/upload",
        files={"file": ("test.gpx", gpx_byte, "application/gpx+xml")}
    )
    assert upload_response.status_code == 200
    route_id = upload_response.json()["route_id"]
    
    # Make request - TestClient will block until entire stream is consumed
    response = client.get(f"/pois/{route_id}?max_distance_km=2.0")
    
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    
    # Parse SSE stream to find the final 'complete' event
    complete_event = None
    received_events = []
    
    # Read all lines from the stream
    for line in response.iter_lines():
        if line:
            # Decode bytes to string if needed
            if isinstance(line, bytes):
                line = line.decode('utf-8')
            
            # SSE format: "data: {...}\n\n"
            if line.startswith("data: "):
                try:
                    event_data = json.loads(line[6:])  # Skip "data: " prefix
                    received_events.append(event_data.get("type", "unknown"))
                    if event_data.get("type") == "complete":
                        complete_event = event_data
                except json.JSONDecodeError:
                    continue
    
    # Verify we received events (progress updates and/or batches)
    assert len(received_events) > 0, "No data events received in SSE stream"
    
    # Use the complete event if found, otherwise fail
    assert complete_event is not None, "No complete event found in SSE stream"
    data = complete_event
    assert "markers" in data
    assert len(data["markers"]) > 0
    
    marker = data["markers"][0]
    assert "lat" in marker  
    assert "lon" in marker  
    assert "name" in marker  
    
    assert "table" in data
    assert len(data["table"]) > 0
    
    table_entry = data["table"][0]
    assert "distance" in table_entry  
    assert "deviation" in table_entry  
    assert "name" in table_entry  
    
    assert isinstance(marker["lat"], float)
    assert isinstance(marker["lon"], float)
    assert isinstance(marker["name"], str)
    assert isinstance(table_entry["distance"], str)  
    assert isinstance(table_entry["deviation"], str)  
    assert isinstance(table_entry["name"], str)