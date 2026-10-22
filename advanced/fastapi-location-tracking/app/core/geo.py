import math

_EARTH_RADIUS_M = 6_371_000.0


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters (teaching helper; not for sub-meter surveying)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(a))


def inside_geofence(
    *,
    lat: float,
    lon: float,
    center_lat: float,
    center_lon: float,
    radius_m: float,
) -> bool:
    return haversine_meters(lat, lon, center_lat, center_lon) <= radius_m
