from dataclasses import dataclass
from typing import Any

from pyproj import CRS, Transformer
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

from orbitrisk.geo.crs import best_utm_crs_for_geometry, normalize_crs
from orbitrisk.masking.edge_buffer import apply_negative_buffer

WGS84 = CRS.from_epsg(4326)


@dataclass(frozen=True)
class PreparedAoi:
    source_crs: CRS
    processing_crs: CRS
    geometry_source: BaseGeometry
    geometry_wgs84: BaseGeometry
    geometry_projected: BaseGeometry
    analysis_geometry: BaseGeometry
    area_ha: float
    usable_area_ha: float
    masked_area_pct: float


def geometry_from_feature(feature: dict[str, Any]) -> BaseGeometry:
    if feature.get("type") != "Feature":
        raise ValueError("AOI must be a GeoJSON Feature")
    geometry = shape(feature.get("geometry"))
    if geometry.is_empty:
        raise ValueError("AOI geometry is empty")
    if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
        raise ValueError("AOI geometry must be Polygon or MultiPolygon")
    if not geometry.is_valid:
        raise ValueError("AOI geometry is invalid")
    return geometry


def reproject_geometry(geometry: BaseGeometry, source_crs: CRS, target_crs: CRS) -> BaseGeometry:
    if source_crs == target_crs:
        return geometry
    transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
    return transform(transformer.transform, geometry)


def prepare_aoi(
    feature: dict[str, Any],
    *,
    source_crs: str = "EPSG:4326",
    negative_buffer_m: float = 0.0,
    processing_crs: str | None = None,
) -> PreparedAoi:
    source = normalize_crs(source_crs)
    geometry_source = geometry_from_feature(feature)
    geometry_wgs84 = reproject_geometry(geometry_source, source, WGS84)
    target = (
        normalize_crs(processing_crs)
        if processing_crs
        else best_utm_crs_for_geometry(geometry_wgs84)
    )
    geometry_projected = reproject_geometry(geometry_wgs84, WGS84, target)
    analysis_geometry = apply_negative_buffer(geometry_projected, negative_buffer_m)

    area_ha = geometry_projected.area / 10_000
    usable_area_ha = analysis_geometry.area / 10_000
    masked_area_pct = 0.0 if area_ha == 0 else (1 - usable_area_ha / area_ha) * 100

    return PreparedAoi(
        source_crs=source,
        processing_crs=target,
        geometry_source=geometry_source,
        geometry_wgs84=geometry_wgs84,
        geometry_projected=geometry_projected,
        analysis_geometry=analysis_geometry,
        area_ha=area_ha,
        usable_area_ha=usable_area_ha,
        masked_area_pct=masked_area_pct,
    )
