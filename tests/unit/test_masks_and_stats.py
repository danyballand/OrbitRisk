import numpy as np

from orbitrisk.processing.cloud_mask import build_scl_valid_mask, summarize_scl_mask
from orbitrisk.processing.stats import aggregate_masked


def test_scl_mask_rejects_cloud_shadow_and_snow() -> None:
    scl = np.array([[4, 5, 8], [3, 11, 4]], dtype=np.uint8)

    valid = build_scl_valid_mask(scl)
    summary = summarize_scl_mask(scl, valid)

    assert valid.tolist() == [[True, True, False], [False, False, True]]
    assert summary.valid == 3
    assert summary.cloud == 1
    assert summary.shadow == 1
    assert summary.snow == 1


def test_aggregate_masked_requires_minimum_pixels() -> None:
    index = np.array([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32)
    valid = np.array([[True, False], [False, True]])

    assert aggregate_masked(index, valid, min_valid_pixels=3) is None

    stats = aggregate_masked(index, valid, min_valid_pixels=2)
    assert stats is not None
    assert np.isclose(stats["mean"], 0.25)
    assert np.isclose(stats["median"], 0.25)
