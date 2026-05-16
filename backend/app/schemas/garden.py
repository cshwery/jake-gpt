from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field


Sunlight = Literal["Full Sun", "Part Sun", "Part Shade", "Shade"]


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


class GardenContextRead(BaseModel):
    id: int
    garden_id: int
    hardiness_zone: str
    last_frost_date: date
    precipitation_category: str
    sunlight_estimate: str
    source: str
    notes: str | None = None

    model_config = {"from_attributes": True}
