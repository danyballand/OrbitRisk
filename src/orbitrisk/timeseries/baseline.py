from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

import numpy as np


@dataclass(frozen=True)
class SeasonalBaselinePoint:
    percentile: float
    z_score: float
    baseline_count: int


def seasonal_baseline(
    dates: Sequence[date],
    values: Sequence[float],
    *,
    window_days: int = 20,
    min_samples: int = 3,
    max_years: int | None = None,
) -> dict[int, SeasonalBaselinePoint]:
    if len(dates) != len(values):
        raise ValueError("dates and values must have the same length")
    if window_days < 0:
        raise ValueError("window_days must be non-negative")
    if min_samples < 1:
        raise ValueError("min_samples must be positive")

    results: dict[int, SeasonalBaselinePoint] = {}
    for idx, (current_date, current_value) in enumerate(zip(dates, values, strict=True)):
        baseline_values = [
            candidate_value
            for candidate_date, candidate_value in zip(dates, values, strict=True)
            if _is_baseline_candidate(current_date, candidate_date, max_years=max_years)
            and _day_distance(current_date, candidate_date) <= window_days
            and np.isfinite(candidate_value)
        ]
        if len(baseline_values) < min_samples or not np.isfinite(current_value):
            continue
        baseline = np.asarray(baseline_values, dtype=np.float32)
        std = float(np.std(baseline))
        z_score = 0.0 if std == 0 else float((current_value - float(np.mean(baseline))) / std)
        percentile = float((baseline < current_value).sum() / baseline.size)
        results[idx] = SeasonalBaselinePoint(
            percentile=percentile,
            z_score=z_score,
            baseline_count=int(baseline.size),
        )
    return results


def _is_baseline_candidate(
    current_date: date,
    candidate_date: date,
    *,
    max_years: int | None,
) -> bool:
    if candidate_date >= current_date:
        return False
    if candidate_date.year == current_date.year:
        return False
    return not (max_years is not None and current_date.year - candidate_date.year > max_years)


def _day_distance(left: date, right: date) -> int:
    left_doy = left.timetuple().tm_yday
    right_doy = right.timetuple().tm_yday
    raw = abs(left_doy - right_doy)
    return min(raw, 366 - raw)
