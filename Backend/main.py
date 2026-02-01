from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional, Dict
import logging
import json
import asyncio
import queue
import os
from pathlib import Path

from Backend.gpx_parser import GPXParser
from Backend.route_storage import RouteStorage
from Backend.overpass_client import OverpassClient
from Backend.gpx_generator import generate_gpx_with_waypoints
from Backend.kml_generator import generate_kml_with_waypoints
from Backend.route_calculator import RouteCalculator
from Backend.poi import POI

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_FILE_SIZE_MB = 2
MAX_FILE_SIZE_BYTES = int(MAX_FILE_SIZE_MB * 1024 * 1024)

app = FastAPI()

# Get allowed origins from environment or use defaults
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",") if os.getenv("ALLOWED_ORIGINS") else ["*"]

# CORS middleware must be added before routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods including OPTIONS
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers
)

# Path setup for frontend files
frontend_path = Path(__file__).parent.parent / "Frontend"
static_path = frontend_path / "static"
css_path = frontend_path / "css"

route_storage = RouteStorage()

# Serve index.html at root
@app.get("/")
async def read_root():
    index_path = frontend_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "MapAhead API", "status": "running"}

@app.post("/gpx/upload")
async def upload_gpx(file: UploadFile = File(...)):
    """
    Endpoint to upload a GPX file and parse route data.
        Args:
            file (UploadFile): The uploaded GPX file.
        Returns: 
            dict: containing route_id, filename and coordinates list. 
    """
    if not file.filename.endswith('.gpx'): # type: ignore
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a GPX file.")
    try:
        # Read up to MAX_FILE_SIZE_BYTES + 1 to detect if file is too large
        gpx_data = await file.read(MAX_FILE_SIZE_BYTES + 1)

        if len(gpx_data) == 0:
            raise HTTPException(status_code=400, detail="The uploaded file is empty. Please upload a valid GPX file.")
        
        if len(gpx_data) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=413, detail=f"File too large. Maximum size: {MAX_FILE_SIZE_MB} MB")
        
        parser = GPXParser(gpx_data)
        route_points, elevation_profile, total_distance = parser.parse_with_elevation()

        if len(route_points) == 0:
            raise HTTPException(status_code=400, detail="The GPX file does not contain any route points. Please upload a valid GPX file with track data.")

        route_id = route_storage.store(route_points, gpx_data=gpx_data, filename=file.filename)

        coordinates = [{"lat": point.lat, "lon": point.lon} for point in route_points]
        return {
            "route_id": route_id,
            "filename": file.filename,
            "coordinates": coordinates,
            "elevation_profile": elevation_profile,
            "total_distance": round(total_distance, 2)
        }
    except HTTPException:
        # Re-raise HTTP exceptions as-is (they already have proper error messages)
        raise
    except ValueError as e:
        # Handle parsing errors from GPXParser
        logger.error(f"GPX parsing error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to parse GPX file: {str(e)}")
    except Exception as e:
        # Handle any other unexpected errors
        logger.error(f"Unexpected error processing GPX file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process GPX file: {str(e)}")


def format_poi_type_name(poi_type: str) -> str:
    """Format POI type name for display (e.g., 'gas_stations' -> 'Gas Stations')"""
    if poi_type == 'camping_hotels':
        return 'Accommodation'
    return poi_type.replace('_', ' ').title()

async def generate_poi_stream(route_id: str, max_distance_km: float, poi_types: Optional[List[str]] = None, deduplication_radius_km: float = 1.0, poi_settings: Optional[Dict[str, Dict[str, float]]] = None):
    """Generator function that yields progress updates and final result"""
    route = route_storage.get(route_id)
    if not route:
        yield f"data: {json.dumps({'error': 'Route not found'})}\n\n"
        return
    
    try:
        overpass_client = OverpassClient(route)
        bbox = overpass_client.get_route_bounding_box(buffer_km=max_distance_km)
        logger.info(f"Querying POIs for route {route_id} with bbox: {bbox}, selected types: {poi_types}")
        
        # Progress tracking using thread-safe queue
        progress_queue = queue.Queue()
        batch_queue = queue.Queue()
        
        def progress_callback(poi_type: str, current: int, total: int):
            # Add progress update to thread-safe queue
            progress_queue.put({
                'type': 'progress',
                'poi_type': poi_type,
                'poi_type_display': format_poi_type_name(poi_type),
                'current': current,
                'total': total
            })
        
        def batch_callback(poi_type: str, pois: List[POI]):
            # Add POI batch to thread-safe queue
            batch_queue.put({
                'type': 'poi_batch',
                'poi_type': poi_type,
                'poi_type_display': format_poi_type_name(poi_type),
                'markers': [
                    {
                        "lat": poi.lat,
                        "lon": poi.lon,
                        "name": poi.name,
                        "poi_type": poi.poi_type,
                        "opening_hours": poi.opening_hours,
                        "url": poi.url,
                        "google_maps_link": poi.google_maps_link,
                        "distance_on_route": poi.distance_on_route,
                        "distance_to_route": poi.distance_to_route,
                        "price_range": poi.price_range,
                        "brand": poi.brand,
                        "operator": poi.operator,
                        "wikipedia": poi.wikipedia,
                        "wikidata": poi.wikidata
                    }
                    for poi in pois
                ],
                "table": [
                    {
                        "distance": f"{poi.distance_on_route:.1f} km",
                        "deviation": f"{poi.distance_to_route * 1000:.0f}m",
                        "name": poi.name,
                        "poi_type": poi.poi_type,
                        "opening_hours": poi.opening_hours or "Not available",
                        "url": poi.url or "",
                        "google_maps_link": poi.google_maps_link,
                        "price_range": poi.price_range
                    }
                    for poi in pois
                ]
            })
        
        # Run the query in a thread pool to allow yielding progress
        import concurrent.futures
        
        def run_query():
            return overpass_client.query_all_poi_types(
                bbox, 
                max_distance_to_route_km=max_distance_km,
                selected_poi_types=poi_types,
                progress_callback=progress_callback,
                batch_callback=batch_callback,
                deduplication_radius_km=deduplication_radius_km,
                poi_settings=poi_settings
            )
        
        # Start the query
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_query)
            
            # Yield progress updates and batches while query is running
            while not future.done():
                # Try to get batch updates first (POIs to display)
                try:
                    batch = batch_queue.get(timeout=0.1)
                    yield f"data: {json.dumps(batch)}\n\n"
                except queue.Empty:
                    # Try to get progress updates
                    try:
                        progress = progress_queue.get(timeout=0.05)
                        yield f"data: {json.dumps(progress)}\n\n"
                    except queue.Empty:
                        # No updates, continue waiting
                        await asyncio.sleep(0.05)
            
            # Get the result
            filtered_pois = future.result()
            logger.info(f"Retrieved {len(filtered_pois)} POIs within {max_distance_km}km of route")
        
        # Yield any remaining batch updates first
        while not batch_queue.empty():
            try:
                batch = batch_queue.get_nowait()
                yield f"data: {json.dumps(batch)}\n\n"
            except queue.Empty:
                break
        
        # Yield any remaining progress updates
        while not progress_queue.empty():
            try:
                progress = progress_queue.get_nowait()
                yield f"data: {json.dumps(progress)}\n\n"
            except queue.Empty:
                break
        
        # Yield final result
        result = {
            'type': 'complete',
            'markers': [
                {
                    "lat": poi.lat,
                    "lon": poi.lon,
                    "name": poi.name,
                    "poi_type": poi.poi_type,
                    "opening_hours": poi.opening_hours,
                    "url": poi.url,
                    "google_maps_link": poi.google_maps_link,
                    "distance_on_route": poi.distance_on_route,
                    "distance_to_route": poi.distance_to_route,
                    "price_range": poi.price_range,
                    "brand": poi.brand,
                    "operator": poi.operator,
                    "wikipedia": poi.wikipedia,
                    "wikidata": poi.wikidata
                }
                for poi in filtered_pois
            ],
            "table": [
                {
                    "distance": f"{poi.distance_on_route:.1f} km",
                    "deviation": f"{poi.distance_to_route * 1000:.0f}m",
                    "name": poi.name,
                    "poi_type": poi.poi_type,
                    "opening_hours": poi.opening_hours or "Not available",
                    "url": poi.url or "",
                    "google_maps_link": poi.google_maps_link,
                    "price_range": poi.price_range
                }
                for poi in filtered_pois
            ]
        }
        yield f"data: {json.dumps(result)}\n\n"
        
    except TimeoutError as e:
        logger.error(f"Timeout retrieving POIs for route {route_id}: {str(e)}", exc_info=True)
        yield f"data: {json.dumps({'type': 'error', 'error': 'POI service timed out. The query is taking too long. Please try again or use a shorter route.'})}\n\n"
    except ConnectionError as e:
        logger.error(f"Connection error retrieving POIs for route {route_id}: {str(e)}", exc_info=True)
        yield f"data: {json.dumps({'type': 'error', 'error': 'POI service is temporarily unavailable. Please try again in a few moments.'})}\n\n"
    except Exception as e:
        logger.error(f"Error retrieving POIs for route {route_id}: {str(e)}", exc_info=True)
        yield f"data: {json.dumps({'type': 'error', 'error': f'Failed to retrieve POIs: {str(e)}'})}\n\n"

@app.get("/pois/{route_id}")
async def get_pois(
    route_id: str, 
    max_distance_km: float = 1.0,
    poi_types: Optional[List[str]] = Query(None, description="List of POI types to query"),
    deduplication_radius_km: float = 1.0,
    poi_settings_json: Optional[str] = Query(None, description="JSON string of per-POI-type settings: {\"poi_type\": {\"max_deviation_km\": float, \"deduplication_radius_km\": float}}")
):
    """
    Endpoint to get point of interests (POI) along a route with progress updates via Server-Sent Events.
        Args:
            route_id (str): The ID of the route.
            max_distance_km (float): Maximum distance from the route to consider POIs (in kilometers). Default is 1 km.
            poi_types (Optional[List[str]]): List of POI types to query. If None, queries all types.
            deduplication_radius_km (float): Radius in kilometers for deduplication. Default is 1.0 km. Used as fallback.
            poi_settings_json (Optional[str]): JSON string with per-POI-type settings.
        Returns: 
            StreamingResponse: Server-Sent Events stream with progress updates and final result.
    """
    poi_settings = None
    if poi_settings_json:
        try:
            poi_settings = json.loads(poi_settings_json)
        except json.JSONDecodeError:
            logger.warning(f"Invalid poi_settings_json, ignoring: {poi_settings_json}")
    
    return StreamingResponse(
        generate_poi_stream(route_id, max_distance_km, poi_types, deduplication_radius_km, poi_settings),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/gpx/download/{route_id}")
async def download_gpx_with_pois(
    route_id: str,
    starred_pois: List[Dict] = Body(..., description="List of starred POI data")
):
    """
    Endpoint to download GPX file with starred POIs as waypoints.
    
    Args:
        route_id (str): The ID of the route.
        starred_pois (List[Dict]): List of starred POI data dictionaries.
        
    Returns:
        Response: GPX file with waypoints as downloadable file.
    """
    route = route_storage.get(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    
    if not route.gpx_data:
        raise HTTPException(status_code=400, detail="Original GPX data not available for this route")
    
    try:
        # Use the starred POIs directly from the request body
        starred_pois_data = starred_pois
        
        # Convert to POI objects
        pois = []
        route_calculator = RouteCalculator()
        
        for poi_data in starred_pois_data:
            # Try to get numeric distance values first (if frontend sends them)
            distance_on_route = poi_data.get('distance_on_route')
            distance_to_route = poi_data.get('distance_to_route')
            
            # If not available, try parsing from formatted strings
            if distance_on_route is None:
                distance_str = poi_data.get('distance', '0 km')
                try:
                    distance_on_route = float(distance_str.replace(' km', ''))
                except (ValueError, TypeError):
                    distance_on_route = 0.0
            
            if distance_to_route is None:
                deviation_str = poi_data.get('deviation', '0m')
                try:
                    distance_to_route = float(deviation_str.replace('m', '')) / 1000.0  # Convert meters to km
                except (ValueError, TypeError):
                    distance_to_route = 0.0
            
            # If distances are still 0 or missing, recalculate from coordinates
            if distance_on_route == 0.0 or distance_to_route == 0.0:
                from Backend.route_storage import RoutePoint
                poi_point = RoutePoint(lat=poi_data['lat'], lon=poi_data['lon'])
                nearest_index = route_calculator.find_nearest_route_point_index(route, poi_point)
                nearest_route_point = route.points[nearest_index]
                distance_to_route = route_calculator.haversine_distance(poi_point, nearest_route_point)
                distance_on_route = route_calculator.calculate_distance_on_route(route, nearest_route_point)
            
            poi = POI(
                lat=poi_data['lat'],
                lon=poi_data['lon'],
                name=poi_data['name'],
                distance_to_route=distance_to_route,
                distance_on_route=distance_on_route,
                poi_type=poi_data.get('poi_type', 'unknown'),
                opening_hours=poi_data.get('opening_hours'),
                url=poi_data.get('url'),
                google_maps_link=poi_data.get('google_maps_link', '')
            )
            pois.append(poi)
        
        # Generate GPX with waypoints
        gpx_xml = generate_gpx_with_waypoints(
            route.gpx_data,
            route,
            pois,
            route_calculator,
            mode='garmin'
        )
        
        # Generate filename
        if route.filename:
            base_name = route.filename.replace('.gpx', '')
            filename = f"{base_name}_with_pois.gpx"
        else:
            filename = f"route_{route_id}_with_pois.gpx"
        
        return Response(
            content=gpx_xml,
            media_type="application/gpx+xml",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating GPX with waypoints: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate GPX file: {str(e)}")


@app.post("/kml/download/{route_id}")
async def download_kml_with_pois(
    route_id: str,
    starred_pois: List[Dict] = Body(..., description="List of starred POI data")
):
    """
    Endpoint to download KML file with starred POIs as placemarks.

    Args:
        route_id (str): The ID of the route.
        starred_pois (List[Dict]): List of starred POI data dictionaries.

    Returns:
        Response: KML file with placemarks as downloadable file.
    """
    route = route_storage.get(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    try:
        starred_pois_data = starred_pois

        # Convert to POI objects
        pois = []
        route_calculator = RouteCalculator()

        for poi_data in starred_pois_data:
            distance_on_route = poi_data.get('distance_on_route')
            distance_to_route = poi_data.get('distance_to_route')

            if distance_on_route is None:
                distance_str = poi_data.get('distance', '0 km')
                if 'km' in distance_str:
                    try:
                        distance_on_route = float(distance_str.replace(' km', '').strip())
                    except ValueError:
                        distance_on_route = 0.0
                else:
                    distance_on_route = 0.0

            if distance_to_route is None:
                deviation_str = poi_data.get('deviation', '0m')
                if 'm' in deviation_str:
                    try:
                        deviation_m = float(deviation_str.replace('m', '').strip())
                        distance_to_route = deviation_m / 1000.0
                    except ValueError:
                        distance_to_route = 0.0
                else:
                    distance_to_route = 0.0

            poi = POI(
                lat=poi_data['lat'],
                lon=poi_data['lon'],
                name=poi_data.get('name', 'Unnamed POI'),
                distance_to_route=distance_to_route,
                distance_on_route=distance_on_route,
                poi_type=poi_data.get('poi_type', 'unknown'),
                opening_hours=poi_data.get('opening_hours'),
                url=poi_data.get('url'),
                google_maps_link=poi_data.get('google_maps_link', '')
            )
            pois.append(poi)

        # Generate KML with waypoints
        route_name = route.filename.replace('.gpx', '') if route.filename else f"Route {route_id}"
        kml_xml = generate_kml_with_waypoints(
            route,
            pois,
            route_name=route_name
        )

        # Generate filename
        if route.filename:
            base_name = route.filename.replace('.gpx', '')
            filename = f"{base_name}_with_pois.kml"
        else:
            filename = f"route_{route_id}_with_pois.kml"

        return Response(
            content=kml_xml,
            media_type="application/vnd.google-earth.kml+xml",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except Exception as e:
        logger.error(f"Error generating KML with waypoints: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate KML file: {str(e)}")


# Mount static files AFTER all API routes to avoid routing conflicts
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

if css_path.exists():
    app.mount("/css", StaticFiles(directory=str(css_path)), name="css")

