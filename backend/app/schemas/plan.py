from typing import Any, Literal

from pydantic import BaseModel, Field


PlantingStyle = Literal["rows", "intensive_grid", "raised_beds", "mixed"]
BedShape = Literal["rectangle", "square", "custom"]
DirectSowPreference = Literal["direct_sow_when_reasonable", "prefer_transplants", "no_preference"]


class GardenGoals(BaseModel):
    goals: list[str] = Field(default_factory=list)
    goal: str
    maintenance_preference: str
    experience_level: str = "beginner"
    sunlight: str
    free_text_preferences: str | None = None
    planting_style: PlantingStyle = "rows"
    using_raised_beds: bool | None = None
    raised_beds: dict[str, Any] | None = None
    start_preference: Literal["germinate_myself", "buy_from_nursery", "no_preference"] | None = None
    can_start_seeds_indoors: bool | None = None
    prefers_buying_starts: bool | None = None
    direct_sow_preference: DirectSowPreference | None = None


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
