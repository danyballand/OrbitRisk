from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from operator import attrgetter

from orbitrisk.processing.datacube import TimedObservationStats

QUALITY_RANK = {
    "rejected": 0,
    "poor": 1,
    "moderate": 2,
    "good": 3,
}


@dataclass(frozen=True)
class CompositeObservation:
    period_start: date
    period_end: date
    selected: TimedObservationStats
    candidate_count: int
    accepted_candidate_count: int
    rejected_candidate_count: int

    @property
    def period(self) -> str:
        return f"{self.period_start.isoformat()}/{self.period_end.isoformat()}"


def composite_observations(
    observations: Iterable[TimedObservationStats],
    *,
    temporal: str,
    start: date | None = None,
    end: date | None = None,
) -> list[CompositeObservation]:
    observations_list = sorted(observations, key=attrgetter("observed_at"))
    if not observations_list:
        return []

    anchor = start or observations_list[0].observed_at
    final_date = end or observations_list[-1].observed_at
    buckets: dict[tuple[date, date], list[TimedObservationStats]] = defaultdict(list)

    for observation in observations_list:
        if observation.observed_at < anchor or observation.observed_at > final_date:
            continue
        buckets[_period_bounds(observation.observed_at, temporal, anchor, final_date)].append(
            observation
        )

    composites: list[CompositeObservation] = []
    for (period_start, period_end), candidates in sorted(buckets.items()):
        selected = max(candidates, key=_selection_score)
        accepted = [candidate for candidate in candidates if candidate.stats.quality != "rejected"]
        composites.append(
            CompositeObservation(
                period_start=period_start,
                period_end=period_end,
                selected=selected,
                candidate_count=len(candidates),
                accepted_candidate_count=len(accepted),
                rejected_candidate_count=len(candidates) - len(accepted),
            )
        )
    return composites


def _selection_score(observation: TimedObservationStats) -> tuple[int, int, int, float, date]:
    stats = observation.stats
    has_indices = int(bool(stats.index_stats))
    return (
        QUALITY_RANK.get(stats.quality, 0),
        has_indices,
        stats.valid_pixel_count,
        -stats.cloud_pct,
        observation.observed_at,
    )


def _period_bounds(
    observed_at: date,
    temporal: str,
    anchor: date,
    final_date: date,
) -> tuple[date, date]:
    if temporal == "P1M":
        period_start = observed_at.replace(day=1)
        period_end = _month_end(observed_at)
    elif temporal.startswith("P") and temporal.endswith("D"):
        days = int(temporal.removeprefix("P").removesuffix("D"))
        if days <= 0:
            raise ValueError("Temporal aggregation duration must be positive")
        offset = (observed_at - anchor).days // days
        period_start = anchor + timedelta(days=offset * days)
        period_end = period_start + timedelta(days=days - 1)
    else:
        raise ValueError(f"Unsupported temporal aggregation: {temporal}")

    return max(period_start, anchor), min(period_end, final_date)


def _month_end(value: date) -> date:
    if value.month == 12:
        return date(value.year, 12, 31)
    return date(value.year, value.month + 1, 1) - timedelta(days=1)
