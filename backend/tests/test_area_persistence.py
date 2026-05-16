from app.api.gardens import _polygon_wkt


def test_polygon_geojson_converts_to_postgis_wkt_for_persistence() -> None:
    geometry = {
        "type": "Polygon",
        "coordinates": [[[-83.0, 42.0], [-83.0, 42.001], [-82.999, 42.001], [-82.999, 42.0], [-83.0, 42.0]]],
    }

    assert _polygon_wkt(geometry).startswith("POLYGON((")
    assert "-83.0 42.0" in _polygon_wkt(geometry)
