from __future__ import annotations

from pyproj import CRS
from shapely.geometry.base import BaseGeometry


def utm_crs_for_lonlat(lon: float, lat: float) -> CRS:
    zone = int((lon + 180) // 6) + 1
    epsg = 32600 + zone if lat >= 0 else 32700 + zone
    return CRS.from_epsg(epsg)


def best_utm_crs_for_geometry(geometry: BaseGeometry) -> CRS:
    centroid = geometry.centroid
    return utm_crs_for_lonlat(float(centroid.x), float(centroid.y))


def normalize_crs(value: str) -> CRS:
    return CRS.from_user_input(value)
