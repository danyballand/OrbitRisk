from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from orbitrisk.geo.aoi import reproject_geometry
from orbitrisk.geo.crs import normalize_crs
from orbitrisk.geo.raster_grid import RasterGrid


@dataclass(frozen=True)
class VectorCropMask:
    mask: NDArray[np.bool_]
    geometry_count: int
    crop_pixel_count: int
    crop_coverage_fraction: float


def crop_mask_from_geojson(
    document: dict[str, Any],
    *,
    source_crs: str,
    grid: RasterGrid,
    clip_geometry: BaseGeometry | None = None,
    all_touched: bool = False,
) -> VectorCropMask:
    source = normalize_crs(source_crs)
    geometries = [
        reproject_geometry(geometry, source, grid.crs)
        for geometry in polygonal_geometries(document)
    ]
    if not geometries:
        empty = np.zeros(grid.shape, dtype=bool)
        return VectorCropMask(
            mask=empty,
            geometry_count=0,
            crop_pixel_count=0,
            crop_coverage_fraction=0.0,
        )

    merged = unary_union(geometries)
    if clip_geometry is not None:
        merged = merged.intersection(clip_geometry)
    if merged.is_empty:
        mask = np.zeros(grid.shape, dtype=bool)
    else:
        mask = grid.mask(merged, all_touched=all_touched)

    crop_pixels = int(mask.sum())
    return VectorCropMask(
        mask=mask,
        geometry_count=len(geometries),
        crop_pixel_count=crop_pixels,
        crop_coverage_fraction=crop_pixels / mask.size if mask.size else 0.0,
    )


def polygonal_geometries(document: dict[str, Any]) -> list[BaseGeometry]:
    document_type = document.get("type")
    if document_type == "Feature":
        return [_validated_polygonal(shape(document.get("geometry")))]
    if document_type == "FeatureCollection":
        return [
            _validated_polygonal(shape(feature.get("geometry")))
            for feature in document.get("features", [])
        ]
    if document_type in {"Polygon", "MultiPolygon"}:
        return [_validated_polygonal(shape(document))]
    raise ValueError(
        "Crop mask GeoJSON must be Feature, FeatureCollection, Polygon, or MultiPolygon"
    )


def _validated_polygonal(geometry: BaseGeometry) -> BaseGeometry:
    if geometry.is_empty:
        raise ValueError("Crop mask geometry is empty")
    if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
        raise ValueError("Crop mask geometry must be Polygon or MultiPolygon")
    if not geometry.is_valid:
        raise ValueError("Crop mask geometry is invalid")
    return geometry
