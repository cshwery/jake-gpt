from datetime import date
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api import gardens as garden_routes
from app.main import app
from app.models import Garden, GardenContext
from app.services.garden_context import (
    GardenContextService,
    GardenGeometryService,
    MockFrostDateProvider,
    MockHardinessZoneProvider,
    MockPrecipitationProvider,
    UserAssistedSunlightProvider,
)


POLYGON = {
    "type": "Polygon",
    "coordinates": [[[-83.0, 42.0], [-83.0, 42.001], [-82.999, 42.001], [-82.999, 42.0], [-83.0, 42.0]]],
}


def test_geometry_valid_polygon_area_centroid_and_bbox() -> None:
    service = GardenGeometryService()

    validation = service.validate_polygon(POLYGON)
    summary = service.summarize_geometry(POLYGON)

    assert validation.valid
    assert summary.area.area_sq_m > 0
    assert 41.999 < summary.centroid.lat < 42.002
    assert -83.001 < summary.centroid.lon < -82.998
    assert summary.bbox.min_lat <= summary.centroid.lat <= summary.bbox.max_lat
    assert summary.bbox.min_lon <= summary.centroid.lon <= summary.bbox.max_lon
    assert summary.bbox.min_lat == 42.0
    assert summary.bbox.max_lon == -82.999


def test_geometry_invalid_polygon_rejected() -> None:
    service = GardenGeometryService()

    validation = service.validate_polygon({"type": "Polygon", "coordinates": [[[-83.0, 42.0], [-83.0, 42.001], [-82.999, 42.0]]]})

    assert not validation.valid
    assert any("at least four" in error or "closed" in error for error in validation.errors)


def test_mock_hardiness_provider_returns_source_and_confidence() -> None:
    result = MockHardinessZoneProvider().get_zone(42.0, -83.0)

    assert result.zone
    assert result.source == "mock"
    assert result.confidence == "low"


def test_mock_frost_provider_returns_ordered_dates_and_growing_season() -> None:
    result = MockFrostDateProvider().get_frost_dates(42.0, -83.0, "6b")

    assert result.estimated_last_frost_date < result.estimated_first_frost_date
    assert result.growing_season_days == (result.estimated_first_frost_date - result.estimated_last_frost_date).days
    assert result.source == "mock"


def test_mock_precipitation_provider_returns_amounts_and_category() -> None:
    result = MockPrecipitationProvider().get_precipitation_summary(42.0, -83.0)

    assert result.expected_annual_precipitation_mm > 0
    assert result.expected_growing_season_precipitation_mm > 0
    assert result.category in {"low", "medium", "high"}


def test_sunlight_provider_respects_user_override_and_unknown() -> None:
    provider = UserAssistedSunlightProvider()

    full_sun = provider.get_sunlight_estimate(42.0, -83.0, POLYGON, user_override="full_sun")
    unknown = provider.get_sunlight_estimate(42.0, -83.0, POLYGON)

    assert full_sun.category == "full_sun"
    assert full_sun.method == "user_reported"
    assert unknown.category == "unknown"
    assert any("shade from trees" in warning for warning in full_sun.warnings)


def test_garden_context_service_generate_persists_context() -> None:
    db = FakeContextSession()

    context = GardenContextService(db).generate_context(1, user_sunlight_override="part_sun")

    assert db.committed
    assert context.garden_id == 1
    assert context.hardiness_zone
    assert context.estimated_last_frost_date
    assert context.estimated_first_frost_date
    assert context.sunlight_category == "part_sun"
    assert context.assumptions
    assert context.warnings


def test_garden_context_service_recalculate_updates_context() -> None:
    db = FakeContextSession()
    service = GardenContextService(db)
    first = service.generate_context(1, user_sunlight_override="part_sun")

    updated = service.recalculate_context(1, user_sunlight_override="shade")

    assert updated is first
    assert updated.sunlight_category == "shade"
    assert service.get_context(1) is updated


def test_garden_context_api_generate_get_recalculate_and_patch(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_service = FakeApiGardenContextService()
    monkeypatch.setattr(garden_routes, "GardenContextService", lambda db: fake_service)
    monkeypatch.setattr(garden_routes, "_authorize_garden", lambda garden_id, db, user: SimpleNamespace(id=garden_id))
    app.dependency_overrides[deps.get_current_user] = lambda: SimpleNamespace(id=1)
    app.dependency_overrides[garden_routes.get_db] = lambda: object()

    client = TestClient(app)
    headers = {"Authorization": "Bearer test"}

    generated = client.post("/api/gardens/1/context/generate", json={"user_sunlight_override": "full_sun"}, headers=headers)
    existing = client.get("/api/gardens/1/context", headers=headers)
    recalculated = client.post("/api/gardens/1/context/recalculate", json={"user_sunlight_override": "part_shade"}, headers=headers)
    patched = client.patch("/api/gardens/1/context/sunlight", json={"user_sunlight_override": "shade"}, headers=headers)

    app.dependency_overrides.clear()

    assert generated.status_code == 200
    assert existing.status_code == 200
    assert recalculated.status_code == 200
    assert patched.status_code == 200
    assert generated.json()["sunlight"]["category"] == "full_sun"
    assert patched.json()["sunlight"]["category"] == "shade"


class FakeContextSession:
    def __init__(self) -> None:
        self.garden = Garden(id=1, property_id=1, name="Test", polygon_geojson=POLYGON, area_sq_m=1, area_sq_ft=10)
        self.context: GardenContext | None = None
        self.committed = False

    def get(self, model, id: int):
        if model is Garden and id == self.garden.id:
            return self.garden
        return None

    def scalar(self, statement):
        return self.context

    def add(self, instance) -> None:
        if isinstance(instance, GardenContext):
            self.context = instance

    def commit(self) -> None:
        self.committed = True

    def refresh(self, instance) -> None:
        return None


class FakeApiGardenContextService:
    def __init__(self) -> None:
        self.context: GardenContext | None = None

    def generate_context(self, garden_id: int, user_sunlight_override: str | None = None) -> GardenContext:
        self.context = _context(garden_id, user_sunlight_override or "unknown")
        return self.context

    def recalculate_context(self, garden_id: int, user_sunlight_override: str | None = None) -> GardenContext:
        self.context = _context(garden_id, user_sunlight_override or "unknown")
        return self.context

    def get_context(self, garden_id: int) -> GardenContext:
        if self.context is None:
            self.context = _context(garden_id, "unknown")
        return self.context

    def update_sunlight(self, garden_id: int, user_sunlight_override: str) -> GardenContext:
        self.context = _context(garden_id, user_sunlight_override)
        return self.context


def _context(garden_id: int, sunlight: str) -> GardenContext:
    return GardenContext(
        garden_id=garden_id,
        centroid_lat=42.0005,
        centroid_lon=-82.9995,
        bbox_min_lat=42.0,
        bbox_min_lon=-83.0,
        bbox_max_lat=42.001,
        bbox_max_lon=-82.999,
        area_sq_m=100.0,
        area_sq_ft=1076.39,
        hardiness_zone="6b",
        hardiness_zone_source="mock",
        hardiness_zone_confidence="low",
        estimated_last_frost_date=date(2026, 5, 5),
        estimated_first_frost_date=date(2026, 10, 12),
        frost_date_source="mock",
        frost_date_confidence="low",
        growing_season_days=160,
        expected_annual_precipitation_mm=920,
        expected_growing_season_precipitation_mm=536.7,
        precipitation_category="medium",
        precipitation_source="mock",
        precipitation_confidence="low",
        sunlight_category=sunlight,
        sunlight_estimate_method="user_reported" if sunlight != "unknown" else "unknown",
        sunlight_confidence="medium" if sunlight != "unknown" else "low",
        user_sunlight_override=sunlight,
        assumptions=["Mock context."],
        warnings=["Sunlight estimate does not account for shade from trees, buildings, fences, or terrain unless manually specified."],
        raw_context={},
    )
