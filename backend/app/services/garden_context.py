from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Garden, GardenContext

SunlightCategory = Literal["full_sun", "part_sun", "part_shade", "shade", "unknown"]
PrecipitationCategory = Literal["low", "medium", "high"]
Confidence = Literal["low", "medium", "high"]

SQ_M_TO_SQ_FT = 10.7639
EARTH_RADIUS_M = 6_371_008.8


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class LatLon:
    lat: float
    lon: float


@dataclass(frozen=True)
class BoundingBox:
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float


@dataclass(frozen=True)
class AreaResult:
    area_sq_m: float
    area_sq_ft: float
    source: str


@dataclass(frozen=True)
class GardenGeometrySummary:
    centroid: LatLon
    bbox: BoundingBox
    area: AreaResult
    normalized_geojson: dict[str, Any]
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw_source: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HardinessZoneResult:
    zone: str | None
    source: str
    confidence: Confidence
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw_source: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FrostDateResult:
    estimated_last_frost_date: date | None
    estimated_first_frost_date: date | None
    growing_season_days: int | None
    source: str
    confidence: Confidence
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw_source: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PrecipitationResult:
    expected_annual_precipitation_mm: float | None
    expected_growing_season_precipitation_mm: float | None
    category: PrecipitationCategory | None
    source: str
    confidence: Confidence
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw_source: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SunlightResult:
    category: SunlightCategory
    method: Literal["user_reported", "solar_baseline", "mock", "unknown"]
    confidence: Confidence
    user_override: SunlightCategory | None = None
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw_source: dict[str, Any] = field(default_factory=dict)


class GardenGeometryService:
    def validate_polygon(self, geojson: dict[str, Any]) -> ValidationResult:
        errors: list[str] = []
        if geojson.get("type") != "Polygon":
            errors.append("Geometry must be a GeoJSON Polygon.")
        coordinates = geojson.get("coordinates")
        if not isinstance(coordinates, list) or not coordinates:
            errors.append("Polygon coordinates are required.")
            return ValidationResult(False, errors)
        outer = coordinates[0]
        if not isinstance(outer, list) or len(outer) < 4:
            errors.append("Polygon outer ring must contain at least four positions.")
            return ValidationResult(False, errors)
        for index, position in enumerate(outer):
            if not isinstance(position, list | tuple) or len(position) < 2:
                errors.append(f"Position {index} must contain longitude and latitude.")
                continue
            lon, lat = position[0], position[1]
            if not isinstance(lon, int | float) or not isinstance(lat, int | float):
                errors.append(f"Position {index} longitude and latitude must be numeric.")
            elif not (-180 <= lon <= 180 and -90 <= lat <= 90):
                errors.append(f"Position {index} is outside valid longitude/latitude bounds.")
        if outer and outer[0][:2] != outer[-1][:2]:
            errors.append("Polygon outer ring must be closed.")
        if abs(_signed_area_lon_lat(outer)) == 0:
            errors.append("Polygon area must be greater than zero.")
        return ValidationResult(not errors, errors)

    def calculate_area(self, geojson: dict[str, Any]) -> AreaResult:
        ring = _outer_ring(geojson)
        area_sq_m = abs(_projected_ring_area_sq_m(ring))
        return AreaResult(area_sq_m=area_sq_m, area_sq_ft=area_sq_m * SQ_M_TO_SQ_FT, source="python_approximation")

    def calculate_centroid(self, geojson: dict[str, Any]) -> LatLon:
        ring = _outer_ring(geojson)
        lon, lat = _polygon_centroid_lon_lat(ring)
        return LatLon(lat=lat, lon=lon)

    def calculate_bbox(self, geojson: dict[str, Any]) -> BoundingBox:
        ring = _outer_ring(geojson)
        lons = [point[0] for point in ring]
        lats = [point[1] for point in ring]
        return BoundingBox(min_lat=min(lats), min_lon=min(lons), max_lat=max(lats), max_lon=max(lons))

    def summarize_geometry(self, geojson: dict[str, Any]) -> GardenGeometrySummary:
        validation = self.validate_polygon(geojson)
        if not validation.valid:
            raise ValueError("; ".join(validation.errors))
        area = self.calculate_area(geojson)
        return GardenGeometrySummary(
            centroid=self.calculate_centroid(geojson),
            bbox=self.calculate_bbox(geojson),
            area=area,
            normalized_geojson=geojson,
            assumptions=["Garden area is calculated server-side with a local geodesic approximation when PostGIS is unavailable."],
            warnings=[],
            raw_source={"geometry_area_source": area.source},
        )


class HardinessZoneProvider:
    def get_zone(self, lat: float, lon: float) -> HardinessZoneResult:
        raise NotImplementedError


class MockHardinessZoneProvider(HardinessZoneProvider):
    def get_zone(self, lat: float, lon: float) -> HardinessZoneResult:
        if lat >= 47:
            zone = "4b"
        elif lat >= 44:
            zone = "5b"
        elif lat >= 40:
            zone = "6b"
        elif lat >= 35:
            zone = "7b"
        elif lat >= 30:
            zone = "8b"
        else:
            zone = "9a"
        return HardinessZoneResult(
            zone=zone,
            source="mock",
            confidence="low",
            assumptions=["Hardiness zone is currently estimated by a mock latitude-band provider."],
            warnings=["Hardiness zone should be replaced with USDA Plant Hardiness Zone GIS lookup before production use."],
            raw_source={"provider": "MockHardinessZoneProvider", "lat": lat, "lon": lon},
        )


class LocalPostGISHardinessZoneProvider(HardinessZoneProvider):
    def get_zone(self, lat: float, lon: float) -> HardinessZoneResult:
        raise NotImplementedError("Import USDA hardiness zone polygons into PostGIS before enabling this provider.")


class FrostDateProvider:
    def get_frost_dates(self, lat: float, lon: float, hardiness_zone: str | None = None) -> FrostDateResult:
        raise NotImplementedError


class MockFrostDateProvider(FrostDateProvider):
    def get_frost_dates(self, lat: float, lon: float, hardiness_zone: str | None = None) -> FrostDateResult:
        year = date.today().year
        zone_num = _zone_number(hardiness_zone)
        frost_by_zone = {
            4: (date(year, 5, 28), date(year, 9, 20)),
            5: (date(year, 5, 18), date(year, 9, 30)),
            6: (date(year, 5, 5), date(year, 10, 12)),
            7: (date(year, 4, 15), date(year, 10, 28)),
            8: (date(year, 3, 25), date(year, 11, 15)),
            9: (date(year, 2, 20), date(year, 12, 10)),
        }
        last_frost, first_frost = frost_by_zone.get(zone_num, frost_by_zone[6])
        return FrostDateResult(
            estimated_last_frost_date=last_frost,
            estimated_first_frost_date=first_frost,
            growing_season_days=(first_frost - last_frost).days,
            source="mock",
            confidence="low",
            assumptions=["Frost dates are estimated from mocked hardiness-zone bands."],
            warnings=["Frost dates are estimates and local microclimates may vary."],
            raw_source={"provider": "MockFrostDateProvider", "hardiness_zone": hardiness_zone, "lat": lat, "lon": lon},
        )


class HistoricalWeatherFrostDateProvider(FrostDateProvider):
    def get_frost_dates(self, lat: float, lon: float, hardiness_zone: str | None = None) -> FrostDateResult:
        raise NotImplementedError("Historical weather integration is not implemented in v0.")


class PrecipitationProvider:
    def get_precipitation_summary(self, lat: float, lon: float, start_month: int = 4, end_month: int = 10) -> PrecipitationResult:
        raise NotImplementedError


class MockPrecipitationProvider(PrecipitationProvider):
    def get_precipitation_summary(self, lat: float, lon: float, start_month: int = 4, end_month: int = 10) -> PrecipitationResult:
        if lat >= 44:
            annual = 820.0
        elif lat >= 36:
            annual = 920.0
        elif lat >= 30:
            annual = 700.0
        else:
            annual = 550.0
        growing = annual * ((end_month - start_month + 1) / 12)
        category: PrecipitationCategory = "low" if annual < 650 else "high" if annual > 950 else "medium"
        return PrecipitationResult(
            expected_annual_precipitation_mm=round(annual, 1),
            expected_growing_season_precipitation_mm=round(growing, 1),
            category=category,
            source="mock",
            confidence="low",
            assumptions=["Precipitation is estimated by a mock regional provider."],
            warnings=["Watering needs should be adjusted based on actual rainfall and soil moisture."],
            raw_source={"provider": "MockPrecipitationProvider", "lat": lat, "lon": lon, "start_month": start_month, "end_month": end_month},
        )


class HistoricalWeatherPrecipitationProvider(PrecipitationProvider):
    def get_precipitation_summary(self, lat: float, lon: float, start_month: int = 4, end_month: int = 10) -> PrecipitationResult:
        raise NotImplementedError("Historical precipitation integration is not implemented in v0.")


class SunlightProvider:
    def get_sunlight_estimate(self, lat: float, lon: float, polygon: dict[str, Any], user_override: SunlightCategory | None = None) -> SunlightResult:
        raise NotImplementedError


class UserAssistedSunlightProvider(SunlightProvider):
    def get_sunlight_estimate(self, lat: float, lon: float, polygon: dict[str, Any], user_override: SunlightCategory | None = None) -> SunlightResult:
        if user_override and user_override != "unknown":
            return SunlightResult(
                category=user_override,
                method="user_reported",
                confidence="medium",
                user_override=user_override,
                assumptions=["Sunlight category is based on the user's observation of the garden during the growing season."],
                warnings=["Sunlight estimate does not account for shade from trees, buildings, fences, or terrain unless manually specified."],
                raw_source={"provider": "UserAssistedSunlightProvider"},
            )
        return SunlightResult(
            category="unknown",
            method="unknown",
            confidence="low",
            user_override=user_override,
            assumptions=["No sunlight override was provided; sunlight remains unknown for v0."],
            warnings=["Sunlight estimate does not account for shade from trees, buildings, fences, or terrain unless manually specified."],
            raw_source={"provider": "UserAssistedSunlightProvider"},
        )


class SolarBaselineSunlightProvider(SunlightProvider):
    def get_sunlight_estimate(self, lat: float, lon: float, polygon: dict[str, Any], user_override: SunlightCategory | None = None) -> SunlightResult:
        raise NotImplementedError("Solar baseline estimation is not implemented in v0.")


class GardenContextService:
    def __init__(
        self,
        db: Session,
        geometry_service: GardenGeometryService | None = None,
        hardiness_provider: HardinessZoneProvider | None = None,
        frost_provider: FrostDateProvider | None = None,
        precipitation_provider: PrecipitationProvider | None = None,
        sunlight_provider: SunlightProvider | None = None,
    ) -> None:
        self.db = db
        self.geometry_service = geometry_service or GardenGeometryService()
        self.hardiness_provider = hardiness_provider or MockHardinessZoneProvider()
        self.frost_provider = frost_provider or MockFrostDateProvider()
        self.precipitation_provider = precipitation_provider or MockPrecipitationProvider()
        self.sunlight_provider = sunlight_provider or UserAssistedSunlightProvider()

    def generate_context(self, garden_id: int, user_sunlight_override: SunlightCategory | None = None) -> GardenContext:
        return self._calculate_and_persist(garden_id, user_sunlight_override=user_sunlight_override)

    def recalculate_context(self, garden_id: int, user_sunlight_override: SunlightCategory | None = None) -> GardenContext:
        existing = self.get_context(garden_id)
        override = user_sunlight_override if user_sunlight_override is not None else existing.user_sunlight_override
        return self._calculate_and_persist(garden_id, user_sunlight_override=override)

    def get_context(self, garden_id: int) -> GardenContext:
        context = self.db.scalar(select(GardenContext).where(GardenContext.garden_id == garden_id))
        if context is None:
            raise LookupError("Garden context has not been generated yet.")
        return context

    def update_sunlight(self, garden_id: int, user_sunlight_override: SunlightCategory) -> GardenContext:
        context = self.db.scalar(select(GardenContext).where(GardenContext.garden_id == garden_id))
        if context is None:
            return self.generate_context(garden_id, user_sunlight_override=user_sunlight_override)
        garden = self._get_garden(garden_id)
        sunlight = self.sunlight_provider.get_sunlight_estimate(
            context.centroid_lat,
            context.centroid_lon,
            garden.polygon_geojson,
            user_override=user_sunlight_override,
        )
        context.sunlight_category = sunlight.category
        context.sunlight_estimate_method = sunlight.method
        context.sunlight_confidence = sunlight.confidence
        context.user_sunlight_override = sunlight.user_override
        context.assumptions = _merge_unique([*(context.assumptions or []), *sunlight.assumptions])
        context.warnings = _merge_unique([*(context.warnings or []), *sunlight.warnings])
        raw = dict(context.raw_context or {})
        raw["sunlight"] = sunlight.raw_source
        context.raw_context = raw
        context.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(context)
        return context

    def _calculate_and_persist(self, garden_id: int, user_sunlight_override: SunlightCategory | None) -> GardenContext:
        garden = self._get_garden(garden_id)
        geometry = self.geometry_service.summarize_geometry(garden.polygon_geojson)
        hardiness = self._safe("hardiness", lambda: self.hardiness_provider.get_zone(geometry.centroid.lat, geometry.centroid.lon))
        frost = self._safe("frost", lambda: self.frost_provider.get_frost_dates(geometry.centroid.lat, geometry.centroid.lon, hardiness.zone if hardiness else None))
        precipitation = self._safe("precipitation", lambda: self.precipitation_provider.get_precipitation_summary(geometry.centroid.lat, geometry.centroid.lon))
        sunlight = self._safe("sunlight", lambda: self.sunlight_provider.get_sunlight_estimate(geometry.centroid.lat, geometry.centroid.lon, garden.polygon_geojson, user_override=user_sunlight_override))

        assumptions = [*geometry.assumptions]
        warnings = [*geometry.warnings]
        raw_context: dict[str, Any] = {"geometry": geometry.raw_source}
        for key, result in [("hardiness", hardiness), ("frost", frost), ("precipitation", precipitation), ("sunlight", sunlight)]:
            if result is None:
                warnings.append(f"{key.title()} provider failed; context is partial.")
                raw_context[key] = {"error": "provider_failed"}
            else:
                assumptions.extend(result.assumptions)
                warnings.extend(result.warnings)
                raw_context[key] = result.raw_source

        context = self.db.scalar(select(GardenContext).where(GardenContext.garden_id == garden.id))
        if context is None:
            context = GardenContext(garden_id=garden.id)
            self.db.add(context)

        context.centroid_lat = geometry.centroid.lat
        context.centroid_lon = geometry.centroid.lon
        context.bbox_min_lat = geometry.bbox.min_lat
        context.bbox_min_lon = geometry.bbox.min_lon
        context.bbox_max_lat = geometry.bbox.max_lat
        context.bbox_max_lon = geometry.bbox.max_lon
        context.area_sq_m = geometry.area.area_sq_m
        context.area_sq_ft = geometry.area.area_sq_ft
        context.hardiness_zone = hardiness.zone if hardiness else None
        context.hardiness_zone_source = hardiness.source if hardiness else None
        context.hardiness_zone_confidence = hardiness.confidence if hardiness else None
        context.estimated_last_frost_date = frost.estimated_last_frost_date if frost else None
        context.estimated_first_frost_date = frost.estimated_first_frost_date if frost else None
        context.frost_date_source = frost.source if frost else None
        context.frost_date_confidence = frost.confidence if frost else None
        context.growing_season_days = frost.growing_season_days if frost else None
        context.expected_annual_precipitation_mm = precipitation.expected_annual_precipitation_mm if precipitation else None
        context.expected_growing_season_precipitation_mm = precipitation.expected_growing_season_precipitation_mm if precipitation else None
        context.precipitation_category = precipitation.category if precipitation else None
        context.precipitation_source = precipitation.source if precipitation else None
        context.precipitation_confidence = precipitation.confidence if precipitation else None
        context.sunlight_category = sunlight.category if sunlight else "unknown"
        context.sunlight_estimate_method = sunlight.method if sunlight else "unknown"
        context.sunlight_confidence = sunlight.confidence if sunlight else "low"
        context.user_sunlight_override = sunlight.user_override if sunlight else user_sunlight_override
        context.assumptions = _merge_unique(assumptions)
        context.warnings = _merge_unique(warnings)
        context.raw_context = raw_context
        context.updated_at = datetime.utcnow()

        garden.area_sq_m = geometry.area.area_sq_m
        garden.area_sq_ft = geometry.area.area_sq_ft
        garden.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(context)
        return context

    def _get_garden(self, garden_id: int) -> Garden:
        garden = self.db.get(Garden, garden_id)
        if garden is None:
            raise LookupError("Garden not found.")
        return garden

    def _safe(self, name: str, callback: Any) -> Any:
        try:
            return callback()
        except Exception:
            return None


def _outer_ring(geojson: dict[str, Any]) -> list[list[float]]:
    return geojson["coordinates"][0]


def _signed_area_lon_lat(ring: list[list[float]]) -> float:
    area = 0.0
    for index in range(len(ring) - 1):
        lon1, lat1 = ring[index][:2]
        lon2, lat2 = ring[index + 1][:2]
        area += lon1 * lat2 - lon2 * lat1
    return area / 2


def _projected_ring_area_sq_m(ring: list[list[float]]) -> float:
    avg_lat_rad = math.radians(sum(point[1] for point in ring[:-1]) / max(len(ring) - 1, 1))
    projected = [(_lon_to_m(point[0], avg_lat_rad), _lat_to_m(point[1])) for point in ring]
    area = 0.0
    for index in range(len(projected) - 1):
        x1, y1 = projected[index]
        x2, y2 = projected[index + 1]
        area += x1 * y2 - x2 * y1
    return area / 2


def _polygon_centroid_lon_lat(ring: list[list[float]]) -> tuple[float, float]:
    signed_area = _signed_area_lon_lat(ring)
    if signed_area == 0:
        points = ring[:-1]
        return sum(point[0] for point in points) / len(points), sum(point[1] for point in points) / len(points)
    cx = 0.0
    cy = 0.0
    for index in range(len(ring) - 1):
        lon1, lat1 = ring[index][:2]
        lon2, lat2 = ring[index + 1][:2]
        cross = lon1 * lat2 - lon2 * lat1
        cx += (lon1 + lon2) * cross
        cy += (lat1 + lat2) * cross
    return cx / (6 * signed_area), cy / (6 * signed_area)


def _lon_to_m(lon: float, avg_lat_rad: float) -> float:
    return math.radians(lon) * EARTH_RADIUS_M * math.cos(avg_lat_rad)


def _lat_to_m(lat: float) -> float:
    return math.radians(lat) * EARTH_RADIUS_M


def _zone_number(zone: str | None) -> int:
    if not zone:
        return 6
    digits = "".join(char for char in zone if char.isdigit())
    return int(digits or "6")


def _merge_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            merged.append(value)
    return merged
