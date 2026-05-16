import json

from fastapi import APIRouter, Depends, HTTPException
from geoalchemy2 import WKTElement
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Garden, GardenContext, Property, User
from app.schemas.garden import ContextUpsert, GardenContextRead, GardenCreate, GardenRead
from app.services.climate import MockGardenContextProvider

router = APIRouter(prefix="/gardens", tags=["gardens"])


@router.post("", response_model=GardenRead)
def create_garden(payload: GardenCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Garden:
    prop = db.get(Property, payload.property_id)
    if prop is None or prop.user_id != user.id:
        raise HTTPException(status_code=404, detail="Property not found")
    geojson = json.dumps(payload.polygon_geojson)
    area_sq_m = db.scalar(text("SELECT ST_Area(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)::geography)"), {"geojson": geojson})
    garden = Garden(
        property_id=prop.id,
        name=payload.name,
        polygon_geojson=payload.polygon_geojson,
        polygon=WKTElement(_polygon_wkt(payload.polygon_geojson), srid=4326),
        area_sq_m=float(area_sq_m or 0),
        area_sq_ft=float(area_sq_m or 0) * 10.7639,
    )
    db.add(garden)
    db.commit()
    db.refresh(garden)
    return garden


@router.get("/{garden_id}", response_model=GardenRead)
def get_garden(garden_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Garden:
    garden = db.get(Garden, garden_id)
    if garden is None or garden.property.user_id != user.id:
        raise HTTPException(status_code=404, detail="Garden not found")
    return garden


@router.post("/{garden_id}/context", response_model=GardenContextRead)
def upsert_context(
    garden_id: int,
    payload: ContextUpsert,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GardenContext:
    garden = db.get(Garden, garden_id)
    if garden is None or garden.property.user_id != user.id:
        raise HTTPException(status_code=404, detail="Garden not found")
    climate = MockGardenContextProvider().context_for(garden.property.latitude, garden.property.longitude)
    context = db.scalar(select(GardenContext).where(GardenContext.garden_id == garden.id))
    if context is None:
        context = GardenContext(garden_id=garden.id)
        db.add(context)
    context.hardiness_zone = climate.hardiness_zone
    context.last_frost_date = climate.last_frost_date
    context.precipitation_category = climate.precipitation_category
    context.sunlight_estimate = payload.sunlight_estimate
    context.source = "mock"
    context.notes = climate.notes
    db.commit()
    db.refresh(context)
    return context


def _polygon_wkt(geometry: dict) -> str:
    rings = []
    for ring in geometry["coordinates"]:
        points = ", ".join(f"{lng} {lat}" for lng, lat in ring)
        rings.append(f"({points})")
    return f"POLYGON({', '.join(rings)})"
