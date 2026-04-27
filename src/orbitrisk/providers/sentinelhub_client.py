from dataclasses import dataclass
from datetime import date
from typing import Any

from orbitrisk.config import Settings


@dataclass(frozen=True)
class SentinelHubRequest:
    bbox: tuple[float, float, float, float]
    date_start: date
    date_end: date
    resolution_m: int
    bands: tuple[str, ...]


class SentinelHubProvider:
    """Boundary for Sentinel Hub Process/Statistical API calls.

    Keep IO here and keep raster math in `processing/` so the numerical core remains
    testable without network credentials.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def enabled(self) -> bool:
        return self.settings.sentinelhub_enabled

    def build_evalscript(self, bands: tuple[str, ...]) -> str:
        output_bands = ", ".join([f'"{band}"' for band in bands])
        sample_values = ", ".join([f"sample.{band}" for band in bands])
        return f"""
//VERSION=3
function setup() {{
  return {{
    input: [{output_bands}, "SCL", "dataMask"],
    output: {{ bands: {len(bands) + 2}, sampleType: "FLOAT32" }}
  }};
}}

function evaluatePixel(sample) {{
  return [{sample_values}, sample.SCL, sample.dataMask];
}}
""".strip()

    async def fetch_process_geotiff(self, request: SentinelHubRequest) -> bytes:
        raise NotImplementedError("Sentinel Hub Process API integration is next in the POC plan")

    async def fetch_statistical_series(self, request: SentinelHubRequest) -> dict[str, Any]:
        raise NotImplementedError(
            "Sentinel Hub Statistical API integration is next in the POC plan"
        )
