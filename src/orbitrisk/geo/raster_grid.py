from dataclasses import dataclass
from math import ceil

import numpy as np
from affine import Affine
from pyproj import CRS
from rasterio.transform import array_bounds, from_origin
from shapely.geometry.base import BaseGeometry

from orbitrisk.geo.rasterize import rasterize_geometry_mask


@dataclass(frozen=True)
class RasterGrid:
    crs: CRS
    transform: Affine
    width: int
    height: int
    resolution_m: float

    @property
    def shape(self) -> tuple[int, int]:
        return (self.height, self.width)

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        south, west, north, east = array_bounds(self.height, self.width, self.transform)
        return west, south, east, north

    def mask(self, geometry: BaseGeometry, *, all_touched: bool = False) -> np.ndarray:
        return rasterize_geometry_mask(
            [geometry],
            out_shape=self.shape,
            transform=self.transform,
            all_touched=all_touched,
        )


def grid_from_geometry(
    geometry: BaseGeometry,
    *,
    crs: CRS,
    resolution_m: float,
    padding_m: float = 0.0,
) -> RasterGrid:
    minx, miny, maxx, maxy = geometry.bounds
    minx -= padding_m
    miny -= padding_m
    maxx += padding_m
    maxy += padding_m

    width = max(1, ceil((maxx - minx) / resolution_m))
    height = max(1, ceil((maxy - miny) / resolution_m))
    transform = from_origin(minx, maxy, resolution_m, resolution_m)

    return RasterGrid(
        crs=crs,
        transform=transform,
        width=width,
        height=height,
        resolution_m=resolution_m,
    )
