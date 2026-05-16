from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field


Sunlight = Literal["Full Sun", "Part Sun", "Part Shade", "Shade"]
SunlightCategory = Literal["full_sun", "part_sun", "part_shade", "shade", "unknown"]


class GardenCreate(BaseModel):
    property_id: int
    name: str = "Garden"
    polygon_geojson: dict[str, Any] = Field(..., description="GeoJSON Polygon geometry")


class GardenRead(BaseModel):
    id: int
    property_id: int
    name: str
    polygon_geojson: dict[str, Any]
    area_sq_m: float
    area_sq_ft: float

    model_config = {"from_attributes": True}


class ContextUpsert(BaseModel):
    sunlight_estimate: Sunlight


class GardenContextGenerate(BaseModel):
    user_sunlight_override: SunlightCategory | None = None


class GardenSunlightUpdate(BaseModel):
    user_sunlight_override: SunlightCategory


class LatLonDTO(BaseModel):
    lat: float
    lon: float


class BoundingBoxDTO(BaseModel):
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float


class GeometryContextDTO(BaseModel):
    centroid: LatLonDTO
    bbox: BoundingBoxDTO
    area_sq_m: float
    area_sq_ft: float


class HardinessContextDTO(BaseModel):
    zone: str | None
    source: str | None
    confidence: str | None


class FrostContextDTO(BaseModel):
    estimated_last_frost_date: date | None
    estimated_first_frost_date: date | None
    growing_season_days: int | None
    source: str | None
    confidence: str | None


class PrecipitationContextDTO(BaseModel):
    expected_annual_precipitation_mm: float | None
    expected_growing_season_precipitation_mm: float | None
    category: str | None
    source: str | None
    confidence: str | None


class SunlightContextDTO(BaseModel):
    category: str | None
    method: str | None
    confidence: str | None
    user_override: str | None


class GardenContextDTO(BaseModel):
    garden_id: int
    geometry: GeometryContextDTO
    hardiness: HardinessContextDTO
    frost: FrostContextDTO
    precipitation: PrecipitationContextDTO
    sunlight: SunlightContextDTO
    assumptions: list[str]
    warnings: list[str]
    raw_context: dict[str, Any]


class GardenContextRead(BaseModel):
    id: int
    garden_id: int
    centroid_lat: float
    centroid_lon: float
    bbox_min_lat: float
    bbox_min_lon: float
    bbox_max_lat: float
    bbox_max_lon: float
    area_sq_m: float
    area_sq_ft: float
    hardiness_zone: str | None
    hardiness_zone_source: str | None
    hardiness_zone_confidence: str | None
    estimated_last_frost_date: date | None
    estimated_first_frost_date: date | None
    frost_date_source: str | None
    frost_date_confidence: str | None
    growing_season_days: int | None
    expected_annual_precipitation_mm: float | None
    expected_growing_season_precipitation_mm: float | None
    precipitation_category: str | None
    precipitation_source: str | None
    precipitation_confidence: str | None
    sunlight_category: str | None
    sunlight_estimate_method: str | None
    sunlight_confidence: str | None
    user_sunlight_override: str | None
    assumptions: list[str]
    warnings: list[str]
    raw_context: dict[str, Any]

    model_config = {"from_attributes": True}


def context_to_dto(context: Any) -> GardenContextDTO:
    if isinstance(context, GardenContextDTO):
        return context
    return GardenContextDTO(
        garden_id=context.garden_id,
        geometry=GeometryContextDTO(
            centroid=LatLonDTO(lat=context.centroid_lat, lon=context.centroid_lon),
            bbox=BoundingBoxDTO(
                min_lat=context.bbox_min_lat,
                min_lon=context.bbox_min_lon,
                max_lat=context.bbox_max_lat,
                max_lon=context.bbox_max_lon,
            ),
            area_sq_m=context.area_sq_m,
            area_sq_ft=context.area_sq_ft,
        ),
        hardiness=HardinessContextDTO(
            zone=context.hardiness_zone,
            source=context.hardiness_zone_source,
            confidence=context.hardiness_zone_confidence,
        ),
        frost=FrostContextDTO(
            estimated_last_frost_date=context.estimated_last_frost_date,
            estimated_first_frost_date=context.estimated_first_frost_date,
            growing_season_days=context.growing_season_days,
            source=context.frost_date_source,
            confidence=context.frost_date_confidence,
        ),
        precipitation=PrecipitationContextDTO(
            expected_annual_precipitation_mm=context.expected_annual_precipitation_mm,
            expected_growing_season_precipitation_mm=context.expected_growing_season_precipitation_mm,
            category=context.precipitation_category,
            source=context.precipitation_source,
            confidence=context.precipitation_confidence,
        ),
        sunlight=SunlightContextDTO(
            category=context.sunlight_category,
            method=context.sunlight_estimate_method,
            confidence=context.sunlight_confidence,
            user_override=context.user_sunlight_override,
        ),
        assumptions=context.assumptions or [],
        warnings=context.warnings or [],
        raw_context=context.raw_context or {},
    )
