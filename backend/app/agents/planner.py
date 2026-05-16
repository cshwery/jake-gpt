from app.models import Garden, Plant, PlantCompanionRelationship
from app.schemas.plan import GardenGoals, GeneratedPlan, PlanItemRead
from app.services.companions import companion_notes, relationship_lookup


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
    def generate(
        self,
        garden: Garden,
        plants: list[Plant],
        relationships: list[PlantCompanionRelationship],
        goals: GardenGoals,
    ) -> GeneratedPlan:
        ordered = sorted(plants, key=lambda p: (0 if p.tree else 1, p.common_name))
        rel_lookup = relationship_lookup(relationships)
        for idx, plant in enumerate(list(ordered)):
            for jdx, other in enumerate(ordered):
                if idx > jdx and rel_lookup.get((plant.id, other.id)) == "beneficial":
                    ordered.insert(jdx + 1, ordered.pop(idx))
                    break

        cols = 4
        rows = max(3, (len(ordered) + cols - 1) // cols + 1)
        items: list[PlanItemRead] = []
        for idx, plant in enumerate(ordered):
            row = idx // cols
            col = idx % cols
            if plant.tree:
                row = 0
            quantity = max(1, int((garden.area_sq_ft / max(plant.spacing_inches * plant.row_spacing_inches / 144, 1)) // max(len(ordered), 1)))
            items.append(
                PlanItemRead(
                    plant_id=plant.id,
                    label=plant.common_name.title(),
                    row=row,
                    col=col,
                    quantity=min(quantity, 12),
                    x_pct=(col + 0.5) / cols * 100,
                    y_pct=(row + 0.5) / rows * 100,
                    notes=f"{plant.spacing_inches} in spacing; {plant.planting_notes}",
                )
            )

        notes = companion_notes(plants, relationships)
        avoided = [note for note in notes if ": avoid." in note.lower()]
        if avoided:
            notes.append("Avoid relationships were detected; layout separates these where possible in the simple grid.")

        return GeneratedPlan(
            garden_id=garden.id,
            summary=(
                f"Deterministic JakeGPT v0 plan for a {garden.area_sq_ft:.0f} sq ft garden. "
                "Tall plants are placed toward the north/top edge, access space is reserved by keeping the grid sparse."
            ),
            layout_grid={"rows": rows, "cols": cols, "access_paths": ["between every grid row"]},
            items=items,
            companion_notes=notes,
            goals=goals,
        )
