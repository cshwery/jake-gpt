from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Garden, GardenContext, Plant, PlantCompanionRelationship, PlantCultivar, User
from app.schemas.plant import PlantSearchResult, PlantSuggestion, SuggestRequest
from app.services.recommendations import suggest_plants

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
    plants = list(db.scalars(stmt).all())
    results = [
        PlantSearchResult.model_validate(plant).model_copy(
            update={"result_type": "species", "plant_id": plant.id, "display_name": plant.common_name}
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
                        "display_name": f"{plant.common_name} > {cultivar.cultivar_name}",
                        "cultivar_notes": cultivar.notes,
                    }
                )
            )
    return results


@router.post("/suggest", response_model=list[PlantSuggestion])
def suggest(payload: SuggestRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[PlantSuggestion]:
    garden = db.get(Garden, payload.garden_id)
    if garden is None or garden.property.user_id != user.id:
        raise HTTPException(status_code=404, detail="Garden not found")
    context = db.scalar(select(GardenContext).where(GardenContext.garden_id == garden.id))
    if context is None:
        raise HTTPException(status_code=400, detail="Garden context is required before suggestions")
    plants = list(db.scalars(select(Plant)).all())
    relationships = list(db.scalars(select(PlantCompanionRelationship)).all())
    return suggest_plants(
        plants,
        garden,
        context,
        payload.goal,
        payload.maintenance_preference,
        payload.sunlight,
        payload.selected_plant_ids,
        relationships,
    )
