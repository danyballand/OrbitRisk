import numpy as np

from orbitrisk.processing.cloud_mask import (
    SCL_CLOUD_HIGH_PROBABILITY,
    SCL_CLOUD_SHADOWS,
    SCL_SNOW_OR_ICE,
    SCL_VEGETATION,
)
from orbitrisk.processing.observation import summarize_observation


def test_summarize_observation_excludes_cloud_shadow_snow_and_non_crop() -> None:
    shape = (3, 3)
    bands = {
        "B03": np.full(shape, 0.20, dtype=np.float32),
        "B04": np.full(shape, 0.20, dtype=np.float32),
        "B05": np.full(shape, 0.30, dtype=np.float32),
        "B08": np.full(shape, 0.60, dtype=np.float32),
        "B11": np.full(shape, 0.30, dtype=np.float32),
    }
    scl = np.full(shape, SCL_VEGETATION, dtype=np.uint8)
    scl[0, 0] = SCL_CLOUD_HIGH_PROBABILITY
    scl[0, 1] = SCL_CLOUD_SHADOWS
    scl[0, 2] = SCL_SNOW_OR_ICE
    data_mask = np.ones(shape, dtype=np.uint8)
    aoi_mask = np.ones(shape, dtype=bool)
    crop_mask = np.ones(shape, dtype=bool)
    crop_mask[2, 2] = False

    summary = summarize_observation(
        bands=bands,
        scl=scl,
        data_mask=data_mask,
        aoi_mask=aoi_mask,
        crop_mask=crop_mask,
        requested_indices=["ndvi", "ndmi"],
        min_valid_pixels=4,
        min_clear_fraction=0.5,
    )

    assert summary.valid_pixel_count == 5
    assert summary.mask_counts["cloud"] == 1
    assert summary.mask_counts["shadow"] == 1
    assert summary.mask_counts["snow"] == 1
    assert summary.mask_counts["non_crop"] == 1
    assert np.isclose(summary.index_stats["ndvi"]["mean"], 0.5)
    assert np.isclose(summary.index_stats["ndmi"]["mean"], 1 / 3)
    assert summary.quality == "good"


def test_summarize_observation_rejects_too_few_pixels() -> None:
    shape = (2, 2)
    bands = {
        "B03": np.full(shape, 0.20, dtype=np.float32),
        "B04": np.full(shape, 0.20, dtype=np.float32),
        "B08": np.full(shape, 0.60, dtype=np.float32),
        "B11": np.full(shape, 0.30, dtype=np.float32),
    }
    summary = summarize_observation(
        bands=bands,
        scl=np.full(shape, SCL_VEGETATION, dtype=np.uint8),
        data_mask=np.ones(shape, dtype=np.uint8),
        aoi_mask=np.ones(shape, dtype=bool),
        requested_indices=["ndvi"],
        min_valid_pixels=5,
        min_clear_fraction=0.7,
    )

    assert summary.quality == "rejected"
    assert summary.index_stats == {}
