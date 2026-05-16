from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.planner import RuleBasedGardenPlanner
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Garden, GardenPlan, PlanItem, Plant, PlantCompanionRelationship, User
from app.schemas.plan import GeneratedPlan, GeneratePlanRequest, SavePlanRequest

router = APIRouter(prefix="/plans", tags=["plans"])


@router.post("/generate", response_model=GeneratedPlan)
def generate_plan(payload: GeneratePlanRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> GeneratedPlan:
    garden = db.get(Garden, payload.garden_id)
    if garden is None or garden.property.user_id != user.id:
        raise HTTPException(status_code=404, detail="Garden not found")
    plants = list(db.scalars(select(Plant).where(Plant.id.in_(payload.selected_plant_ids))).all())
    if not plants:
        raise HTTPException(status_code=400, detail="Select at least one plant")
    relationships = list(db.scalars(select(PlantCompanionRelationship)).all())
    return RuleBasedGardenPlanner().generate(garden, plants, relationships, payload.goals)


@router.post("", response_model=GeneratedPlan)
def save_plan(payload: SavePlanRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> GeneratedPlan:
    generated = payload.generated_plan
    garden = db.get(Garden, generated.garden_id)
    if garden is None or garden.property.user_id != user.id:
        raise HTTPException(status_code=404, detail="Garden not found")
    plan = GardenPlan(
        garden_id=garden.id,
        summary=generated.summary,
        layout_grid=generated.layout_grid,
        companion_notes=generated.companion_notes,
        goals=generated.goals.model_dump(),
    )
    db.add(plan)
    db.flush()
    for item in generated.items:
        db.add(PlanItem(plan_id=plan.id, **item.model_dump(exclude={"id"})))
    db.commit()
    db.refresh(plan)
    generated.id = plan.id
    return generated
