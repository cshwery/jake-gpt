from __future__ import annotations

from dataclasses import dataclass

from app.models import Plant, PlantCompanionRelationship, PlantCultivar


@dataclass(frozen=True)
class ResolvedPlantProfile:
    plant: Plant
    cultivar: PlantCultivar | None
    display_name: str
    sunlight_requirement: str
    water_requirement: str
    spacing_inches: int | None
    row_spacing_inches: int | None
    days_to_maturity_min: int | None
    days_to_maturity_max: int | None
    min_hardiness_zone: int | None
    max_hardiness_zone: int | None
    notes: str | None


def search_species_and_cultivars(plants: list[Plant], cultivars: list[PlantCultivar], query: str | None) -> list[str]:
    needle = (query or "").strip().lower()
    results: list[str] = []
    for plant in sorted(plants, key=lambda item: item.common_name):
        if not needle or needle in plant.common_name.lower() or needle in (plant.slug or ""):
            results.append(plant.common_name)
    plants_by_id = {plant.id: plant for plant in plants}
    for cultivar in sorted(cultivars, key=lambda item: (plants_by_id[item.plant_id].common_name, item.cultivar_name)):
        plant = plants_by_id.get(cultivar.plant_id)
        if plant is None:
            continue
        haystack = f"{plant.common_name} {cultivar.cultivar_name} {cultivar.normalized_name} {cultivar.slug}".lower()
        if not needle or needle in haystack:
            results.append(f"{plant.common_name} > {cultivar.cultivar_name}")
    return results


def resolve_profile(plant: Plant, cultivar: PlantCultivar | None = None) -> ResolvedPlantProfile:
    display = plant.common_name if cultivar is None else f"{plant.common_name} - {cultivar.cultivar_name}"
    return ResolvedPlantProfile(
        plant=plant,
        cultivar=cultivar,
        display_name=display,
        sunlight_requirement=(cultivar.sunlight_requirement_override if cultivar else None) or plant.sunlight_requirement,
        water_requirement=(cultivar.water_requirement_override if cultivar else None) or plant.water_requirement,
        spacing_inches=(cultivar.spacing_inches_override if cultivar else None) or plant.typical_spacing_inches or plant.spacing_inches,
        row_spacing_inches=(cultivar.row_spacing_inches_override if cultivar else None) or plant.typical_row_spacing_inches or plant.row_spacing_inches,
        days_to_maturity_min=(cultivar.days_to_maturity_min if cultivar else None) or plant.typical_days_to_maturity_min or plant.days_to_maturity,
        days_to_maturity_max=(cultivar.days_to_maturity_max if cultivar else None) or plant.typical_days_to_maturity_max or plant.days_to_maturity,
        min_hardiness_zone=(cultivar.min_hardiness_zone if cultivar else None) or plant.min_hardiness_zone or plant.min_zone,
        max_hardiness_zone=(cultivar.max_hardiness_zone if cultivar else None) or plant.max_hardiness_zone or plant.max_zone,
        notes=(cultivar.notes if cultivar else None) or plant.notes or plant.planting_notes,
    )


def relationship_lookup(relationships: list[PlantCompanionRelationship]) -> dict[tuple[int, int], PlantCompanionRelationship]:
    lookup: dict[tuple[int, int], PlantCompanionRelationship] = {}
    for rel in relationships:
        lookup[(rel.source_plant_id, rel.target_plant_id)] = rel
        if rel.relationship_direction == "symmetric":
            lookup[(rel.target_plant_id, rel.source_plant_id)] = rel
    return lookup


def avoid_conflicts(selected_plant_ids: list[int], relationships: list[PlantCompanionRelationship]) -> list[PlantCompanionRelationship]:
    selected = set(selected_plant_ids)
    conflicts = []
    for rel in relationships:
        if rel.relationship_type != "avoid":
            continue
        if rel.source_plant_id in selected and rel.target_plant_id in selected:
            conflicts.append(rel)
        elif rel.relationship_direction == "symmetric" and rel.target_plant_id in selected and rel.source_plant_id in selected:
            conflicts.append(rel)
    return conflicts


def score_species(
    plant: Plant,
    *,
    hardiness_zone: int | None,
    sunlight: str | None,
    water: str | None,
    goal: str | None,
    maintenance: str | None,
    available_space_inches: int | None = None,
    selected_plant_ids: list[int] | None = None,
    relationships: list[PlantCompanionRelationship] | None = None,
) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    if hardiness_zone is not None and (plant.min_hardiness_zone or plant.min_zone) <= hardiness_zone <= (plant.max_hardiness_zone or plant.max_zone):
        score += 4
        reasons.append("hardiness match")
    if sunlight and plant.sunlight_requirement == sunlight:
        score += 3
        reasons.append("sunlight match")
    if water and plant.water_requirement == water:
        score += 2
        reasons.append("water match")
    goal_lower = (goal or "").lower()
    if goal_lower in {"food", "edible"} and plant.edible:
        score += 4
        reasons.append("food goal")
    if goal_lower in {"pollinator", "flowers"}:
        score += plant.pollinator_value_score or 0
        reasons.append("pollinator value")
    if goal_lower == "shade" and (plant.is_tree or plant.tree):
        score += 4
        reasons.append("shade goal")
    if maintenance and plant.maintenance_level == maintenance:
        score += 2
        reasons.append("maintenance match")
    if plant.beginner_friendliness_score:
        score += min(3, plant.beginner_friendliness_score // 3)
    if available_space_inches and (plant.typical_spacing_inches or plant.spacing_inches) > available_space_inches:
        score -= 5
        reasons.append("space penalty")
    selected = set(selected_plant_ids or [])
    for rel in relationships or []:
        if rel.source_plant_id == plant.id and rel.target_plant_id in selected:
            if rel.relationship_type == "avoid":
                score -= 6
                reasons.append("avoid conflict")
            elif rel.relationship_type in {"beneficial", "guild", "pollinator_support", "pest_deterrent"}:
                score += 2
                reasons.append("companion bonus")
    return score, reasons


def score_cultivar(cultivar: PlantCultivar, plant: Plant, *, goal: str | None = None, max_days_to_maturity: int | None = None, container: bool = False) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    profile = resolve_profile(plant, cultivar)
    if max_days_to_maturity and profile.days_to_maturity_max and profile.days_to_maturity_max <= max_days_to_maturity:
        score += 3
        reasons.append("maturity fit")
    if cultivar.disease_resistance:
        score += 1
        reasons.append("disease notes available")
    if container and cultivar.container_friendly:
        score += 4
        reasons.append("container friendly")
    if cultivar.compact_variety:
        score += 2
        reasons.append("compact")
    goal_lower = (goal or "").lower()
    if goal_lower and cultivar.common_uses and goal_lower in cultivar.common_uses.lower():
        score += 3
        reasons.append("use match")
    for attr in (cultivar.heat_tolerance_score, cultivar.cold_tolerance_score, cultivar.drought_tolerance_score):
        if attr:
            score += min(2, attr // 4)
    return score, reasons
