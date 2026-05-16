from app.models import Garden, GardenContext, Plant, PlantCompanionRelationship
from app.schemas.plant import PlantSuggestion


BENEFICIAL_RECOMMENDATION_TYPES = {"beneficial", "guild", "pollinator_support", "pest_deterrent", "nutrient_support", "shade_support", "spatial_compatibility"}
AVOID_RECOMMENDATION_TYPES = {"avoid", "disease_risk", "pest_risk", "allelopathy", "competition"}


def parse_zone(zone: str) -> int:
    digits = "".join(ch for ch in zone if ch.isdigit())
    return int(digits or "6")


def score_plant(
    plant: Plant,
    goal: str,
    maintenance: str,
    sunlight: str,
    zone: str,
    selected_ids: list[int],
    relationships: list[PlantCompanionRelationship],
) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    zone_num = parse_zone(zone)
    goal_lower = goal.lower()

    if plant.min_zone <= zone_num <= plant.max_zone:
        score += 4
        reasons.append(f"fits hardiness zone {zone}")
    if sunlight == plant.sunlight_requirement or plant.sunlight_requirement in {"Full Sun", "Part Sun"} and sunlight in {"Full Sun", "Part Sun"}:
        score += 3
        reasons.append(f"matches {sunlight.lower()} conditions")
    if goal_lower == "food" and plant.edible:
        score += 4
        reasons.append("supports food production")
    if goal_lower == "flowers" and plant.flower:
        score += 4
        reasons.append("adds flowers")
    if goal_lower == "shade" and plant.tree:
        score += 4
        reasons.append("can provide shade")
    if goal_lower == "combination" and (plant.edible or plant.flower or plant.tree):
        score += 3
        reasons.append("supports a mixed garden")
    if plant.maintenance_level.lower() == maintenance.lower():
        score += 2
        reasons.append(f"matches {maintenance.lower()} maintenance")

    selected = set(selected_ids)
    for rel in relationships:
        matches_forward = rel.source_plant_id == plant.id and rel.target_plant_id in selected
        matches_symmetric = rel.relationship_direction == "symmetric" and rel.target_plant_id == plant.id and rel.source_plant_id in selected
        if not matches_forward and not matches_symmetric:
            continue
        if rel.relationship_type in BENEFICIAL_RECOMMENDATION_TYPES:
            score += 2
            reasons.append("benefits a selected companion")
        elif rel.relationship_type in AVOID_RECOMMENDATION_TYPES:
            score -= 4
            reasons.append("conflicts with a selected plant")
    return score, reasons


def suggest_plants(
    plants: list[Plant],
    garden: Garden,
    context: GardenContext,
    goal: str,
    maintenance: str,
    sunlight: str,
    selected_ids: list[int],
    relationships: list[PlantCompanionRelationship],
) -> list[PlantSuggestion]:
    scored = []
    for plant in plants:
        score, reasons = score_plant(plant, goal, maintenance, sunlight, context.hardiness_zone, selected_ids, relationships)
        if score > 0:
            scored.append(PlantSuggestion(plant=plant, score=score, reasons=reasons))
    return sorted(scored, key=lambda item: (-item.score, item.plant.common_name))[:12]
