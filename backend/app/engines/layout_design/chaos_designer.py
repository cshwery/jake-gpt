from app.models import Plant

from app.engines.layout_design.schemas import ChaosBlueprint
from app.engines.planting_design.schemas import PlantingDesignPlan


class ChaosLayoutDesigner:
    def design(self, design_plan: PlantingDesignPlan, plants: list[Plant]) -> ChaosBlueprint:
        roles = _roles_by_slug(design_plan)
        name_by_slug = {_slug(plant): plant.common_name.title() for plant in plants}
        easy = [
            name_by_slug[slug]
            for slug, plant_roles in roles.items()
            if slug in name_by_slug and plant_roles & {"leafy_green", "root_crop", "filler_crop", "primary_crop"} and not plant_roles & {"tree", "shrub", "sprawling_crop"}
        ]
        low = [
            plant.common_name.title()
            for plant in plants
            if (getattr(plant, "maintenance_level", "") or "").lower() in {"low", "easy"}
            or getattr(plant, "direct_sow_allowed", False)
        ]
        pollinator = [name_by_slug[slug] for slug, plant_roles in roles.items() if slug in name_by_slug and plant_roles & {"pollinator_flower", "border_plant"}]
        isolate = [name_by_slug[slug] for slug, plant_roles in roles.items() if slug in name_by_slug and plant_roles & {"tree", "shrub", "avoid_or_isolate"}]
        return ChaosBlueprint(
            suggested_plant_count_range=_count_range(len(plants)),
            easy_direct_sow_plants=sorted(set(easy)),
            low_maintenance_plants=sorted(set(low)),
            pollinator_support_plants=sorted(set(pollinator)),
            plants_to_isolate=sorted(set(isolate)),
            keep_apart_notes=[rule.rationale for rule in design_plan.separation_rules],
            scatter_guidance=[
                "Scatter compatible plants in small clusters instead of rows or a grid.",
                "Repeat flowers and herbs through the garden and along borders.",
                "Keep taller crops toward the north edge when practical.",
                "Give sprawling plants an edge and isolate aggressive plants.",
            ],
            warnings=design_plan.warnings,
        )


def _roles_by_slug(design_plan: PlantingDesignPlan) -> dict[str, set[str]]:
    roles: dict[str, set[str]] = {}
    for role in design_plan.plant_roles:
        roles.setdefault(role.plant_slug, set()).add(role.role)
    return roles


def _slug(plant: Plant) -> str:
    return getattr(plant, "slug", None) or plant.common_name.lower().replace(" ", "_")


def _count_range(count: int) -> str:
    low = max(4, min(count, 8))
    high = max(low + 2, min(max(count + 4, 10), 16))
    return f"{low}-{high}"
