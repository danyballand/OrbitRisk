import numpy as np
from numpy.typing import NDArray


def simple_vegetation_mask(
    ndvi: NDArray[np.floating],
    *,
    min_ndvi: float = 0.25,
    max_ndwi: float | None = None,
    ndwi: NDArray[np.floating] | None = None,
) -> NDArray[np.bool_]:
    """Baseline crop mask for the POC.

    This is deliberately conservative and should be replaced or augmented with external
    parcel/crop layers before claiming semantic vineyard segmentation.
    """
    mask = np.isfinite(ndvi) & (ndvi >= min_ndvi)
    if max_ndwi is not None:
        if ndwi is None:
            raise ValueError("ndwi is required when max_ndwi is set")
        mask &= np.isfinite(ndwi) & (ndwi <= max_ndwi)
    return np.asarray(mask, dtype=bool)
