import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Plant, PlantCompanionRelationship, PlantCultivar
from app.services.companions import CompanionGraphService, score_edge


def test_symmetric_relationship_lookup_works_both_ways() -> None:
    graph = _graph(
        [
            _plant(1, "tomato"),
            _plant(2, "basil"),
        ],
        [
            _relationship(1, 1, 2, "beneficial", direction="symmetric"),
        ],
    )

    assert graph.get_relationship("tomato", "basil").relationship_type == "beneficial"
    assert graph.get_relationship("basil", "tomato").relationship_type == "beneficial"


def test_one_way_relationship_lookup_preserves_direction() -> None:
    graph = _graph(
        [
            _plant(1, "sunflower"),
            _plant(2, "lettuce"),
        ],
        [
            _relationship(1, 1, 2, "shade_support", direction="one_way"),
        ],
    )

    assert graph.get_relationship("sunflower", "lettuce").relationship_type == "shade_support"
    assert graph.get_relationship("lettuce", "sunflower") is None


def test_edge_scoring_applies_relationship_confidence_and_evidence_weights() -> None:
    assert score_edge("beneficial", "high", "extension_service") == pytest.approx(20.0)
    assert score_edge("beneficial", "medium", "master_gardener") == pytest.approx(11.05)
    assert score_edge("avoid", "high", "peer_reviewed") == pytest.approx(-35.0)


def test_positive_and_negative_companion_lookup() -> None:
    graph = _graph(
        [
            _plant(1, "tomato"),
            _plant(2, "basil"),
            _plant(3, "potato"),
        ],
        [
            _relationship(1, 1, 2, "beneficial"),
            _relationship(2, 1, 3, "disease_risk"),
        ],
    )

    assert [edge.target_plant_slug for edge in graph.get_positive_companions("tomato")] == ["basil"]
    assert [edge.target_plant_slug for edge in graph.get_negative_companions("tomato")] == ["potato"]


def test_conflict_detection_returns_negative_relationships_with_actions() -> None:
    graph = _graph(
        [
            _plant(1, "tomato"),
            _plant(2, "potato"),
            _plant(3, "basil"),
        ],
        [
            _relationship(1, 1, 2, "disease_risk", rationale="Both are nightshades and can share disease pressure."),
            _relationship(2, 1, 3, "beneficial"),
        ],
    )

    conflicts = graph.find_conflicts(["tomato", "potato", "basil"])

    assert len(conflicts) == 1
    assert conflicts[0].source_plant_slug == "tomato"
    assert conflicts[0].target_plant_slug == "potato"
    assert conflicts[0].relationship_type == "disease_risk"
    assert conflicts[0].score < 0
    assert "Avoid close clustering" in conflicts[0].suggested_action


def test_companion_suggestion_ranking_uses_total_relationship_score() -> None:
    graph = _graph(
        [
            _plant(1, "tomato"),
            _plant(2, "basil"),
            _plant(3, "marigold"),
            _plant(4, "potato"),
        ],
        [
            _relationship(1, 2, 1, "beneficial", confidence="high"),
            _relationship(2, 3, 1, "pollinator_support", confidence="medium"),
            _relationship(3, 4, 1, "avoid", confidence="high"),
        ],
    )

    suggestions = graph.suggest_companions(["tomato"], ["basil", "marigold", "potato"])

    assert [suggestion.plant_slug for suggestion in suggestions] == ["basil", "marigold"]
    assert suggestions[0].score > suggestions[1].score
    assert any("beneficial" in explanation for explanation in suggestions[0].explanations)


def test_generated_inference_has_lower_weight_than_extension_relationship() -> None:
    extension_score = score_edge("beneficial", "low", "extension_service")
    generated_score = score_edge("beneficial", "low", "generated_inference")

    assert generated_score == pytest.approx(1.5)
    assert generated_score < extension_score


def test_avoid_relationship_overrides_weak_beneficial_relationship() -> None:
    graph = _graph(
        [
            _plant(1, "tomato"),
            _plant(2, "potato"),
        ],
        [
            _relationship(1, 1, 2, "beneficial", confidence="low", evidence_type="generated_inference"),
            _relationship(2, 1, 2, "avoid", confidence="high", evidence_type="extension_service"),
        ],
    )

    assert graph.get_relationship("tomato", "potato").relationship_type == "avoid"
    assert graph.score_pair("tomato", "potato") < 0
    assert graph.suggest_companions(["tomato"], ["potato"]) == []


def test_graph_service_loads_canonical_relationships_from_database() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    for table in [Plant.__table__, PlantCultivar.__table__, PlantCompanionRelationship.__table__]:
        table.create(engine)

    with Session(engine) as session:
        session.add_all([_plant(1, "tomato"), _plant(2, "basil")])
        session.add(_relationship(1, 1, 2, "beneficial"))
        session.commit()

        graph = CompanionGraphService.from_db(session)

    assert graph.score_pair("tomato", "basil") > 0


def _graph(plants: list[Plant], relationships: list[PlantCompanionRelationship]) -> CompanionGraphService:
    return CompanionGraphService(plants=plants, relationships=relationships)


def _plant(id: int, slug: str) -> Plant:
    return Plant(
        id=id,
        slug=slug,
        common_name=slug.replace("-", " ").title(),
        plant_type="vegetable",
        edible=True,
        flower=False,
        tree=False,
        perennial=False,
        min_zone=3,
        max_zone=10,
        sunlight_requirement="Full Sun",
        water_requirement="medium",
        spacing_inches=12,
        row_spacing_inches=24,
        maintenance_level="Moderate",
        planting_notes="Test plant.",
    )


def _relationship(
    id: int,
    source_plant_id: int,
    target_plant_id: int,
    relationship_type: str,
    *,
    confidence: str = "medium",
    evidence_type: str = "extension_service",
    rationale: str = "Test relationship.",
    direction: str = "symmetric",
) -> PlantCompanionRelationship:
    return PlantCompanionRelationship(
        id=id,
        source_plant_id=source_plant_id,
        target_plant_id=target_plant_id,
        relationship_type=relationship_type,
        confidence=confidence,
        evidence_type=evidence_type,
        rationale=rationale,
        source_name="Test Source",
        source_url="https://example.com",
        relationship_direction=direction,
        source_notes="Test source notes.",
    )
