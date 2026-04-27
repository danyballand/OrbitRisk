from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import numpy as np
from numpy.typing import NDArray

from orbitrisk.processing.observation import ObservationStats, summarize_observation

REQUIRED_INDEX_BANDS: dict[str, set[str]] = {
    "ndvi": {"B04", "B08"},
    "ndwi": {"B03", "B08"},
    "ndmi": {"B08", "B11"},
    "ndre": {"B05", "B08"},
}


@dataclass(frozen=True)
class TimedObservationStats:
    observed_at: date
    stats: ObservationStats


def summarize_datacube(
    dataset: Any,
    *,
    aoi_mask: NDArray[np.bool_],
    requested_indices: list[str],
    min_valid_pixels: int,
    min_clear_fraction: float,
    exclude_scl_classes: set[int] | None = None,
    crop_mask: NDArray[np.bool_] | None = None,
) -> list[TimedObservationStats]:
    """Summarize an xarray Sentinel-2 datacube into auditable observations."""
    _validate_requested_bands(dataset, requested_indices)
    time_values = _time_values(dataset)
    observations: list[TimedObservationStats] = []

    for time_index, time_value in enumerate(time_values):
        bands = _extract_band_arrays(dataset, requested_indices, time_index)
        scl_raw = _extract_2d_array(dataset, "SCL", time_index)
        data_mask = _extract_data_mask(dataset, bands, scl_raw, time_index)
        scl = np.nan_to_num(scl_raw, nan=0).astype(np.uint8)
        observation = summarize_observation(
            bands=bands,
            scl=scl,
            data_mask=data_mask,
            aoi_mask=aoi_mask,
            crop_mask=crop_mask,
            requested_indices=requested_indices,
            min_valid_pixels=min_valid_pixels,
            min_clear_fraction=min_clear_fraction,
            exclude_scl_classes=exclude_scl_classes,
        )
        observations.append(
            TimedObservationStats(observed_at=_as_date(time_value), stats=observation)
        )

    return observations


def _validate_requested_bands(dataset: Any, requested_indices: list[str]) -> None:
    needed = {"SCL"}
    for index_name in requested_indices:
        try:
            needed |= REQUIRED_INDEX_BANDS[index_name]
        except KeyError as exc:
            raise ValueError(f"Unsupported index: {index_name}") from exc

    available = set(dataset.data_vars)
    missing = sorted(needed - available)
    if missing:
        raise ValueError(f"Datacube is missing required bands: {missing}")


def _time_values(dataset: Any) -> list[Any]:
    if "time" not in dataset.coords:
        return [None]
    values = dataset.coords["time"].values
    return list(np.atleast_1d(values))


def _extract_band_arrays(
    dataset: Any,
    requested_indices: list[str],
    time_index: int,
) -> dict[str, NDArray[np.floating]]:
    required_bands: set[str] = set()
    for index_name in requested_indices:
        required_bands |= REQUIRED_INDEX_BANDS[index_name]
    return {
        band: _extract_2d_array(dataset, band, time_index).astype(np.float32)
        for band in sorted(required_bands)
    }


def _extract_2d_array(dataset: Any, variable: str, time_index: int) -> NDArray[Any]:
    data_array = dataset[variable]
    if "time" in data_array.dims:
        data_array = data_array.isel(time=time_index)
    array = data_array.values
    if array.ndim != 2:
        raise ValueError(f"Expected 2D array for {variable}, got shape {array.shape}")
    return np.asarray(array)


def _extract_data_mask(
    dataset: Any,
    bands: dict[str, NDArray[np.floating]],
    scl: NDArray[np.integer],
    time_index: int,
) -> NDArray[np.bool_]:
    if "dataMask" in dataset.data_vars:
        return _extract_2d_array(dataset, "dataMask", time_index).astype(bool)

    mask = np.isfinite(scl)
    for band in bands.values():
        mask &= np.isfinite(band)
    return np.asarray(mask, dtype=bool)


def _as_date(value: Any) -> date:
    if value is None:
        return date.today()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(np.datetime_as_string(value, unit="D"))
