from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import CompanionRelationshipCandidate, Plant, PlantCompanionRelationship
from app.plant_kb.companion_report import build_candidate_report, build_report, build_reports


def test_companion_report_contains_required_sections(tmp_path) -> None:
    report_path = tmp_path / "companion_report.md"

    content = build_report(report_path=report_path)

    assert report_path.exists()
    assert "## 1. Summary" in content
    assert "## 2. High-confidence relationships" in content
    assert "## 3. Medium-confidence relationships" in content
    assert "## 4. Low-confidence/generated relationships" in content
    assert "## 5. Avoid relationships" in content
    assert "## 6. Conflicts needing review" in content
    assert "## 7. Missing data" in content
    assert "## 8. Suggested next research targets" in content
    assert "Generated candidates needing review" not in content


def test_companion_report_splits_canonical_and_candidate_tables(tmp_path) -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    for table in [Plant.__table__, PlantCompanionRelationship.__table__, CompanionRelationshipCandidate.__table__]:
        table.create(engine)
    with Session(engine) as session:
        session.add_all([_plant(1, "tomato", "Tomato"), _plant(2, "basil", "Basil"), _plant(3, "potato", "Potato")])
        session.add(
            PlantCompanionRelationship(
                source_plant_id=1,
                target_plant_id=2,
                relationship_type="beneficial",
                confidence="medium",
                evidence_type="extension_service",
                rationale="Canonical relationship.",
                source_name="Test Source",
                source_url="https://example.com",
                source_notes="Known source.",
                relationship_direction="symmetric",
            )
        )
        session.add_all(
            [
                _candidate("tomato-potato-risk", "tomato", "potato", "disease_risk", "needs_review"),
                _candidate("tomato-basil-duplicate", "tomato", "basil", "beneficial", "approved"),
                _candidate("basil-tomato-avoid", "basil", "tomato", "avoid", "needs_more_research"),
            ]
        )
        session.commit()

        reports = build_reports(tmp_path / "canonical.md", tmp_path / "candidates.md", db=session)

    assert (tmp_path / "canonical.md").exists()
    assert (tmp_path / "candidates.md").exists()
    assert "# Canonical Companion Relationship Report" in reports["canonical"]
    assert "# Companion Candidate Review Report" in reports["candidates"]
    assert "Total canonical relationships: 1" in reports["canonical"]
    assert "Total candidate relationships: 3" in reports["candidates"]
    assert "## 2. Candidates Needing Review" in reports["candidates"]
    assert "## 3. Approved Candidates Not Yet Promoted" in reports["candidates"]
    assert "## 6. Duplicate Canonical Relationships" in reports["candidates"]
    assert "## 7. Conflicts With Canonical Relationships" in reports["candidates"]
    assert "## 8. Candidate Pair Conflicts" in reports["candidates"]
    assert "## 11. High-Priority Review Candidates" in reports["candidates"]


def test_candidate_report_marks_missing_source_and_low_generated(tmp_path) -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    for table in [Plant.__table__, PlantCompanionRelationship.__table__, CompanionRelationshipCandidate.__table__]:
        table.create(engine)
    with Session(engine) as session:
        session.add_all([_plant(1, "tomato", "Tomato"), _plant(2, "potato", "Potato")])
        session.add(_candidate("tomato-potato-risk", "tomato", "potato", "disease_risk", "needs_review"))
        session.commit()

        content = build_candidate_report(tmp_path / "candidates.md", db=session)

    assert "Candidates missing source_name or source_url: 1" in content
    assert "## 10. Low-Confidence Generated Candidates" in content
    assert "Tomato -> Potato" in content


def _candidate(slug: str, source: str, target: str, relationship_type: str, status: str) -> CompanionRelationshipCandidate:
    return CompanionRelationshipCandidate(
        candidate_slug=slug,
        source_plant_slug=source,
        target_plant_slug=target,
        relationship_type=relationship_type,
        confidence="low",
        evidence_type="generated_inference",
        rationale="Candidate relationship.",
        relationship_direction="symmetric",
        generation_rule="test_rule",
        review_status=status,
    )


def _plant(id: int, slug: str, common_name: str) -> Plant:
    return Plant(
        id=id,
        slug=slug,
        common_name=common_name,
        plant_type="vegetable",
        edible=True,
        flower=False,
        tree=False,
        perennial=False,
        min_zone=3,
        max_zone=10,
        sunlight_requirement="full_sun",
        water_requirement="medium",
        spacing_inches=12,
        row_spacing_inches=24,
        maintenance_level="low",
        planting_notes="Test plant.",
    )
