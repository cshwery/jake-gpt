from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Garden, GardenLayout, GardenRecommendationRun, Plant, PlantCultivar, User
from app.engines.planting_design import PlantingDesignService
from app.services.companions import CompanionGraphService
from app.services.garden_context import GardenContextService
from app.services.garden_recommendations import GardenRecommendationResult
from app.services.layout import LayoutEngine
from app.services.layout.layout_schemas import LayoutGenerateRequest, LayoutResult

router = APIRouter(tags=["layouts"])


@router.post("/gardens/{garden_id}/layouts/generate", response_model=LayoutResult)
def generate_layout(
    garden_id: int,
    payload: LayoutGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> LayoutResult:
    garden = _authorize_garden(garden_id, db, user)
    try:
        context = GardenContextService(db).get_context(garden_id)
    except LookupError:
        raise HTTPException(status_code=400, detail="Generate garden context before creating a layout.")

    recommendation_run: GardenRecommendationRun | None = None
    recommendation_result: GardenRecommendationResult | None = None
    if payload.recommendation_run_id is not None:
        recommendation_run = db.get(GardenRecommendationRun, payload.recommendation_run_id)
        if recommendation_run is None or recommendation_run.garden_id != garden_id:
            raise HTTPException(status_code=404, detail="Recommendation run not found")
        recommendation_result = GardenRecommendationResult.model_validate(recommendation_run.result)

    selected_slugs = _unique([*payload.selected_plant_slugs, *payload.accepted_recommendation_slugs])
    cultivar_slugs = _unique([*payload.selected_cultivar_slugs, *payload.accepted_cultivar_slugs])
    plants = list(db.scalars(select(Plant).where(Plant.slug.in_(selected_slugs))).all()) if selected_slugs else []
    cultivars = list(db.scalars(select(PlantCultivar).where(PlantCultivar.slug.in_(cultivar_slugs))).all()) if cultivar_slugs else []
    cultivar_plant_ids = {cultivar.plant_id for cultivar in cultivars}
    missing_cultivar_plants = cultivar_plant_ids - {plant.id for plant in plants}
    if missing_cultivar_plants:
        plants.extend(db.scalars(select(Plant).where(Plant.id.in_(missing_cultivar_plants))).all())
    if not plants:
        raise HTTPException(status_code=400, detail="Select at least one plant before generating a layout.")

    companion_graph = CompanionGraphService.from_db(db)
    organization_style = "raised_beds" if payload.options.using_raised_beds else payload.options.layout_style
    design_plan = PlantingDesignService().create_design_plan(
        garden_context=context,
        plants=plants,
        cultivars=cultivars,
        companion_graph=companion_graph,
        garden_goals=None,
        recommendation_result=recommendation_result,
        organization_style=organization_style,
    )
    engine = LayoutEngine()
    result = engine.generate_layout(
        garden=garden,
        garden_context=context,
        plants=plants,
        cultivars=cultivars,
        companion_graph=companion_graph,
        recommendation_result=recommendation_result,
        options=payload.options,
        design_plan=design_plan,
    )
    result.recommendation_run_id = payload.recommendation_run_id
    if payload.options.persist:
        persisted = engine.persist_layout(
            result,
            db,
            garden=garden,
            recommendation_run_id=payload.recommendation_run_id,
            input_payload=payload.model_dump(mode="json"),
        )
        db.commit()
        result.layout_id = persisted.id
    return result


@router.get("/gardens/{garden_id}/layouts/latest", response_model=LayoutResult)
def latest_layout(garden_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> LayoutResult:
    _authorize_garden(garden_id, db, user)
    layout = db.scalar(select(GardenLayout).where(GardenLayout.garden_id == garden_id).order_by(desc(GardenLayout.created_at), desc(GardenLayout.id)))
    if layout is None:
        raise HTTPException(status_code=404, detail="No layout exists for this garden.")
    return _layout_to_result(layout)


@router.get("/layouts/{layout_id}", response_model=LayoutResult)
def get_layout(layout_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> LayoutResult:
    layout = db.get(GardenLayout, layout_id)
    if layout is None or layout.garden.property.user_id != user.id:
        raise HTTPException(status_code=404, detail="Layout not found")
    return _layout_to_result(layout)


def _authorize_garden(garden_id: int, db: Session, user: User) -> Garden:
    garden = db.get(Garden, garden_id)
    if garden is None or garden.property.user_id != user.id:
        raise HTTPException(status_code=404, detail="Garden not found")
    return garden


def _layout_to_result(layout: GardenLayout) -> LayoutResult:
    result = LayoutResult.model_validate(layout.result)
    result.layout_id = layout.id
    result.garden_id = layout.garden_id
    result.garden_plan_id = layout.garden_plan_id
    result.recommendation_run_id = layout.recommendation_run_id
    return result


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
