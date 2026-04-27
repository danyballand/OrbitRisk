from datetime import date

from orbitrisk.timeseries.baseline import seasonal_baseline


def test_seasonal_baseline_uses_prior_year_same_doy_window() -> None:
    dates = [
        date(2020, 7, 10),
        date(2021, 7, 12),
        date(2022, 7, 9),
        date(2023, 7, 11),
    ]
    values = [0.30, 0.28, 0.32, 0.12]

    result = seasonal_baseline(dates, values, window_days=5, min_samples=3, max_years=5)

    assert 3 in result
    assert result[3].baseline_count == 3
    assert result[3].percentile == 0.0
    assert result[3].z_score < -1.0


def test_seasonal_baseline_requires_enough_history() -> None:
    result = seasonal_baseline(
        [date(2022, 7, 10), date(2023, 7, 11)],
        [0.30, 0.12],
        window_days=5,
        min_samples=3,
    )

    assert result == {}
