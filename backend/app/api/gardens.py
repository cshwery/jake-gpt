import json

from fastapi import APIRouter, Depends, HTTPException
from geoalchemy2 import WKTElement
from sqlalchemy import desc, select, text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Garden, GardenRecommendationRun, Property, User
from app.schemas.garden import ContextUpsert, GardenContextDTO, GardenContextGenerate, GardenCreate, GardenRead, GardenSunlightUpdate, context_to_dto
from app.services.garden_context import GardenContextService, GardenGeometryService, SunlightCategory
from app.services.garden_recommendations import GardenRecommendationRequest, GardenRecommendationResult, GardenRecommendationService, GardenGoalInput

router = APIRouter(prefix="/gardens", tags=["gardens"])


@router.post("", response_model=GardenRead)
def create_garden(payload: GardenCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Garden:
    prop = db.get(Property, payload.property_id)
    if prop is None or prop.user_id != user.id:
        raise HTTPException(status_code=404, detail="Property not found")
    geometry_service = GardenGeometryService()
    try:
        geometry = geometry_service.summarize_geometry(payload.polygon_geojson)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    geojson = json.dumps(payload.polygon_geojson)
    area_sq_m = geometry.area.area_sq_m
    try:
        postgis_area = db.scalar(text("SELECT ST_Area(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326)::geography)"), {"geojson": geojson})
        if postgis_area:
            area_sq_m = float(postgis_area)
    except Exception:
        area_sq_m = geometry.area.area_sq_m
    garden = Garden(
        property_id=prop.id,
        name=payload.name,
        polygon_geojson=payload.polygon_geojson,
        polygon=WKTElement(_polygon_wkt(payload.polygon_geojson), srid=4326),
        area_sq_m=area_sq_m,
        area_sq_ft=area_sq_m * 10.7639,
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


@router.post("/{garden_id}/context", response_model=GardenContextDTO)
def upsert_context(
    garden_id: int,
    payload: ContextUpsert,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GardenContextDTO:
    _authorize_garden(garden_id, db, user)
    context = GardenContextService(db).generate_context(garden_id, user_sunlight_override=_legacy_sunlight(payload.sunlight_estimate))
    return context_to_dto(context)


@router.post("/{garden_id}/context/generate", response_model=GardenContextDTO)
def generate_context(
    garden_id: int,
    payload: GardenContextGenerate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GardenContextDTO:
    _authorize_garden(garden_id, db, user)
    context = GardenContextService(db).generate_context(garden_id, user_sunlight_override=payload.user_sunlight_override)
    return context_to_dto(context)


@router.post("/{garden_id}/context/recalculate", response_model=GardenContextDTO)
def recalculate_context(
    garden_id: int,
    payload: GardenContextGenerate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GardenContextDTO:
    _authorize_garden(garden_id, db, user)
    context = GardenContextService(db).recalculate_context(garden_id, user_sunlight_override=payload.user_sunlight_override)
    return context_to_dto(context)


@router.get("/{garden_id}/context", response_model=GardenContextDTO)
def get_context(garden_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> GardenContextDTO:
    _authorize_garden(garden_id, db, user)
    try:
        context = GardenContextService(db).get_context(garden_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Garden context has not been generated yet.")
    return context_to_dto(context)


@router.patch("/{garden_id}/context/sunlight", response_model=GardenContextDTO)
def update_sunlight_context(
    garden_id: int,
    payload: GardenSunlightUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GardenContextDTO:
    _authorize_garden(garden_id, db, user)
    context = GardenContextService(db).update_sunlight(garden_id, payload.user_sunlight_override)
    return context_to_dto(context)


@router.post("/{garden_id}/recommendations/generate", response_model=GardenRecommendationResult)
def generate_recommendations(
    garden_id: int,
    payload: GardenRecommendationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GardenRecommendationResult:
    _authorize_garden(garden_id, db, user)
    try:
        context = GardenContextService(db).get_context(garden_id)
    except LookupError:
        raise HTTPException(status_code=400, detail="Garden context has not been generated yet. Generate garden context before recommendations.")
    goal_input = GardenGoalInput(
        goals=payload.goals,
        primary_goal=payload.primary_goal,
        maintenance_preference=payload.maintenance_preference,
        experience_level=payload.experience_level,
        desired_plant_slugs=payload.selected_plant_slugs,
        desired_cultivar_slugs=payload.selected_cultivar_slugs,
        excluded_plant_slugs=payload.excluded_plant_slugs,
        notes=payload.notes,
    )
    result = GardenRecommendationService(db=db).recommend_for_garden(
        context_to_dto(context),
        goal_input,
        selected_plant_slugs=payload.selected_plant_slugs,
        selected_cultivar_slugs=payload.selected_cultivar_slugs,
        limit=payload.limit,
        include_excluded=payload.include_excluded,
    )
    run = GardenRecommendationRun(
        garden_id=garden_id,
        input=payload.model_dump(mode="json"),
        result=result.model_dump(mode="json"),
    )
    db.add(run)
    db.commit()
    return result


@router.get("/{garden_id}/recommendations/latest", response_model=GardenRecommendationResult)
def latest_recommendations(garden_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> GardenRecommendationResult:
    _authorize_garden(garden_id, db, user)
    run = db.scalar(
        select(GardenRecommendationRun)
        .where(GardenRecommendationRun.garden_id == garden_id)
        .order_by(desc(GardenRecommendationRun.created_at), desc(GardenRecommendationRun.id))
    )
    if run is None:
        raise HTTPException(status_code=404, detail="No recommendation run exists for this garden.")
    return GardenRecommendationResult.model_validate(run.result)


def _polygon_wkt(geometry: dict) -> str:
    rings = []
    for ring in geometry["coordinates"]:
        points = ", ".join(f"{lng} {lat}" for lng, lat in ring)
        rings.append(f"({points})")
    return f"POLYGON({', '.join(rings)})"


def _authorize_garden(garden_id: int, db: Session, user: User) -> Garden:
    garden = db.get(Garden, garden_id)
    if garden is None or garden.property.user_id != user.id:
        raise HTTPException(status_code=404, detail="Garden not found")
    return garden


def _legacy_sunlight(value: str) -> SunlightCategory:
    return {
        "Full Sun": "full_sun",
        "Part Sun": "part_sun",
        "Part Shade": "part_shade",
        "Shade": "shade",
    }.get(value, "unknown")  # type: ignore[return-value]
