from app.models import Garden, Plant, PlantCompanionRelationship
from app.schemas.plan import GardenGoals, GeneratedPlan
from app.services.companions import CompanionGraphService, companion_notes
from app.services.layout import LayoutEngine


class GardenPlanner:
    def generate(
        self,
        garden: Garden,
        plants: list[Plant],
        relationships: list[PlantCompanionRelationship],
        goals: GardenGoals,
    ) -> GeneratedPlan:
        raise NotImplementedError


class RuleBasedGardenPlanner(GardenPlanner):
    def __init__(self, layout_engine: LayoutEngine | None = None) -> None:
        self.layout_engine = layout_engine or LayoutEngine()

    def generate(
        self,
        garden: Garden,
        plants: list[Plant],
        relationships: list[PlantCompanionRelationship],
        goals: GardenGoals,
    ) -> GeneratedPlan:
        companion_graph = CompanionGraphService(relationships=relationships, plants=plants)
        layout = self.layout_engine.generate_layout(garden, plants, companion_graph=companion_graph)
        notes = companion_notes(plants, relationships)
        avoided = [note for note in notes if ": avoid." in note.lower()]
        if avoided:
            notes.append("Avoid relationships were detected; layout separates these where possible in the simple grid.")
        notes.extend(layout.warnings)

        return GeneratedPlan(
            garden_id=garden.id,
            summary=(
                f"Deterministic JakeGPT v0 plan for a {garden.area_sq_ft:.0f} sq ft garden. "
                "Tall plants are placed toward the north/top edge, access space is reserved by keeping the grid sparse."
            ),
            layout_grid=layout.layout_grid,
            items=layout.items,
            companion_notes=notes,
            goals=goals,
        )
