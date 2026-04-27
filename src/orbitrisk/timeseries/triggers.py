from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from orbitrisk.schemas.response import CriticalPeriod


@dataclass(frozen=True)
class TriggerResult:
    triggered: bool
    reason: str | None
    periods: list[CriticalPeriod]


def detect_water_stress_trigger(
    values: Sequence[float],
    *,
    threshold: float,
    min_consecutive: int,
    dates: Sequence[date] | None = None,
) -> TriggerResult:
    run_start: int | None = None
    run_length = 0
    periods: list[CriticalPeriod] = []

    for idx, value in enumerate(values):
        if value <= threshold:
            run_start = idx if run_start is None else run_start
            run_length += 1
            continue

        if run_start is not None and run_length >= min_consecutive:
            periods.append(_period_for_run(run_start, idx - 1, dates))
        run_start = None
        run_length = 0

    if run_start is not None and run_length >= min_consecutive:
        periods.append(_period_for_run(run_start, len(values) - 1, dates))

    triggered = bool(periods)
    reason = f"ndmi_ema_below_{threshold}_for_{min_consecutive}_periods" if triggered else None
    return TriggerResult(triggered=triggered, reason=reason, periods=periods)


def _period_for_run(start_idx: int, end_idx: int, dates: Sequence[date] | None) -> CriticalPeriod:
    if dates:
        start = dates[start_idx]
        end = dates[end_idx]
    else:
        start = date(1970, 1, 1)
        end = date(1970, 1, 1)
    return CriticalPeriod(start=start, end=end, severity="high")
