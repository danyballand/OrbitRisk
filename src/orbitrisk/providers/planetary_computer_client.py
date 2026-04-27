from typing import TYPE_CHECKING, Any

from orbitrisk.providers.base import ObservationQuery

if TYPE_CHECKING:
    from orbitrisk.config import Settings


class PlanetaryComputerProvider:
    """STAC-first data provider for low-cost POC development.

    The implementation intentionally keeps imports inside methods so the numerical core
    remains importable even in minimal environments. Production serving can still use
    Sentinel Hub once the pipeline behavior is validated.
    """

    def __init__(self, settings: "Settings") -> None:
        self.settings = settings

    def enabled(self) -> bool:
        return self.settings.data_provider == "planetary-computer"

    def search_items(self, query: ObservationQuery) -> list[Any]:
        from pystac_client import Client

        catalog = Client.open(self.settings.planetary_computer_stac_url)
        search = catalog.search(
            collections=[self.settings.planetary_computer_collection],
            bbox=query.bbox_wgs84,
            datetime=f"{query.date_start.isoformat()}/{query.date_end.isoformat()}",
            query=_cloud_cover_query(query.max_cloud_cover_pct),
        )
        items: list[Any] = []
        for item in search.items():
            items.append(item)
            if query.max_items is not None and len(items) >= query.max_items:
                break
        return items

    def sign_items(self, items: list[Any]) -> list[Any]:
        import planetary_computer

        return [planetary_computer.sign(item) for item in items]

    def load_datacube(self, query: ObservationQuery, *, geobox: Any | None = None) -> Any:
        import odc.stac

        items = self.sign_items(self.search_items(query))
        if not items:
            raise ValueError("No Sentinel-2 items found for query")
        if geobox is not None:
            return odc.stac.load(
                items,
                bands=list(query.bands),
                geobox=geobox,
                chunks={},
            )
        return odc.stac.load(
            items,
            bands=list(query.bands),
            resolution=query.resolution_m,
            bbox=query.bbox_wgs84,
            crs=query.output_crs,
            chunks={},
        )


def _cloud_cover_query(max_cloud_cover_pct: float | None) -> dict[str, Any] | None:
    if max_cloud_cover_pct is None:
        return None
    return {"eo:cloud_cover": {"lt": max_cloud_cover_pct}}
