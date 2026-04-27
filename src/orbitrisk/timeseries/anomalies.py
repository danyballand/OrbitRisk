from collections.abc import Sequence

import numpy as np


def z_scores(values: Sequence[float]) -> list[float]:
    arr = np.asarray(values, dtype=np.float32)
    mean = float(np.nanmean(arr))
    std = float(np.nanstd(arr))
    if std == 0 or not np.isfinite(std):
        return [0.0 for _ in values]
    return [float((value - mean) / std) for value in arr]


def percentile_anomaly(value: float, baseline: Sequence[float]) -> float:
    base = np.asarray(baseline, dtype=np.float32)
    base = base[np.isfinite(base)]
    if base.size == 0:
        return float("nan")
    return float((base < value).sum() / base.size)
