from app.plant_kb.companion_relationships import relationship_seed_for_sqlite
from app.plant_kb.seed_data import plant_records

PLANTS = [
    (
        plant["slug"],
        plant["scientific_name"],
        plant["plant_category"],
        plant["edible"],
        plant["ornamental"] or (plant["pollinator_value_score"] or 0) >= 7,
        plant["is_tree"],
        plant["lifecycle"] == "perennial",
        plant["min_hardiness_zone"] or 1,
        plant["max_hardiness_zone"] or 13,
        plant["sunlight_requirement"].replace("_", " ").title().replace("Sun", "Sun"),
        plant["water_requirement"],
        plant["typical_spacing_inches"] or 12,
        plant["typical_row_spacing_inches"] or 12,
        plant["typical_days_to_maturity_max"],
        plant["maintenance_level"].title(),
        plant["notes"] or "",
    )
    for plant in plant_records()
]

COMPANIONS = [
    (row["source_plant_slug"], row["target_plant_slug"], row["relationship_type"], row["rationale"])
    for row in relationship_seed_for_sqlite()
]
