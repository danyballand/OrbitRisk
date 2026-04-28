from datetime import date

import numpy as np

from orbitrisk.timeseries.anomalies import z_scores
from orbitrisk.timeseries.smoothing import ema
from orbitrisk.timeseries.triggers import detect_water_stress_trigger


def test_ema() -> None:
    assert ema([1.0, 0.0, 0.0], alpha=0.5) == [1.0, 0.5, 0.25]


def test_z_scores_center_series() -> None:
    scores = z_scores([1.0, 2.0, 3.0])

    assert np.isclose(sum(scores), 0.0)


def test_trigger_detects_consecutive_low_values() -> None:
    result = detect_water_stress_trigger(
        [0.25, 0.14, 0.13, 0.20],
        threshold=0.15,
        min_consecutive=2,
        dates=[date(2025, 7, 1), date(2025, 7, 11), date(2025, 7, 21), date(2025, 8, 1)],
    )

    assert result.triggered
    assert result.reason == "ndmi_ema_below_0.15_for_2_periods"
    assert result.periods[0].start == date(2025, 7, 11)
    assert result.periods[0].end == date(2025, 7, 21)


def test_trigger_reason_formats_float_threshold_stably() -> None:
    result = detect_water_stress_trigger(
        [0.14, 0.13],
        threshold=0.15000000000000002,
        min_consecutive=2,
    )

    assert result.triggered
    assert result.reason == "ndmi_ema_below_0.15_for_2_periods"


def test_trigger_reason_is_none_without_trigger() -> None:
    result = detect_water_stress_trigger(
        [0.25, 0.14, 0.20],
        threshold=0.15,
        min_consecutive=2,
    )

    assert not result.triggered
    assert result.reason is None
