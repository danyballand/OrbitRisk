from collections.abc import Mapping

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.floating]

EPSILON = np.float32(1e-6)


def normalized_difference(
    left: FloatArray,
    right: FloatArray,
    *,
    nodata_mask: NDArray[np.bool_] | None = None,
) -> FloatArray:
    """Compute a stable normalized difference for two reflectance bands."""
    numerator = left.astype(np.float32) - right.astype(np.float32)
    denominator = left.astype(np.float32) + right.astype(np.float32)
    out = numerator / np.where(np.abs(denominator) < EPSILON, np.nan, denominator)
    if nodata_mask is not None:
        out = np.where(nodata_mask, np.nan, out)
    return out.astype(np.float32)


def ndvi(
    red: FloatArray,
    nir: FloatArray,
    *,
    nodata_mask: NDArray[np.bool_] | None = None,
) -> FloatArray:
    return normalized_difference(nir, red, nodata_mask=nodata_mask)


def ndwi(
    green: FloatArray,
    nir: FloatArray,
    *,
    nodata_mask: NDArray[np.bool_] | None = None,
) -> FloatArray:
    return normalized_difference(green, nir, nodata_mask=nodata_mask)


def ndmi(
    nir: FloatArray,
    swir: FloatArray,
    *,
    nodata_mask: NDArray[np.bool_] | None = None,
) -> FloatArray:
    return normalized_difference(nir, swir, nodata_mask=nodata_mask)


def ndre(
    red_edge: FloatArray,
    nir: FloatArray,
    *,
    nodata_mask: NDArray[np.bool_] | None = None,
) -> FloatArray:
    return normalized_difference(nir, red_edge, nodata_mask=nodata_mask)


def compute_indices(
    bands: Mapping[str, FloatArray],
    requested: list[str],
    *,
    nodata_mask: NDArray[np.bool_] | None = None,
) -> dict[str, FloatArray]:
    """Compute known Sentinel-2 indices from named bands.

    Expected Sentinel-2 keys:
    - B03 green at 10 m
    - B04 red at 10 m
    - B05 red-edge at 20 m
    - B08 NIR at 10 m
    - B11 SWIR at 20 m
    """
    outputs: dict[str, FloatArray] = {}
    for name in requested:
        if name == "ndvi":
            outputs[name] = ndvi(bands["B04"], bands["B08"], nodata_mask=nodata_mask)
        elif name == "ndwi":
            outputs[name] = ndwi(bands["B03"], bands["B08"], nodata_mask=nodata_mask)
        elif name == "ndmi":
            outputs[name] = ndmi(bands["B08"], bands["B11"], nodata_mask=nodata_mask)
        elif name == "ndre":
            outputs[name] = ndre(bands["B05"], bands["B08"], nodata_mask=nodata_mask)
        else:
            raise ValueError(f"Unsupported index: {name}")
    return outputs
