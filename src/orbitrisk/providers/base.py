from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ObservationQuery:
    bbox_wgs84: tuple[float, float, float, float]
    date_start: date
    date_end: date
    output_crs: str
    resolution_m: int
    bands: tuple[str, ...]
    max_cloud_cover_pct: float | None = None
