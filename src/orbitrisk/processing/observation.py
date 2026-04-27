from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from orbitrisk.processing.cloud_mask import (
    SCL_CLOUD_HIGH_PROBABILITY,
    SCL_CLOUD_MEDIUM_PROBABILITY,
    SCL_CLOUD_SHADOWS,
    SCL_SNOW_OR_ICE,
    SCL_THIN_CIRRUS,
    build_scl_valid_mask,
)
from orbitrisk.processing.indices import compute_indices
from orbitrisk.processing.stats import aggregate_masked


@dataclass(frozen=True)
class ObservationStats:
    valid_pixel_count: int
    cloud_pct: float
    quality: str
    index_stats: dict[str, dict[str, float]]
    mask_counts: dict[str, int]


def summarize_observation(
    *,
    bands: dict[str, NDArray[np.floating]],
    scl: NDArray[np.integer],
    data_mask: NDArray[np.integer | np.bool_],
    aoi_mask: NDArray[np.bool_],
    requested_indices: list[str],
    min_valid_pixels: int,
    min_clear_fraction: float,
    exclude_scl_classes: set[int] | None = None,
    crop_mask: NDArray[np.bool_] | None = None,
) -> ObservationStats:
    shape = _common_shape(bands, scl, data_mask, aoi_mask, crop_mask)
    scl_valid = build_scl_valid_mask(scl, exclude_classes=exclude_scl_classes)
    data_valid = data_mask.astype(bool)
    crop_valid = crop_mask if crop_mask is not None else np.ones(shape, dtype=bool)

    inside_aoi = aoi_mask & data_valid
    valid_mask = inside_aoi & scl_valid & crop_valid
    valid_pixel_count = int(valid_mask.sum())
    inside_count = int(inside_aoi.sum())

    cloud_count = _count_classes(
        scl,
        inside_aoi,
        {SCL_CLOUD_MEDIUM_PROBABILITY, SCL_CLOUD_HIGH_PROBABILITY, SCL_THIN_CIRRUS},
    )
    shadow_count = _count_classes(scl, inside_aoi, {SCL_CLOUD_SHADOWS})
    snow_count = _count_classes(scl, inside_aoi, {SCL_SNOW_OR_ICE})
    non_crop_count = int((inside_aoi & ~crop_valid).sum()) if crop_mask is not None else 0
    outside_aoi_count = int((~aoi_mask).sum())

    indices = compute_indices(bands, requested_indices, nodata_mask=~data_valid)
    index_stats: dict[str, dict[str, float]] = {}
    for name, index in indices.items():
        stats = aggregate_masked(index, valid_mask, min_valid_pixels=min_valid_pixels)
        if stats is not None:
            index_stats[name] = stats

    clear_fraction = valid_pixel_count / inside_count if inside_count else 0.0
    cloud_pct = 100 * cloud_count / inside_count if inside_count else 100.0
    quality = _quality(
        valid_pixel_count=valid_pixel_count,
        min_valid_pixels=min_valid_pixels,
        clear_fraction=clear_fraction,
        min_clear_fraction=min_clear_fraction,
        cloud_pct=cloud_pct,
    )

    return ObservationStats(
        valid_pixel_count=valid_pixel_count,
        cloud_pct=cloud_pct,
        quality=quality,
        index_stats=index_stats,
        mask_counts={
            "valid": valid_pixel_count,
            "cloud": cloud_count,
            "shadow": shadow_count,
            "snow": snow_count,
            "outside_aoi": outside_aoi_count,
            "non_crop": non_crop_count,
        },
    )


def _common_shape(
    bands: dict[str, NDArray[np.floating]],
    scl: NDArray[np.integer],
    data_mask: NDArray[np.integer | np.bool_],
    aoi_mask: NDArray[np.bool_],
    crop_mask: NDArray[np.bool_] | None,
) -> tuple[int, int]:
    arrays: list[NDArray[np.generic]] = [scl, data_mask, aoi_mask, *bands.values()]
    if crop_mask is not None:
        arrays.append(crop_mask)
    shapes = {array.shape for array in arrays}
    if len(shapes) != 1:
        raise ValueError(f"All observation arrays must have the same shape, got {shapes}")
    return next(iter(shapes))


def _count_classes(
    scl: NDArray[np.integer],
    mask: NDArray[np.bool_],
    classes: set[int],
) -> int:
    return int((mask & np.isin(scl, list(classes))).sum())


def _quality(
    *,
    valid_pixel_count: int,
    min_valid_pixels: int,
    clear_fraction: float,
    min_clear_fraction: float,
    cloud_pct: float,
) -> str:
    if valid_pixel_count < min_valid_pixels:
        return "rejected"
    if clear_fraction < min_clear_fraction:
        return "poor"
    if cloud_pct > 15:
        return "moderate"
    return "good"
