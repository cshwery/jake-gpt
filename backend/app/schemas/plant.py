from pydantic import BaseModel


class PlantRead(BaseModel):
    id: int
    slug: str | None = None
    common_name: str
    scientific_name: str | None = None
    plant_type: str
    edible: bool
    flower: bool
    tree: bool
    perennial: bool
    min_zone: int
    max_zone: int
    sunlight_requirement: str
    water_requirement: str
    spacing_inches: int
    row_spacing_inches: int
    days_to_maturity: int | None = None
    maintenance_level: str
    planting_notes: str

    model_config = {"from_attributes": True}


class PlantSearchResult(PlantRead):
    result_type: str = "species"
    plant_id: int | None = None
    cultivar_id: int | None = None
    cultivar_slug: str | None = None
    cultivar_name: str | None = None
    display_name: str | None = None
    cultivar_notes: str | None = None


class SuggestRequest(BaseModel):
    garden_id: int
    goal: str
    maintenance_preference: str
    sunlight: str
    selected_plant_ids: list[int] = []
    free_text_preferences: str | None = None


class PlantSuggestion(BaseModel):
    plant: PlantRead
    score: int
    reasons: list[str]
