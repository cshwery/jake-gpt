import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Garden, GardenContext, Plant, PlantCultivar, User
from app.schemas.garden import context_to_dto
from app.schemas.plant import PlantSearchResult, PlantSuggestion, SuggestRequest
from app.services.garden_recommendations import GardenGoalInput, GardenRecommendationResult, GardenRecommendationService

router = APIRouter(prefix="/plants", tags=["plants"])


@router.get("", response_model=list[PlantSearchResult])
def search_plants(
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PlantSearchResult]:
    stmt = select(Plant).order_by(Plant.common_name)
    if q:
        stmt = stmt.where(Plant.common_name.ilike(f"%{q}%") | Plant.slug.ilike(f"%{q}%"))
    plants = _dedupe_species(list(db.scalars(stmt).all()))
    results = [
        PlantSearchResult.model_validate(plant).model_copy(
            update={"result_type": "species", "plant_id": plant.id, "display_name": _title_case(plant.common_name)}
        )
        for plant in plants
    ]
    if q:
        cultivar_stmt = (
            select(PlantCultivar, Plant)
            .join(Plant, Plant.id == PlantCultivar.plant_id)
            .where(
                PlantCultivar.cultivar_name.ilike(f"%{q}%")
                | PlantCultivar.normalized_name.ilike(f"%{q}%")
                | PlantCultivar.slug.ilike(f"%{q}%")
                | Plant.common_name.ilike(f"%{q}%")
            )
            .order_by(Plant.common_name, PlantCultivar.cultivar_name)
        )
        for cultivar, plant in db.execute(cultivar_stmt):
            results.append(
                PlantSearchResult.model_validate(plant).model_copy(
                    update={
                        "result_type": "cultivar",
                        "plant_id": plant.id,
                        "cultivar_id": cultivar.id,
                        "cultivar_slug": cultivar.slug,
                        "cultivar_name": cultivar.cultivar_name,
                        "display_name": f"{_title_case(plant.common_name)} — {cultivar.cultivar_name}",
                        "cultivar_notes": cultivar.notes,
                    }
                )
            )
    return results


def _dedupe_species(plants: list[Plant]) -> list[Plant]:
    by_identity: dict[str, Plant] = {}
    for plant in plants:
        identity = _species_identity(plant)
        existing = by_identity.get(identity)
        if existing is None or (not existing.slug and plant.slug):
            by_identity[identity] = plant
    return sorted(by_identity.values(), key=lambda plant: _title_case(plant.common_name))


def _species_identity(plant: Plant) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (plant.slug or plant.common_name).strip().lower()).strip("_")


@router.post("/suggest", response_model=list[PlantSuggestion])
def suggest(payload: SuggestRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[PlantSuggestion]:
    garden = db.get(Garden, payload.garden_id)
    if garden is None or garden.property.user_id != user.id:
        raise HTTPException(status_code=404, detail="Garden not found")
    context = db.scalar(select(GardenContext).where(GardenContext.garden_id == garden.id))
    if context is None:
        raise HTTPException(status_code=400, detail="Garden context is required before suggestions")
    selected_plants = list(db.scalars(select(Plant).where(Plant.id.in_(payload.selected_plant_ids))).all()) if payload.selected_plant_ids else []
    selected_slugs = [plant.slug for plant in selected_plants if plant.slug]
    result = GardenRecommendationService(db=db).recommend_for_garden(
        context_to_dto(context),
        GardenGoalInput(
            goals=_legacy_goal_values(payload.goal),
            primary_goal=_legacy_goal(payload.goal),
            maintenance_preference=_legacy_maintenance(payload.maintenance_preference),
            experience_level="beginner",
            start_preference=payload.start_preference,
            notes=payload.free_text_preferences,
        ),
        selected_plant_slugs=selected_slugs,
        selected_cultivar_slugs=[],
        limit=12,
    )
    plants_by_slug = {plant.slug: plant for plant in db.scalars(select(Plant)).all() if plant.slug}
    return _legacy_suggestions(result, plants_by_slug)


def _legacy_suggestions(result: GardenRecommendationResult, plants_by_slug: dict[str, Plant]) -> list[PlantSuggestion]:
    suggestions: list[PlantSuggestion] = []
    for recommendation in result.recommendations:
        plant = plants_by_slug.get(recommendation.plant_slug)
        if plant is None or recommendation.recommendation_type == "warning_only":
            continue
        suggestions.append(
            PlantSuggestion(
                plant=plant,
                score=int(round(recommendation.score)),
                reasons=_legacy_reasons(recommendation.explanation, recommendation.reason_codes, recommendation.warnings),
            )
        )
    return suggestions


def _legacy_reasons(explanation: str, reason_codes: list[str], warnings: list[str]) -> list[str]:
    reasons = [explanation, *[code.lower().replace("_", " ") for code in reason_codes[:4]]]
    if warnings:
        reasons.append(warnings[0])
    return reasons


def _legacy_goal(value: str) -> str:
    normalized = value.lower().replace(" ", "_")
    return {
        "food": "food",
        "flowers": "flowers",
        "shade": "shade",
        "pollinators": "pollinators",
        "herbs": "herbs",
        "fruit": "fruit",
        "native_plants": "native_plants",
        "combination": "combination",
    }.get(normalized, "combination")


def _legacy_goal_values(value: str) -> list[str]:
    goal = _legacy_goal(value)
    return ["food", "flowers", "pollinators", "combination"] if goal == "combination" else [goal]


def _legacy_maintenance(value: str) -> str:
    normalized = value.lower()
    if normalized in {"intensive", "high"}:
        return "high"
    if normalized == "low":
        return "low"
    return "moderate"


def _title_case(value: str) -> str:
    return " ".join(part.capitalize() for part in value.split())
