from dataclasses import dataclass
from datetime import date

import numpy as np

from orbitrisk.geo.aoi import PreparedAoi
from orbitrisk.geo.raster_grid import RasterGrid, grid_from_geometry
from orbitrisk.providers.base import ObservationQuery

SENTINEL2_L2A_BANDS = ("B03", "B04", "B05", "B08", "B11", "SCL")


@dataclass(frozen=True)
class PreparedRasterJob:
    grid: RasterGrid
    aoi_mask: np.ndarray
    query: ObservationQuery


def prepare_raster_job(
    prepared_aoi: PreparedAoi,
    *,
    date_start: date,
    date_end: date,
    resolution_m: int,
    max_cloud_cover_pct: float | None = 80.0,
    max_items: int | None = None,
) -> PreparedRasterJob:
    grid = grid_from_geometry(
        prepared_aoi.geometry_projected,
        crs=prepared_aoi.processing_crs,
        resolution_m=resolution_m,
    )
    query = ObservationQuery(
        bbox_wgs84=prepared_aoi.geometry_wgs84.bounds,
        date_start=date_start,
        date_end=date_end,
        output_crs=prepared_aoi.processing_crs.to_string(),
        resolution_m=resolution_m,
        bands=SENTINEL2_L2A_BANDS,
        max_cloud_cover_pct=max_cloud_cover_pct,
        max_items=max_items,
    )
    return PreparedRasterJob(
        grid=grid,
        aoi_mask=grid.mask(prepared_aoi.analysis_geometry),
        query=query,
    )
