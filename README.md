# POI Ahead

Upload a GPX track. Discover shops, water sources, and stops along your route. Star key POIs, export for Garmin to get notifications while riding, or generate a cue sheet — everything you need for your next ultracycling or bikepacking adventure.

Built on [MapAhead](https://github.com/arcticfade/MapAhead) by [arcticfade](https://github.com/arcticfade), which provides the really helpful R-tree spatial indexing and POI discovery engine. Thanks!

## Features

- **GPX Upload** - Import GPX files up to 2MB
- **Interactive Map** - Route visualization using Leaflet.js with multiple map layers (Standard, Cycling, Topo, Satellite)
- **POI Discovery** - Automatic detection of various POI types along your route via Overpass API and possibility to only show a POI every x meters.
- **Smart Timeline** - Elevation profile with POI markers and estimated travel times
- **Export Options** - Download starred POIs as GPX (for Garmin, Komoot, Ride with GPS) or KML (for Google My Maps)
- **Responsive Design** - Modern UI that works on desktop and mobile

> **Important:** Not all POI icons and information fields are fully supported across all platforms (Garmin Connect, RideWithGPS, Komoot, etc.). For example, only toilet icons display correctly on Garmin Connect - other POI types appear as generic flags. Always test your exported GPX file on your device before your adventure to ensure POIs display as expected.

### Supported POI Types

- Toilets
- Bakeries
- Gas Stations
- Grocery Stores
- Water Fountains
- Bicycle Shops
- Bicycle Vending Machines
- Vending Machines
- Accommodation (Hotels, Camping)
- Sport Areas

## Quick Start

### Prerequisites

- Python 3.8+

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/gardaholm/poiahead.git
   cd poiahead
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the backend** (in `Backend/` folder)
   ```bash
   cd Backend
   fastapi dev main.py --port 8000
   ```

4. **Start the frontend** (in `Frontend/` folder)
   ```bash
   cd Frontend
   python -m http.server 4000
   ```

5. **Open in browser**
   ```
   http://localhost:4000
   ```

## Project Structure

```
poiahead/
├── Backend/
│   ├── main.py                 # FastAPI application
│   ├── gpx_parser.py           # GPX file parsing
│   ├── gpx_generator.py        # GPX export with waypoints
│   ├── kml_generator.py        # KML export for Google My Maps
│   ├── route_storage.py        # Route storage with R-tree indexing
│   ├── route_calculator.py     # Distance calculations
│   ├── overpass_client.py      # Overpass API integration
│   └── poi.py                  # POI data model
├── Frontend/
│   ├── index.html              # Main HTML page
│   └── static/
│       ├── script.js           # Frontend logic
│       ├── style.css           # Modern styling
│       └── poi-icons.json      # POI icon configuration
└── tests/
    ├── unit/                   # Unit tests
    └── integration/            # Integration & performance tests
```

## Technology Stack

**Backend:**
- FastAPI - REST API framework with SSE streaming
- rtree - Spatial indexing (R-tree)
- haversine - Geodesic distance calculations
- gpxpy - GPX parsing and generation

**Frontend:**
- Leaflet.js - Interactive maps
- OpenStreetMap / CyclOSM / OpenTopoMap - Map tiles
- Vanilla JavaScript - No framework dependencies
- Inter font - Modern typography

**Testing:**
- pytest - Testing framework
- responses - HTTP mocking
- Selenium - Frontend testing

## API Endpoints

### `POST /gpx/upload`
Upload a GPX file and receive route data.

### `GET /pois/{route_id}`
Get POIs along a route (SSE streaming).

**Query Parameters:**
- `poi_types` - Comma-separated POI types to fetch
- `poi_settings` - JSON object with per-POI-type max deviation and deduplication radius

### `POST /gpx/download/{route_id}`
Download GPX file with starred POIs as waypoints.

### `POST /kml/download/{route_id}`
Download KML file with starred POIs for Google My Maps.

## Docker Deployment

```bash
docker build -t poiahead .
docker run -p 8000:8000 poiahead
```

## Testing

```bash
pytest                                    # All tests
pytest tests/unit/                        # Unit tests only
pytest tests/integration/                 # Integration tests only
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Credits

This project is based on [MapAhead](https://github.com/arcticfade/MapAhead) by [arcticfade](https://github.com/arcticfade).

## Acknowledgments

- OpenStreetMap contributors for map data
- Overpass API for POI queries
- Leaflet.js for mapping capabilities
- CyclOSM for cycling-optimized map tiles
