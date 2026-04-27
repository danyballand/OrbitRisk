from datetime import date
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
        if _should_use_year_stratified_search(query):
            return self._search_items_by_year(catalog, query)

        return self._search_items_for_range(
            catalog,
            query,
            date_start=query.date_start,
            date_end=query.date_end,
            limit=query.max_items,
        )

    def _search_items_by_year(self, catalog: Any, query: ObservationQuery) -> list[Any]:
        slices = _seasonal_year_slices(query.date_start, query.date_end)
        budgets = _allocate_item_budgets(query.max_items or 0, len(slices))
        items: list[Any] = []
        for (date_start, date_end), budget in zip(slices, budgets, strict=True):
            if budget <= 0:
                continue
            candidates = self._search_items_for_range(
                catalog,
                query,
                date_start=date_start,
                date_end=date_end,
                limit=None,
            )
            items.extend(_sample_evenly(_sort_items_by_datetime(candidates), budget))
        return _sort_items_by_datetime(items)

    def _search_items_for_range(
        self,
        catalog: Any,
        query: ObservationQuery,
        *,
        date_start: date,
        date_end: date,
        limit: int | None,
    ) -> list[Any]:
        search = catalog.search(
            collections=[self.settings.planetary_computer_collection],
            bbox=query.bbox_wgs84,
            datetime=f"{date_start.isoformat()}/{date_end.isoformat()}",
            query=_cloud_cover_query(query.max_cloud_cover_pct),
        )
        items: list[Any] = []
        for item in search.items():
            items.append(item)
            if limit is not None and len(items) >= limit:
                break
        return _sort_items_by_datetime(items)

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


def _should_use_year_stratified_search(query: ObservationQuery) -> bool:
    return (
        query.max_items is not None
        and query.max_items > 0
        and query.date_start.year < query.date_end.year
        and (query.date_start.month, query.date_start.day)
        <= (query.date_end.month, query.date_end.day)
    )


def _seasonal_year_slices(date_start: date, date_end: date) -> list[tuple[date, date]]:
    slices: list[tuple[date, date]] = []
    for year in range(date_start.year, date_end.year + 1):
        start = date(year, date_start.month, date_start.day)
        end = date(year, date_end.month, date_end.day)
        slices.append((max(start, date_start), min(end, date_end)))
    return [(start, end) for start, end in slices if start <= end]


def _allocate_item_budgets(max_items: int, slice_count: int) -> list[int]:
    if max_items <= 0 or slice_count <= 0:
        return []
    base = max_items // slice_count
    remainder = max_items % slice_count
    budgets = [base for _ in range(slice_count)]
    for index in range(slice_count - 1, -1, -1):
        if remainder <= 0:
            break
        budgets[index] += 1
        remainder -= 1
    return budgets


def _sort_items_by_datetime(items: list[Any]) -> list[Any]:
    return sorted(items, key=_item_datetime_key)


def _sample_evenly(items: list[Any], limit: int) -> list[Any]:
    if limit <= 0:
        return []
    if len(items) <= limit:
        return items
    if limit == 1:
        return [items[len(items) // 2]]

    selected: list[Any] = []
    seen_indexes: set[int] = set()
    for offset in range(limit):
        index = round(offset * (len(items) - 1) / (limit - 1))
        if index in seen_indexes:
            continue
        seen_indexes.add(index)
        selected.append(items[index])
    return selected


def _item_datetime_key(item: Any) -> str:
    dt = getattr(item, "datetime", None)
    if dt is not None:
        return str(dt.isoformat())
    properties = getattr(item, "properties", {})
    if isinstance(properties, dict):
        value = properties.get("datetime")
        if value is not None:
            return str(value)
    return str(getattr(item, "id", ""))
