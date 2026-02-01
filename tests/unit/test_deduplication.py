"""
Unit tests for POI deduplication functionality.
"""
import pytest
from rtree import index
from overpass_client import OverpassClient
from route_storage import RoutePoint, Route
from poi import POI


@pytest.fixture
def simple_route():
    """Create a simple route for testing."""
    points = [RoutePoint(0.0, 0.0), RoutePoint(0.0, 0.01), RoutePoint(0.01, 0.01)]
    rtree = index.Index()
    for i, point in enumerate(points):
        rtree.insert(i, (point.lon, point.lat, point.lon, point.lat))
    return Route(points=points, id="test_route", rtree=rtree)


@pytest.fixture
def overpass_client(simple_route):
    """Create an OverpassClient instance for testing."""
    return OverpassClient(simple_route)


def test_deduplication_same_type_within_radius(overpass_client):
    """Test that POIs of the same type within deduplication radius are deduplicated."""
    # Create two POIs of the same type very close to each other (within 1km)
    # Distance between (0.0, 0.0) and (0.001, 0.001) is approximately 0.157km
    # Both are same distance to route, but one has longer opening hours (24/7)
    pois = [
        POI(lat=0.0, lon=0.0, name="Toilet 1", distance_to_route=0.1, distance_on_route=0.0, 
            poi_type="public_toilets", opening_hours="24/7"),
        POI(lat=0.001, lon=0.001, name="Toilet 2", distance_to_route=0.1, distance_on_route=0.0, 
            poi_type="public_toilets", opening_hours="Mo-Fr 09:00-17:00"),
    ]
    
    # Deduplicate with 1km radius
    deduplicated = overpass_client.deduplicate_pois(pois, deduplication_radius_km=1.0)
    
    # Should keep only one POI (prefer longer opening hours when distance is equal)
    assert len(deduplicated) == 1
    assert deduplicated[0].name == "Toilet 1"  # 24/7 should be preferred (longer hours)
    assert deduplicated[0].opening_hours == "24/7"


def test_deduplication_same_type_outside_radius(overpass_client):
    """Test that POIs of the same type outside deduplication radius are kept."""
    # Create two POIs far apart (more than 1km)
    # Distance between (0.0, 0.0) and (0.01, 0.01) is approximately 1.57km
    pois = [
        POI(lat=0.0, lon=0.0, name="Toilet 1", distance_to_route=0.1, distance_on_route=0.0, 
            poi_type="public_toilets"),
        POI(lat=0.01, lon=0.01, name="Toilet 2", distance_to_route=0.15, distance_on_route=0.0, 
            poi_type="public_toilets"),
    ]
    
    # Deduplicate with 1km radius
    deduplicated = overpass_client.deduplicate_pois(pois, deduplication_radius_km=1.0)
    
    # Should keep both POIs
    assert len(deduplicated) == 2


def test_deduplication_different_types(overpass_client):
    """Test that POIs of different types are not deduplicated."""
    # Create POIs of different types close to each other
    pois = [
        POI(lat=0.0, lon=0.0, name="Toilet", distance_to_route=0.1, distance_on_route=0.0, 
            poi_type="public_toilets"),
        POI(lat=0.001, lon=0.001, name="Bakery", distance_to_route=0.15, distance_on_route=0.0, 
            poi_type="bakeries"),
    ]
    
    # Deduplicate with 1km radius
    deduplicated = overpass_client.deduplicate_pois(pois, deduplication_radius_km=1.0)
    
    # Should keep both POIs (different types)
    assert len(deduplicated) == 2


def test_deduplication_prefers_closer_to_route(overpass_client):
    """Test that when multiple POIs are within radius, the one closer to route is preferred."""
    # Create two POIs, neither is 24/7, but one is closer to route
    pois = [
        POI(lat=0.0, lon=0.0, name="Toilet 1", distance_to_route=0.2, distance_on_route=0.0, 
            poi_type="public_toilets", opening_hours="Mo-Fr 09:00-17:00"),
        POI(lat=0.001, lon=0.001, name="Toilet 2", distance_to_route=0.1, distance_on_route=0.0, 
            poi_type="public_toilets", opening_hours="Mo-Fr 09:00-17:00"),
    ]
    
    # Deduplicate with 1km radius
    deduplicated = overpass_client.deduplicate_pois(pois, deduplication_radius_km=1.0)
    
    # Should keep only one POI (closer to route)
    assert len(deduplicated) == 1
    assert deduplicated[0].name == "Toilet 2"  # Closer to route
    assert deduplicated[0].distance_to_route == 0.1


def test_deduplication_prefers_closest_with_longest_hours(overpass_client):
    """Test that closest POI is preferred, and when distance is equal, longest opening hours are preferred."""
    # Create two POIs with same distance but different opening hours
    pois = [
        POI(lat=0.0, lon=0.0, name="Toilet 1", distance_to_route=0.1, distance_on_route=0.0, 
            poi_type="public_toilets", opening_hours="24/7"),
        POI(lat=0.001, lon=0.001, name="Toilet 2", distance_to_route=0.1, distance_on_route=0.0, 
            poi_type="public_toilets", opening_hours="Mo-Fr 09:00-17:00"),
    ]
    
    # Deduplicate with 1km radius
    deduplicated = overpass_client.deduplicate_pois(pois, deduplication_radius_km=1.0)
    
    # Should keep the one with longest opening hours (24/7) when distance is equal
    assert len(deduplicated) == 1
    assert deduplicated[0].name == "Toilet 1"  # 24/7 preferred (longer hours)
    assert deduplicated[0].opening_hours == "24/7"


def test_deduplication_gas_stations(overpass_client):
    """Test that gas stations are deduplicated when within radius."""
    # Create multiple gas stations close together (within 1km)
    pois = [
        POI(lat=0.0, lon=0.0, name="Gas 1", distance_to_route=0.1, distance_on_route=0.0, 
            poi_type="gas_stations", opening_hours="24/7"),
        POI(lat=0.001, lon=0.001, name="Gas 2", distance_to_route=0.15, distance_on_route=0.0, 
            poi_type="gas_stations", opening_hours="Mo-Fr 09:00-17:00"),
    ]
    
    # Deduplicate with 1km radius
    deduplicated = overpass_client.deduplicate_pois(pois, deduplication_radius_km=1.0)
    
    # Should keep only one (gas_stations are now in deduplicate_types)
    assert len(deduplicated) == 1
    # Should prefer the one with longer opening hours when distance is similar
    assert deduplicated[0].opening_hours == "24/7"


def test_deduplication_with_per_poi_settings(overpass_client):
    """Test deduplication with per-POI-type settings."""
    # Create two POIs very close
    pois = [
        POI(lat=0.0, lon=0.0, name="Toilet 1", distance_to_route=0.1, distance_on_route=0.0, 
            poi_type="public_toilets"),
        POI(lat=0.001, lon=0.001, name="Toilet 2", distance_to_route=0.15, distance_on_route=0.0, 
            poi_type="public_toilets"),
    ]
    
    # Use per-POI settings with very small radius (0.1km = 100m)
    poi_settings = {
        "public_toilets": {
            "deduplication_radius_km": 0.1  # 100 meters
        }
    }
    
    # Distance between POIs is ~0.157km, so with 0.1km radius they should both be kept
    deduplicated = overpass_client.deduplicate_pois(pois, deduplication_radius_km=1.0, poi_settings=poi_settings)
    
    # Should keep both (they're outside the 0.1km radius)
    assert len(deduplicated) == 2


def test_deduplication_camping_hotels(overpass_client):
    """Test that camping_hotels are included in deduplication."""
    # Create two camping sites close to each other
    pois = [
        POI(lat=0.0, lon=0.0, name="Camp 1", distance_to_route=0.1, distance_on_route=0.0, 
            poi_type="camping_hotels", price_range="Free"),
        POI(lat=0.001, lon=0.001, name="Camp 2", distance_to_route=0.15, distance_on_route=0.0, 
            poi_type="camping_hotels", price_range="€10"),
    ]
    
    # Deduplicate with 1km radius
    deduplicated = overpass_client.deduplicate_pois(pois, deduplication_radius_km=1.0)
    
    # Should keep only one (camping_hotels is in deduplicate_types)
    assert len(deduplicated) == 1


def test_deduplication_multiple_groups(overpass_client):
    """Test deduplication with multiple groups of POIs."""
    # Create multiple groups: 2 toilets close, 2 bakeries close, 1 gas station
    # For each group, the closer one also has longer opening hours
    pois = [
        # Group 1: Two toilets close together - closer one has 24/7
        POI(lat=0.0, lon=0.0, name="Toilet 1", distance_to_route=0.1, distance_on_route=0.0, 
            poi_type="public_toilets", opening_hours="24/7"),
        POI(lat=0.001, lon=0.001, name="Toilet 2", distance_to_route=0.15, distance_on_route=0.0, 
            poi_type="public_toilets", opening_hours="Mo-Fr 09:00-17:00"),
        # Group 2: Two bakeries close together - closer one has 24/7
        POI(lat=0.01, lon=0.01, name="Bakery 1", distance_to_route=0.1, distance_on_route=0.0, 
            poi_type="bakeries", opening_hours="24/7"),
        POI(lat=0.011, lon=0.011, name="Bakery 2", distance_to_route=0.15, distance_on_route=0.0, 
            poi_type="bakeries", opening_hours="Mo-Fr 09:00-17:00"),
        # Group 3: Gas station (not deduplicated)
        POI(lat=0.02, lon=0.02, name="Gas 1", distance_to_route=0.1, distance_on_route=0.0, 
            poi_type="gas_stations"),
    ]
    
    # Deduplicate with 1km radius
    deduplicated = overpass_client.deduplicate_pois(pois, deduplication_radius_km=1.0)
    
    # Should have: 1 toilet (closer with 24/7), 1 bakery (closer with 24/7), 1 gas station = 3 total
    assert len(deduplicated) == 3
    # Verify types
    types = {poi.poi_type for poi in deduplicated}
    assert types == {"public_toilets", "bakeries", "gas_stations"}
    # Verify the closer ones with longer hours are kept
    for poi in deduplicated:
        if poi.poi_type in ["public_toilets", "bakeries"]:
            assert poi.opening_hours == "24/7"
            assert poi.distance_to_route == 0.1  # Closer one


def test_deduplication_prefers_branded_pois(overpass_client):
    """Test that branded/chain POIs are preferred when distance and opening hours are equal."""
    # Create two POIs with same distance and opening hours, but one is branded
    pois = [
        POI(lat=0.0, lon=0.0, name="Bakery 1", distance_to_route=0.1, distance_on_route=0.0, 
            poi_type="bakeries", opening_hours="Mo-Fr 09:00-17:00", brand="Brand A"),
        POI(lat=0.001, lon=0.001, name="Bakery 2", distance_to_route=0.1, distance_on_route=0.0, 
            poi_type="bakeries", opening_hours="Mo-Fr 09:00-17:00"),
    ]
    
    # Deduplicate with 1km radius
    deduplicated = overpass_client.deduplicate_pois(pois, deduplication_radius_km=1.0)
    
    # Should keep the branded one
    assert len(deduplicated) == 1
    assert deduplicated[0].name == "Bakery 1"
    assert deduplicated[0].brand == "Brand A"


def test_deduplication_prefers_notable_pois(overpass_client):
    """Test that POIs with wikipedia/wikidata are preferred when other factors are equal."""
    # Create two POIs with same distance, opening hours, and no brand, but one has wikipedia
    pois = [
        POI(lat=0.0, lon=0.0, name="Toilet 1", distance_to_route=0.1, distance_on_route=0.0, 
            poi_type="public_toilets", opening_hours="Mo-Fr 09:00-17:00", wikipedia="en:Toilet"),
        POI(lat=0.001, lon=0.001, name="Toilet 2", distance_to_route=0.1, distance_on_route=0.0, 
            poi_type="public_toilets", opening_hours="Mo-Fr 09:00-17:00"),
    ]
    
    # Deduplicate with 1km radius
    deduplicated = overpass_client.deduplicate_pois(pois, deduplication_radius_km=1.0)
    
    # Should keep the one with wikipedia
    assert len(deduplicated) == 1
    assert deduplicated[0].name == "Toilet 1"
    assert deduplicated[0].wikipedia == "en:Toilet"

