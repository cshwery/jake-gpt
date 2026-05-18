from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api import properties as property_routes
from app.main import app
from app.services.geocoding import GeocodeResult, MapboxGeocoder, MockGeocoder, get_geocoder


def test_mapbox_geocoder_maps_api_response(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def read(self) -> bytes:
            return b"""
            {
                "features": [
                    {
                        "place_name": "123 Main St, Detroit, Michigan 48201, United States",
                        "center": [-83.0458, 42.3314],
                        "bbox": [-83.046, 42.331, -83.045, 42.332],
                        "relevance": 0.98,
                        "properties": {"accuracy": "rooftop"}
                    }
                ]
            }
            """

    monkeypatch.setattr("app.services.geocoding.urlopen", lambda *args, **kwargs: FakeResponse())

    result = MapboxGeocoder("token").geocode("123 Main St Detroit MI")

    assert result.provider == "mapbox"
    assert result.normalized_address.startswith("123 Main")
    assert result.latitude == 42.3314
    assert result.longitude == -83.0458
    assert result.accuracy == "rooftop"
    assert result.confidence == "0.98"
    assert result.bbox == [-83.046, 42.331, -83.045, 42.332]


def test_mock_geocoder_still_works() -> None:
    result = MockGeocoder().geocode("123 Garden Lane, Detroit, MI")

    assert result.provider == "mock"
    assert result.normalized_address.endswith("(mock geocode)")
    assert result.latitude == 42.3314


def test_missing_mapbox_token_falls_back_to_mock() -> None:
    assert isinstance(get_geocoder(provider="mapbox", mapbox_access_token=None), MockGeocoder)


def test_geocode_endpoint_returns_normalized_address(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        property_routes,
        "_geocode_address",
        lambda address: GeocodeResult(provider="mock", query=address, normalized_address="Normalized Address", latitude=42.0, longitude=-83.0),
    )
    app.dependency_overrides[deps.get_current_user] = lambda: SimpleNamespace(id=1)

    response = TestClient(app).post("/api/properties/geocode", json={"address": "raw"}, headers={"Authorization": "Bearer test"})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["normalized_address"] == "Normalized Address"
    assert response.json()["latitude"] == 42.0
