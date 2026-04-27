import numpy as np
from numpy.typing import NDArray


def robust_stats(values: NDArray[np.floating]) -> dict[str, float]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {
            "mean": float("nan"),
            "median": float("nan"),
            "p10": float("nan"),
            "p90": float("nan"),
            "std": float("nan"),
        }
    return {
        "mean": float(np.mean(finite)),
        "median": float(np.median(finite)),
        "p10": float(np.percentile(finite, 10)),
        "p90": float(np.percentile(finite, 90)),
        "std": float(np.std(finite)),
    }


def aggregate_masked(
    index: NDArray[np.floating],
    valid_mask: NDArray[np.bool_],
    *,
    min_valid_pixels: int,
) -> dict[str, float] | None:
    if index.shape != valid_mask.shape:
        raise ValueError("index and valid_mask must have identical shapes")
    if int(valid_mask.sum()) < min_valid_pixels:
        return None
    return robust_stats(np.where(valid_mask, index, np.nan))
