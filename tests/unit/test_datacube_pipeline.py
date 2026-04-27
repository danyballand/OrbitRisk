from datetime import date

import numpy as np
import xarray as xr

from orbitrisk.processing.datacube import summarize_datacube


def test_summarize_datacube_uses_time_axis_and_derived_data_mask() -> None:
    dataset = _dataset()
    dataset["B08"].values[0, 0, 0] = np.nan
    aoi_mask = np.ones((3, 3), dtype=bool)

    observations = summarize_datacube(
        dataset,
        aoi_mask=aoi_mask,
        requested_indices=["ndvi", "ndmi"],
        min_valid_pixels=5,
        min_clear_fraction=0.5,
    )

    assert [observation.observed_at for observation in observations] == [
        date(2022, 7, 1),
        date(2022, 7, 11),
    ]
    assert observations[0].stats.valid_pixel_count == 8
    assert observations[1].stats.valid_pixel_count == 9
    assert np.isclose(observations[0].stats.index_stats["ndvi"]["mean"], 0.5)


def test_summarize_datacube_respects_explicit_data_mask() -> None:
    dataset = _dataset()
    data_mask = np.ones((2, 3, 3), dtype=np.uint8)
    data_mask[:, 1, 1] = 0
    dataset["dataMask"] = (("time", "y", "x"), data_mask)

    observations = summarize_datacube(
        dataset,
        aoi_mask=np.ones((3, 3), dtype=bool),
        requested_indices=["ndwi"],
        min_valid_pixels=5,
        min_clear_fraction=0.5,
    )

    assert observations[0].stats.valid_pixel_count == 8
    assert "ndwi" in observations[0].stats.index_stats


def test_summarize_datacube_treats_nan_scl_as_nodata() -> None:
    dataset = _dataset()
    dataset["SCL"] = dataset["SCL"].astype(np.float32)
    dataset["SCL"].values[0, 0, 0] = np.nan

    observations = summarize_datacube(
        dataset,
        aoi_mask=np.ones((3, 3), dtype=bool),
        requested_indices=["ndvi"],
        min_valid_pixels=5,
        min_clear_fraction=0.5,
    )

    assert observations[0].stats.valid_pixel_count == 8


def test_summarize_datacube_rejects_missing_bands() -> None:
    dataset = _dataset().drop_vars("B11")

    try:
        summarize_datacube(
            dataset,
            aoi_mask=np.ones((3, 3), dtype=bool),
            requested_indices=["ndmi"],
            min_valid_pixels=5,
            min_clear_fraction=0.5,
        )
    except ValueError as exc:
        assert "B11" in str(exc)
    else:
        raise AssertionError("Expected missing band validation error")


def _dataset() -> xr.Dataset:
    shape = (2, 3, 3)
    coords = {
        "time": np.array(["2022-07-01", "2022-07-11"], dtype="datetime64[D]"),
        "y": np.arange(3),
        "x": np.arange(3),
    }
    return xr.Dataset(
        {
            "B03": (("time", "y", "x"), np.full(shape, 0.20, dtype=np.float32)),
            "B04": (("time", "y", "x"), np.full(shape, 0.20, dtype=np.float32)),
            "B05": (("time", "y", "x"), np.full(shape, 0.30, dtype=np.float32)),
            "B08": (("time", "y", "x"), np.full(shape, 0.60, dtype=np.float32)),
            "B11": (("time", "y", "x"), np.full(shape, 0.30, dtype=np.float32)),
            "SCL": (("time", "y", "x"), np.full(shape, 4, dtype=np.uint8)),
        },
        coords=coords,
    )
