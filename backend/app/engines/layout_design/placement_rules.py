from app.engines.layout_design.schemas import PlacementRule
from app.engines.planting_design.schemas import PlantingDesignPlan


def placement_rules_from_design(design_plan: PlantingDesignPlan) -> list[PlacementRule]:
    rules: list[PlacementRule] = []
    for cluster in design_plan.companion_clusters:
        near = [cluster.anchor_plant_slug, *cluster.companion_plant_slugs]
        if len(near) > 1:
            rules.append(PlacementRule(rule_type="place_near", plant_slugs=near, rationale=cluster.placement_guidance, priority="high"))
        if cluster.border_plant_slugs:
            rules.append(PlacementRule(rule_type="border", plant_slugs=cluster.border_plant_slugs, rationale="Use these plants at row ends, bed edges, or garden borders.", priority="medium"))
        if cluster.filler_plant_slugs:
            rules.append(PlacementRule(rule_type="interplant", plant_slugs=[cluster.anchor_plant_slug, *cluster.filler_plant_slugs], rationale="Use filler crops near the anchor where spacing allows.", priority="medium"))
    for rule in design_plan.separation_rules:
        rules.append(
            PlacementRule(
                rule_type="isolate" if rule.placement_guidance in {"isolate", "containerize"} else "keep_apart",
                plant_slugs=rule.plant_slugs,
                rationale=rule.rationale,
                priority="high" if rule.severity == "high" else "medium",
            )
        )
    for role in design_plan.plant_roles:
        if role.role in {"tree", "shrub"}:
            rules.append(PlacementRule(rule_type="separate_section", plant_slugs=[role.plant_slug], rationale=role.rationale, priority="high"))
        elif role.role in {"tall_crop", "trellised_crop"}:
            rules.append(PlacementRule(rule_type="north_edge", plant_slugs=[role.plant_slug], rationale=role.rationale, priority="medium"))
        elif role.role == "sprawling_crop":
            rules.append(PlacementRule(rule_type="edge_sprawl", plant_slugs=[role.plant_slug], rationale=role.rationale, priority="medium"))
    return _unique_rules(rules)


def _unique_rules(rules: list[PlacementRule]) -> list[PlacementRule]:
    seen: set[tuple[str, tuple[str, ...]]] = set()
    result: list[PlacementRule] = []
    for rule in rules:
        identity = (rule.rule_type, tuple(rule.plant_slugs))
        if identity in seen:
            continue
        seen.add(identity)
        result.append(rule)
    return result

