# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Run Commands

**Backend (FastAPI):**
```bash
cd Backend
fastapi dev main.py --port 8000
```

**Frontend (static files):**
```bash
cd Frontend
python -m http.server 4000
```

**Tests:**
```bash
pytest                                    # All tests
pytest tests/unit/                        # Unit tests only
pytest tests/integration/                 # Integration tests only
pytest tests/unit/test_gpx_parser.py     # Single test file
pytest -k "test_filter"                   # Run tests matching pattern
```

**Docker:**
```bash
docker build -t poiahead .
docker run -p 8000:8000 poiahead
```

## Architecture Overview

POI Ahead: Upload a GPX track. Discover shops, water sources, and stops along your route. Star key POIs, export for Garmin to get notifications while riding, or generate a cue sheet — everything you need for your next ultracycling or bikepacking adventure. Uses OpenStreetMap data via Overpass API.

### Data Flow
1. User uploads GPX file → `GPXParser` extracts `RoutePoint` list
2. `RouteStorage` stores route with R-tree spatial index for efficient nearest-neighbor queries
3. `OverpassClient` queries OpenStreetMap Overpass API for POIs within route bounding box
4. POIs filtered by distance to route using `RouteCalculator` with haversine distance
5. Results streamed to frontend via Server-Sent Events (SSE)
6. User can star POIs and export them as GPX or KML

### Key Backend Components

- **`main.py`**: FastAPI app with endpoints:
  - `/gpx/upload` (POST) - Upload GPX file
  - `/pois/{route_id}` (GET) - SSE streaming of POIs
  - `/gpx/download/{route_id}` (POST) - Export GPX with waypoints
  - `/kml/download/{route_id}` (POST) - Export KML for Google My Maps
- **`route_storage.py`**: In-memory route storage with R-tree indexing. `RouteStorage` is thread-safe; `Route` holds points + spatial index
- **`overpass_client.py`**: Queries multiple Overpass API instances with retry/fallback. `POI_TYPE_CONFIG` dict defines all supported POI types and their Overpass queries
- **`route_calculator.py`**: Distance calculations using haversine formula and R-tree for nearest point lookup
- **`poi.py`**: `POI` dataclass with coordinates, distances, metadata (opening hours, brand, price range, etc.)
- **`gpx_generator.py`**: Generates GPX files with POI waypoints for Garmin/Komoot/RideWithGPS
- **`kml_generator.py`**: Generates KML files with styled placemarks for Google My Maps

### POI Types
Defined in `POI_TYPE_CONFIG` in `overpass_client.py`:
- `public_toilets`, `bakeries`, `gas_stations`, `grocery_stores`, `water_fountains`
- `bicycle_shops`, `bicycle_vending`, `vending_machines`, `camping_hotels`, `sport_areas`

### Frontend Architecture

Modern responsive UI with floating panels over a full-screen map.

**Key Files:**
- `index.html` - Main HTML with floating controls, POI panel, settings panel, timeline, modals
- `static/script.js` - All frontend logic (map, POI handling, settings, exports)
- `static/style.css` - Modern CSS with design tokens, glassmorphism effects
- `static/poi-icons.json` - POI type to icon/color mapping

**UI Components:**
- **Top Toolbar** - Logo on left, action buttons (Upload, Export, Timeline, Settings) + GitHub/Info links on right; spans from left edge to POI panel
- **POI Panel** - Right sidebar (desktop) or bottom panel (mobile), collapsible; toolbar expands when collapsed
- **Settings Panel** - Slide-out from right with POI type toggles and filter settings
- **Timeline Panel** - Elevation profile with distance/time scales and POI markers (bottom, left of POI panel)
- **Export Modal** - Choose between GPX and KML export formats
- **Credits Modal** - About info with attribution and links

**Map Layers:**
- Standard (OpenStreetMap)
- Cycling (CyclOSM)
- Topo (OpenTopoMap)
- Satellite (Esri)

**Responsive Breakpoints:**
- Desktop: > 900px - POI panel on right side
- Tablet: 600-900px - POI panel at bottom
- Mobile: < 600px - Compact controls, hidden header

## Test Fixtures

- GPX test files located in `tests/files/`
- `conftest.py` adds Backend to Python path
