from datetime import date

from orbitrisk.processing.datacube import TimedObservationStats
from orbitrisk.processing.observation import ObservationStats
from orbitrisk.timeseries.compositing import composite_observations


def test_composite_observations_selects_best_quality_then_pixels_then_cloud() -> None:
    observations = [
        _obs(date(2022, 7, 1), "poor", valid=900, cloud=5),
        _obs(date(2022, 7, 2), "good", valid=100, cloud=60),
        _obs(date(2022, 7, 3), "moderate", valid=2000, cloud=0),
        _obs(date(2022, 7, 4), "good", valid=500, cloud=10),
        _obs(date(2022, 7, 5), "good", valid=500, cloud=2),
    ]

    composites = composite_observations(
        observations,
        temporal="P10D",
        start=date(2022, 7, 1),
        end=date(2022, 7, 10),
    )

    assert len(composites) == 1
    assert composites[0].selected.observed_at == date(2022, 7, 5)
    assert composites[0].candidate_count == 5
    assert composites[0].accepted_candidate_count == 5
    assert composites[0].period == "2022-07-01/2022-07-10"


def test_composite_observations_tracks_rejected_candidates() -> None:
    composites = composite_observations(
        [
            _obs(date(2022, 7, 1), "rejected", valid=0, cloud=100, has_indices=False),
            _obs(date(2022, 7, 2), "good", valid=120, cloud=2),
        ],
        temporal="P10D",
        start=date(2022, 7, 1),
        end=date(2022, 7, 10),
    )

    assert composites[0].selected.observed_at == date(2022, 7, 2)
    assert composites[0].rejected_candidate_count == 1


def test_composite_observations_supports_monthly_buckets() -> None:
    composites = composite_observations(
        [
            _obs(date(2022, 7, 31), "good", valid=100, cloud=0),
            _obs(date(2022, 8, 1), "good", valid=100, cloud=0),
        ],
        temporal="P1M",
        start=date(2022, 7, 15),
        end=date(2022, 8, 15),
    )

    assert [composite.period for composite in composites] == [
        "2022-07-15/2022-07-31",
        "2022-08-01/2022-08-15",
    ]


def _obs(
    observed_at: date,
    quality: str,
    *,
    valid: int,
    cloud: float,
    has_indices: bool = True,
) -> TimedObservationStats:
    return TimedObservationStats(
        observed_at=observed_at,
        stats=ObservationStats(
            valid_pixel_count=valid,
            cloud_pct=cloud,
            quality=quality,
            index_stats={"ndmi": {"mean": 0.1}} if has_indices else {},
            mask_counts={
                "valid": valid,
                "cloud": int(cloud),
                "shadow": 0,
                "snow": 0,
                "outside_aoi": 0,
                "non_crop": 0,
            },
        ),
    )
