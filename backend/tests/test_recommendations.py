from types import SimpleNamespace

from app.services.recommendations import score_plant


def test_recommendation_scoring_matches_goal_zone_and_sun() -> None:
    plant = SimpleNamespace(
        id=1,
        common_name="tomato",
        edible=True,
        flower=True,
        tree=False,
        min_zone=3,
        max_zone=10,
        sunlight_requirement="Full Sun",
        maintenance_level="Moderate",
    )

    score, reasons = score_plant(plant, "Food", "Moderate", "Full Sun", "6b", [], [])

    assert score >= 13
    assert "supports food production" in reasons


def test_recommendation_scoring_uses_canonical_relationship_shape() -> None:
    plant = SimpleNamespace(
        id=1,
        common_name="basil",
        edible=True,
        flower=False,
        tree=False,
        min_zone=3,
        max_zone=10,
        sunlight_requirement="Full Sun",
        maintenance_level="Moderate",
    )
    rel = SimpleNamespace(
        source_plant_id=2,
        target_plant_id=1,
        relationship_type="beneficial",
        relationship_direction="symmetric",
    )

    score, reasons = score_plant(plant, "Food", "Moderate", "Full Sun", "6b", [2], [rel])

    assert score >= 15
    assert "benefits a selected companion" in reasons
