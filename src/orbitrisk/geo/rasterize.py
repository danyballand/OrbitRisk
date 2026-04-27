from collections.abc import Iterable

import numpy as np
from affine import Affine
from rasterio.features import geometry_mask
from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry


def rasterize_geometry_mask(
    geometries: Iterable[BaseGeometry],
    *,
    out_shape: tuple[int, int],
    transform: Affine,
    all_touched: bool = False,
) -> np.ndarray:
    """Return True for pixels inside the provided geometries."""
    return ~geometry_mask(
        [mapping(geometry) for geometry in geometries],
        out_shape=out_shape,
        transform=transform,
        invert=False,
        all_touched=all_touched,
    )
