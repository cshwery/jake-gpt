from app.api.gardens import _polygon_wkt
from app.services.garden_area import area_category, area_warning
from app.services.garden_context import GardenGeometryService


def test_polygon_geojson_converts_to_postgis_wkt_for_persistence() -> None:
    geometry = {
        "type": "Polygon",
        "coordinates": [[[-83.0, 42.0], [-83.0, 42.001], [-82.999, 42.001], [-82.999, 42.0], [-83.0, 42.0]]],
    }

    assert _polygon_wkt(geometry).startswith("POLYGON((")
    assert "-83.0 42.0" in _polygon_wkt(geometry)


def test_area_category_and_warnings() -> None:
    assert area_category(24) == "Tiny"
    assert area_category(250) == "Medium"
    assert area_category(12_000) == "Probably Accidental"
    assert "very large" in area_warning(2_001).lower()
    assert "wrong zoom" in area_warning(10_001).lower()


def test_invalid_polygon_rejected_with_clear_error() -> None:
    validation = GardenGeometryService().validate_polygon({"type": "Polygon", "coordinates": [[[-83.0, 42.0], [-83.0, 42.001], [-82.999, 42.0]]]})

    assert not validation.valid
    assert validation.errors
