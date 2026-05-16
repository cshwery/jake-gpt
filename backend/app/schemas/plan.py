from typing import Any

from pydantic import BaseModel


class GardenGoals(BaseModel):
    goal: str
    maintenance_preference: str
    sunlight: str
    free_text_preferences: str | None = None


class GeneratePlanRequest(BaseModel):
    garden_id: int
    selected_plant_ids: list[int]
    goals: GardenGoals


class PlanItemRead(BaseModel):
    id: int | None = None
    plant_id: int
    label: str
    row: int
    col: int
    width: int = 1
    height: int = 1
    quantity: int = 1
    x_pct: float
    y_pct: float
    notes: str | None = None

    model_config = {"from_attributes": True}


class GeneratedPlan(BaseModel):
    id: int | None = None
    garden_id: int
    summary: str
    layout_grid: dict[str, Any]
    items: list[PlanItemRead]
    companion_notes: list[str]
    goals: GardenGoals


class SavePlanRequest(BaseModel):
    generated_plan: GeneratedPlan
