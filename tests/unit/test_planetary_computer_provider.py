from types import SimpleNamespace

from orbitrisk.providers.planetary_computer_client import (
    PlanetaryComputerProvider,
    _cloud_cover_query,
)


def test_cloud_cover_query_is_optional() -> None:
    assert _cloud_cover_query(None) is None
    assert _cloud_cover_query(20.0) == {"eo:cloud_cover": {"lt": 20.0}}


def test_planetary_provider_enabled_by_config() -> None:
    settings = SimpleNamespace(data_provider="planetary-computer")

    provider = PlanetaryComputerProvider(settings)

    assert provider.enabled()
