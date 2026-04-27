from collections.abc import Sequence


def ema(values: Sequence[float], *, alpha: float) -> list[float]:
    if not 0 < alpha <= 1:
        raise ValueError("alpha must be in (0, 1]")
    smoothed: list[float] = []
    previous: float | None = None
    for value in values:
        current = (
            float(value)
            if previous is None
            else alpha * float(value) + (1 - alpha) * previous
        )
        smoothed.append(current)
        previous = current
    return smoothed
