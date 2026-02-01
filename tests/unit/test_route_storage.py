from Backend.route_storage import RouteStorage, Route, RoutePoint

def test_multiple_route_storage():
    """ Test storing multiple routes and retrieving them correctly."""
    storage = RouteStorage()
    points1 = [RoutePoint(lat=10.0, lon=20.0)]
    points2 = [RoutePoint(lat=15.0, lon=25.0)]
    
    route_id1 = storage.store(points1)
    route_id2 = storage.store(points2)
    
    assert route_id1 != route_id2

    route1 = storage.get(route_id1)
    route2 = storage.get(route_id2)
    
    assert route1.points[0].lat == 10.0 # type: ignore
    assert route2.points[0].lat == 15.0 # type: ignore

def test_store():
    """ Test storing a route and verifying its contents."""
    storage = RouteStorage()
    points = [RoutePoint(lat=42, lon=-42) for _ in range(100)]

    route_id = storage.store(points)
    
    assert route_id is not None
    assert storage._routes[route_id].points == points
    assert len(storage._routes[route_id].points) == 100
    assert len(storage._routes) == 1
    assert storage._routes[route_id].id == route_id
    assert isinstance(storage._routes[route_id], Route)

def test_get():
    """ Test retrieving a stored route by its ID."""
    storage = RouteStorage()
    points = [RoutePoint(lat=1, lon=1), RoutePoint(lat=2, lon=2)]
    route_id = storage.store(points)
    
    retrieved_route = storage.get(route_id)

    assert isinstance(retrieved_route, Route)
    assert retrieved_route.id == route_id
    assert retrieved_route.points == points