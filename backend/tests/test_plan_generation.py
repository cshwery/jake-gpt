from types import SimpleNamespace

from app.agents.planner import RuleBasedGardenPlanner
from app.schemas.plan import GardenGoals


def test_plan_generation_is_deterministic() -> None:
    garden = SimpleNamespace(id=7, area_sq_ft=240)
    plants = [
        SimpleNamespace(id=2, common_name="basil", tree=False, spacing_inches=12, row_spacing_inches=18, planting_notes="Pinch."),
        SimpleNamespace(id=1, common_name="tomato", tree=False, spacing_inches=24, row_spacing_inches=36, planting_notes="Stake."),
    ]
    rels = [SimpleNamespace(source_plant_id=1, target_plant_id=2, relationship_type="beneficial", rationale="Good neighbors.", relationship_direction="symmetric")]
    goals = GardenGoals(goal="Food", maintenance_preference="Moderate", sunlight="Full Sun")

    first = RuleBasedGardenPlanner().generate(garden, plants, rels, goals)
    second = RuleBasedGardenPlanner().generate(garden, plants, rels, goals)

    assert first.model_dump() == second.model_dump()
    assert first.layout_grid["cols"] == 4
    assert any("Tomato and Basil" in note for note in first.companion_notes)
