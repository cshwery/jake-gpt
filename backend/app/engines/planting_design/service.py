from typing import Any

from app.models import Plant, PlantCultivar
from app.schemas.garden import GardenContextDTO
from app.services.companions import CompanionGraphService
from app.services.garden_recommendations import GardenRecommendationResult

from app.engines.planting_design.cluster_builder import CompanionClusterBuilder
from app.engines.planting_design.role_classifier import PlantRoleClassifier
from app.engines.planting_design.schemas import PlacementGuidance, PlantingDesignPlan
from app.engines.planting_design.separation_rules import SeparationRuleBuilder


class PlantingDesignService:
    def __init__(
        self,
        role_classifier: PlantRoleClassifier | None = None,
        cluster_builder: CompanionClusterBuilder | None = None,
        separation_builder: SeparationRuleBuilder | None = None,
    ) -> None:
        self.role_classifier = role_classifier or PlantRoleClassifier()
        self.cluster_builder = cluster_builder or CompanionClusterBuilder()
        self.separation_builder = separation_builder or SeparationRuleBuilder()

    def create_design_plan(
        self,
        garden_context: GardenContextDTO | Any,
        plants: list[Plant],
        cultivars: list[PlantCultivar] | None,
        companion_graph: CompanionGraphService | None,
        garden_goals: Any | None = None,
        recommendation_result: GardenRecommendationResult | None = None,
        organization_style: str = "rows",
    ) -> PlantingDesignPlan:
        organization_style = _normalize_style(organization_style)
        cultivar_by_plant = {cultivar.plant_id: cultivar for cultivar in cultivars or []}
        selected_slugs = [_plant_slug(plant) for plant in plants]
        plant_roles = [
            role
            for plant in plants
            for role in self.role_classifier.classify(
                plant,
                cultivar=cultivar_by_plant.get(plant.id),
                companion_graph=companion_graph,
                selected_slugs=selected_slugs,
            )
        ]
        separation_rules = self.separation_builder.build(plants, companion_graph)
        companion_clusters, plant_groups, pollinator_border = self.cluster_builder.build(
            plants,
            plant_roles,
            companion_graph=companion_graph,
            organization_style=organization_style,
        )
        guidance = _guidance_for_style(organization_style, plant_roles, separation_rules)
        warnings = [rule.rationale for rule in separation_rules if rule.severity in {"medium", "high"}]
        summary = _summary(organization_style, companion_clusters, separation_rules, pollinator_border)
        assumptions = [
            "Planting design uses deterministic garden heuristics and companion graph evidence.",
            "Design guidance is advisory; final spacing still depends on cultivar, pruning, support, and local conditions.",
        ]
        if recommendation_result is None:
            assumptions.append("No recommendation run was attached, so design used selected plants and companion graph data only.")
        return PlantingDesignPlan(
            organization_style=organization_style,
            summary=summary,
            plant_roles=plant_roles,
            plant_groups=plant_groups,
            companion_clusters=companion_clusters,
            pollinator_border=pollinator_border,
            separation_rules=separation_rules,
            placement_guidance=guidance,
            warnings=_unique(warnings),
            assumptions=assumptions,
        )


def _guidance_for_style(organization_style: str, plant_roles, separation_rules) -> PlacementGuidance:
    tall = sorted({role.plant_slug for role in plant_roles if role.role in {"tall_crop", "trellised_crop"}})
    sprawling = sorted({role.plant_slug for role in plant_roles if role.role == "sprawling_crop"})
    woody = sorted({role.plant_slug for role in plant_roles if role.role in {"tree", "shrub"}})
    pollinator = sorted({role.plant_slug for role in plant_roles if role.role in {"pollinator_flower", "border_plant"}})
    guidance = PlacementGuidance(
        north_south_guidance=["Place tall crops toward the north edge so they shade smaller crops less."] if tall else [],
        border_guidance=["Use flowers as repeated border/support plants instead of one isolated block."] if pollinator else [],
        spacing_guidance=[rule.rationale for rule in separation_rules],
    )
    if organization_style == "rows":
        guidance.rows_guidance = [
            "Primary crops get rows; companion herbs can be adjacent rows or interplanted near anchors.",
            "Flowers work best at row ends and borders.",
        ]
        if woody:
            guidance.rows_guidance.append("Trees and shrubs belong in a separate Trees & Bushes section, not crop rows.")
        if sprawling:
            guidance.rows_guidance.append("Sprawling crops should use edge rows or a dedicated edge area.")
    elif organization_style == "raised_beds":
        guidance.raised_beds_guidance = [
            "Use bed-level companion clusters instead of one isolated block per plant.",
            "Repeat pollinator or border flowers around bed edges.",
            "Interplant herbs near primary crops they support.",
            "Tree crops are not recommended for raised beds unless using a dwarf variety.",
        ]
    elif organization_style == "chaos":
        guidance.chaos_guidance = [
            "Chaos mode gives guidance rather than a detailed placement map.",
            "Scatter compatible plants in small clusters and thin seedlings to comfortable spacing.",
            "Scatter flowers and herbs among crops and along borders.",
            "Isolate aggressive plants and keep warned combinations apart.",
        ]
    else:
        guidance.rows_guidance = ["Use primary crop clusters, nearby companion herbs, and pollinator borders where practical."]
    return guidance


def _summary(organization_style: str, clusters, separation_rules, pollinator_border: list[str]) -> str:
    parts = [f"Planting design uses {organization_style.replace('_', ' ')} organization."]
    if clusters:
        parts.append(f"{len(clusters)} companion cluster{'s' if len(clusters) != 1 else ''} identified.")
    if pollinator_border:
        parts.append("Pollinator flowers are treated as repeated border/support plants.")
    if separation_rules:
        parts.append(f"{len(separation_rules)} keep-apart note{'s' if len(separation_rules) != 1 else ''} added.")
    return " ".join(parts)


def _normalize_style(value: str | None) -> str:
    if value in {"raised_beds", "rows", "chaos", "intensive_grid", "mixed", "grid"}:
        return value
    return "rows"


def _plant_slug(plant: Plant) -> str:
    return getattr(plant, "slug", None) or plant.common_name.lower().replace(" ", "_")


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
