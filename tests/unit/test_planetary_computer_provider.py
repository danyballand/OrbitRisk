from datetime import UTC, date, datetime
from types import SimpleNamespace

from orbitrisk.providers.base import ObservationQuery
from orbitrisk.providers.planetary_computer_client import (
    PlanetaryComputerProvider,
    _allocate_item_budgets,
    _cloud_cover_query,
    _sample_evenly,
    _seasonal_year_slices,
)


class _FakeItem:
    def __init__(self, observed_at: datetime) -> None:
        self.datetime = observed_at


class _FakeSearch:
    def __init__(self, items: list[_FakeItem]) -> None:
        self._items = items

    def items(self) -> list[_FakeItem]:
        return self._items


class _FakeCatalog:
    def __init__(self, items_by_year: dict[int, list[_FakeItem]]) -> None:
        self.items_by_year = items_by_year
        self.datetimes: list[str] = []

    def search(
        self,
        *,
        collections: list[str],
        bbox: tuple[float, float, float, float],
        datetime: str,
        query: dict[str, object] | None,
    ) -> _FakeSearch:
        assert collections == ["sentinel-2-l2a"]
        assert bbox == (-0.1, 44.7, -0.05, 44.75)
        assert query == {"eo:cloud_cover": {"lt": 70.0}}
        self.datetimes.append(datetime)
        year = int(datetime[:4])
        return _FakeSearch(list(reversed(self.items_by_year[year])))


def test_cloud_cover_query_is_optional() -> None:
    assert _cloud_cover_query(None) is None
    assert _cloud_cover_query(20.0) == {"eo:cloud_cover": {"lt": 20.0}}


def test_planetary_provider_enabled_by_config() -> None:
    settings = SimpleNamespace(data_provider="planetary-computer")

    provider = PlanetaryComputerProvider(settings)

    assert provider.enabled()


def test_seasonal_year_slices_preserve_requested_month_day_window() -> None:
    assert _seasonal_year_slices(date(2019, 6, 1), date(2022, 8, 31)) == [
        (date(2019, 6, 1), date(2019, 8, 31)),
        (date(2020, 6, 1), date(2020, 8, 31)),
        (date(2021, 6, 1), date(2021, 8, 31)),
        (date(2022, 6, 1), date(2022, 8, 31)),
    ]


def test_allocate_item_budgets_spreads_budget_and_prefers_target_year() -> None:
    assert _allocate_item_budgets(80, 4) == [20, 20, 20, 20]
    assert _allocate_item_budgets(10, 4) == [2, 2, 3, 3]


def test_sample_evenly_preserves_first_middle_and_last_items() -> None:
    assert _sample_evenly(list(range(10)), 4) == [0, 3, 6, 9]


def test_year_stratified_search_spreads_budget_across_seasons() -> None:
    items_by_year = {
        year: [
            _FakeItem(datetime(year, month, day, tzinfo=UTC))
            for month, day in [(6, 1), (6, 15), (7, 1), (7, 15), (8, 1), (8, 15)]
        ]
        for year in [2019, 2020, 2021, 2022]
    }
    catalog = _FakeCatalog(items_by_year)
    settings = SimpleNamespace(
        data_provider="planetary-computer",
        planetary_computer_collection="sentinel-2-l2a",
    )
    provider = PlanetaryComputerProvider(settings)
    query = ObservationQuery(
        bbox_wgs84=(-0.1, 44.7, -0.05, 44.75),
        date_start=date(2019, 6, 1),
        date_end=date(2022, 8, 31),
        output_crs="EPSG:32630",
        resolution_m=10,
        bands=("B08", "B11", "SCL"),
        max_cloud_cover_pct=70.0,
        max_items=10,
    )

    items = provider._search_items_by_year(catalog, query)

    assert catalog.datetimes == [
        "2019-06-01/2019-08-31",
        "2020-06-01/2020-08-31",
        "2021-06-01/2021-08-31",
        "2022-06-01/2022-08-31",
    ]
    assert [item.datetime.year for item in items].count(2019) == 2
    assert [item.datetime.year for item in items].count(2020) == 2
    assert [item.datetime.year for item in items].count(2021) == 3
    assert [item.datetime.year for item in items].count(2022) == 3
    assert items == sorted(items, key=lambda item: item.datetime)
