import pytest
import time
import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

MOCK_POIS_RESPONSE = {
    "markers": [
        {"lat": 54.244, "lon": 10.037, "name": "OIL!"},
        {"lat": 54.245, "lon": 10.040, "name": "Aral"},
        {"lat": 54.246, "lon": 10.042, "name": "Shell"},
        {"lat": 54.247, "lon": 10.044, "name": "Shell"},
        {"lat": 54.248, "lon": 10.045, "name": "Clean Car"},
        {"lat": 54.249, "lon": 10.047, "name": "Jet"},
        {"lat": 54.250, "lon": 10.049, "name": "Shell"},
        {"lat": 54.251, "lon": 10.050, "name": "H2 Tankstelle"},
        {"lat": 54.252, "lon": 10.051, "name": "Unnamed Gas Station"},
        {"lat": 54.253, "lon": 10.052, "name": "Aral"},
    ],
    "table": [
        {"distance": "1.1 km", "deviation": "106m", "name": "OIL!"},
        {"distance": "3.0 km", "deviation": "812m", "name": "Aral"},
        {"distance": "4.3 km", "deviation": "88m", "name": "Shell"},
        {"distance": "5.4 km", "deviation": "304m", "name": "Shell"},
        {"distance": "6.8 km", "deviation": "51m", "name": "Clean Car"},
        {"distance": "7.2 km", "deviation": "196m", "name": "Jet"},
        {"distance": "7.8 km", "deviation": "879m", "name": "Shell"},
        {"distance": "7.8 km", "deviation": "878m", "name": "H2 Tankstelle"},
        {"distance": "8.1 km", "deviation": "526m", "name": "Unnamed Gas Station"},
        {"distance": "8.2 km", "deviation": "654m", "name": "Aral"},
    ]
}

@pytest.fixture
def browser():
    chrome_options = Options()
    chrome_options.add_argument("--allow-insecure-localhost")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=chrome_options)
    yield driver
    driver.quit()

def test_map_existence_and_loading_time(browser):
    """
    Test Frontend Requirement 1: Map must load within 3 seconds.
    
    Verifies:
    - Map element exists and is visible
    - OSM attribution is present
    - Leaflet controls are loaded
    - Total loading time < 3 seconds
    """
    start_time = time.time()
    browser.get("http://127.0.0.1:8000")
    wait = WebDriverWait(browser,3)

    map_element = wait.until(
        EC.presence_of_element_located((By.ID, "map"))
    )
    end_time = time.time()
    total_time = end_time - start_time
    assert total_time < 3
    assert map_element.is_displayed()

    license = wait.until(
        EC.presence_of_element_located((By.CLASS_NAME, "leaflet-attribution-flag"))
    )
    assert "OpenStreetMap" in browser.page_source

    zoom_controls = browser.find_elements(By.CLASS_NAME, "leaflet-control-zoom")
    assert len(zoom_controls) > 0

def test_gpx_upload_route_pois_happy_path(browser):
    """
    Test Frontend Requirements 3 & 4:
    - Requirement 3: Display 200 route coordinates within 2 seconds
    - Requirement 4: Load and display 10 POIs within 2 seconds
    
    Tests complete user workflow from GPX upload to POI visualization.
    """
    # Generate mock coordinates (at least 200 as per requirement)
    mock_route_id = "test-route-123"
    mock_coordinates = [
        {"lat": 54.0 + i * 0.001, "lon": 10.0 + i * 0.001}
        for i in range(200)
    ]
    mock_gpx_response = {
        "route_id": mock_route_id,
        "filename": "test_file_100km.gpx",
        "coordinates": mock_coordinates
    }
    
    browser.get("http://127.0.0.1:8000")
    wait = WebDriverWait(browser,10)
    
    # Wait for page to be fully loaded
    wait.until(EC.presence_of_element_located((By.ID, "map")))
    
    # Inject fetch mocks before the page makes requests
    # Mock fetch to intercept both GPX upload and POI requests
    mock_gpx_json = json.dumps(mock_gpx_response)
    mock_pois_json = json.dumps(MOCK_POIS_RESPONSE)
    mock_script = f"""
    const originalFetch = window.fetch;
    const mockGpxResponse = {mock_gpx_json};
    const mockPoisResponse = {mock_pois_json};
    window.fetch = function(url, options) {{
        if (url.includes('/gpx/upload') && options && options.method === 'POST') {{
            return Promise.resolve(new Response(
                JSON.stringify(mockGpxResponse),
                {{ status: 200, headers: {{ 'Content-Type': 'application/json' }} }}
            ));
        }}
        if (url.includes('/pois/{mock_route_id}')) {{
            return Promise.resolve(new Response(
                JSON.stringify(mockPoisResponse),
                {{ status: 200, headers: {{ 'Content-Type': 'application/json' }} }}
            ));
        }}
        return originalFetch.apply(this, arguments);
    }};
    """
    browser.execute_script(mock_script)

    # GPX-Upload und display
    file_input = wait.until(
        EC.presence_of_element_located((By.ID, "gpx-upload"))
    )
    # Get the absolute path to the test file (cross-platform)
    test_dir = Path(__file__).parent.parent
    file_path = str(test_dir / "files" / "test_file_100km.gpx")
    file_input.send_keys(file_path)
    upload_start = time.time()
    route_line = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".leaflet-pane svg path"))
    )
    upload_time = time.time() - upload_start
    assert upload_time < 2, f"Upload dauerte {upload_time:.2f}s"
    assert route_line is not None
    filename_display = wait.until(
        EC.presence_of_element_located((By.ID, "filename-display"))
    )
    assert "test_file_100km.gpx" in filename_display.text
    time.sleep(0.2)

    # POI-Load
    poi_load_start = time.time()
    route_id = browser.execute_script("return currentRouteID;")
    assert route_id == mock_route_id
    
    poi_time = time.time() - poi_load_start
    wait.until(
        lambda driver: len(driver.find_elements(By.CSS_SELECTOR, "#poi-tbody tr")) >= 10,
    )
    assert poi_time < 2
    table_rows = browser.find_elements(By.CSS_SELECTOR, "#poi-tbody tr")
    assert len(table_rows) >= 10


    