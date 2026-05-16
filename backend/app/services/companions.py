from app.models import Plant, PlantCompanionRelationship


def companion_notes(plants: list[Plant], relationships: list[PlantCompanionRelationship]) -> list[str]:
    selected = {plant.id: plant for plant in plants}
    notes: list[str] = []
    for rel in relationships:
        if rel.source_plant_id in selected and rel.target_plant_id in selected:
            notes.append(
                f"{selected[rel.source_plant_id].common_name.title()} and "
                f"{selected[rel.target_plant_id].common_name.title()}: "
                f"{rel.relationship_type}. {rel.rationale}"
            )
    return notes


def relationship_lookup(relationships: list[PlantCompanionRelationship]) -> dict[tuple[int, int], str]:
    lookup: dict[tuple[int, int], str] = {}
    for rel in relationships:
        lookup[(rel.source_plant_id, rel.target_plant_id)] = rel.relationship_type
        if rel.relationship_direction == "symmetric":
            lookup[(rel.target_plant_id, rel.source_plant_id)] = rel.relationship_type
    return lookup
