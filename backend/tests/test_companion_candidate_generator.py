import csv
import json
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import CompanionRelationshipCandidate, Plant, PlantCompanion, PlantCompanionRelationship, PlantCultivar
from app.plant_kb.companion_candidates import REVIEW_CSV_COLUMNS, candidate_slug_for, export_review_csv, import_candidate_jsonl, import_review_csv, promote_approved_candidates, promote_candidate
from app.plant_kb.generate_companion_candidates import generate_candidates


def test_legumes_generate_nutrient_support_candidates() -> None:
    candidates = generate_candidates()

    assert _find(candidates, "bean", "tomato", "nutrient_support")
    assert _find(candidates, "pea", "corn", "nutrient_support")


def test_pollinator_plants_generate_pollinator_support_candidates() -> None:
    candidates = generate_candidates()

    assert _find(candidates, "marigold", "tomato", "pollinator_support")
    assert _find(candidates, "borage", "strawberry", "pollinator_support")


def test_same_family_nightshades_generate_disease_risk_candidates() -> None:
    candidates = generate_candidates()

    assert _find_pair(candidates, "tomato", "pepper", "disease_risk")
    assert _find_pair(candidates, "eggplant", "potato", "disease_risk")


def test_fennel_generates_allelopathy_candidates() -> None:
    candidates = generate_candidates()

    assert _find(candidates, "fennel", "tomato", "allelopathy")
    assert _find(candidates, "fennel", "bean", "allelopathy")


def test_apiaceae_seed_saving_generates_avoid_candidates() -> None:
    candidates = generate_candidates()

    assert _find_pair(candidates, "cilantro", "dill", "avoid")
    assert _find_pair(candidates, "cilantro", "fennel", "avoid")
    assert _find_pair(candidates, "dill", "fennel", "avoid")
    candidate = next(
        candidate
        for candidate in candidates
        if candidate["relationship_type"] == "avoid"
        and {candidate["source_plant_slug"], candidate["target_plant_slug"]} == {"cilantro", "dill"}
    )
    assert candidate["generation_rule"] == "apiaceae_seed_saving_isolation_candidate"
    assert candidate["confidence"] == "low"
    assert candidate["evidence_type"] == "generated_inference"
    assert "seed-purity caution" in candidate["rationale"]


def test_generated_candidates_are_not_high_confidence_facts() -> None:
    candidates = generate_candidates()

    assert candidates
    assert all(candidate["candidate_slug"] for candidate in candidates)
    assert all(candidate["generation_rule"] for candidate in candidates)
    assert all(candidate["evidence_type"] == "generated_inference" for candidate in candidates)
    assert all(candidate["confidence"] == "low" for candidate in candidates)
    assert all(candidate["review_status"] == "needs_review" for candidate in candidates)
    assert all("source_name" not in candidate for candidate in candidates)


def test_candidate_slugs_are_stable_and_deterministic() -> None:
    first = candidate_slug_for("tomato", "basil", "pest_deterrent", "generated_inference", generation_rule="aromatic_diversity_candidate")
    second = candidate_slug_for("tomato", "basil", "pest_deterrent", "generated_inference", generation_rule="aromatic_diversity_candidate")

    assert first == second
    assert first == "tomato-basil-pest-deterrent-generated-inference-aromatic-diversity-candidate"


def test_generated_candidates_import_to_review_table_not_canonical(tmp_path: Path) -> None:
    engine = _candidate_engine()
    path = _candidate_file(
        tmp_path,
        {
            "source_plant_slug": "bean",
            "target_plant_slug": "tomato",
            "relationship_type": "nutrient_support",
            "confidence": "low",
            "evidence_type": "generated_inference",
            "rationale": "Legume support candidate.",
            "relationship_direction": "one_way",
            "generation_rule": "legume_nitrogen_support_candidate",
            "review_status": "needs_review",
        },
    )
    with Session(engine) as session:
        _seed_plants(session)
        summary = import_candidate_jsonl(path, session)
        candidates = session.scalars(select(CompanionRelationshipCandidate)).all()
        canonical = session.scalars(select(PlantCompanionRelationship)).all()
        review_status = candidates[0].review_status

    assert summary["inserted"] == 1
    assert len(candidates) == 1
    assert review_status == "needs_review"
    assert canonical == []


def test_rejected_candidates_are_preserved_and_suppress_reimport(tmp_path: Path) -> None:
    engine = _candidate_engine()
    slug = candidate_slug_for("bean", "tomato", "nutrient_support", "generated_inference", generation_rule="legume_nitrogen_support_candidate")
    path = _candidate_file(
        tmp_path,
        {
            "source_plant_slug": "bean",
            "target_plant_slug": "tomato",
            "relationship_type": "nutrient_support",
            "confidence": "low",
            "evidence_type": "generated_inference",
            "rationale": "New generated text should not overwrite rejection.",
            "relationship_direction": "one_way",
            "generation_rule": "legume_nitrogen_support_candidate",
            "review_status": "needs_review",
        },
    )
    with Session(engine) as session:
        _seed_plants(session)
        session.add(
            CompanionRelationshipCandidate(
                candidate_slug=slug,
                source_plant_slug="bean",
                target_plant_slug="tomato",
                relationship_type="nutrient_support",
                confidence="low",
                evidence_type="generated_inference",
                rationale="Rejected by reviewer.",
                relationship_direction="one_way",
                generation_rule="legume_nitrogen_support_candidate",
                review_status="rejected",
            )
        )
        session.commit()

        summary = import_candidate_jsonl(path, session)
        candidate = session.scalar(select(CompanionRelationshipCandidate).where(CompanionRelationshipCandidate.candidate_slug == slug))
        review_status = candidate.review_status
        rationale = candidate.rationale

    assert summary["skipped_rejected"] == 1
    assert candidate is not None
    assert review_status == "rejected"
    assert rationale == "Rejected by reviewer."


def test_needs_more_research_candidates_preserve_review_state_on_reimport(tmp_path: Path) -> None:
    engine = _candidate_engine()
    slug = candidate_slug_for("bean", "tomato", "nutrient_support", "generated_inference", generation_rule="legume_nitrogen_support_candidate")
    path = _candidate_file(
        tmp_path,
        {
            "source_plant_slug": "bean",
            "target_plant_slug": "tomato",
            "relationship_type": "nutrient_support",
            "confidence": "low",
            "evidence_type": "generated_inference",
            "rationale": "Regenerated text can update non-review fields.",
            "relationship_direction": "one_way",
            "generation_rule": "legume_nitrogen_support_candidate",
            "review_status": "needs_review",
        },
    )
    with Session(engine) as session:
        _seed_plants(session)
        session.add(
            CompanionRelationshipCandidate(
                candidate_slug=slug,
                source_plant_slug="bean",
                target_plant_slug="tomato",
                relationship_type="nutrient_support",
                confidence="low",
                evidence_type="generated_inference",
                rationale="Needs more research.",
                relationship_direction="one_way",
                generation_rule="legume_nitrogen_support_candidate",
                review_status="needs_more_research",
                conflict_notes="Reviewer held this.",
            )
        )
        session.commit()

        summary = import_candidate_jsonl(path, session)
        candidate = session.scalar(select(CompanionRelationshipCandidate).where(CompanionRelationshipCandidate.candidate_slug == slug))

    assert summary["updated"] == 1
    assert candidate.review_status == "needs_more_research"
    assert candidate.conflict_notes == "Reviewer held this."
    assert candidate.rationale == "Regenerated text can update non-review fields."


def test_approved_candidate_promotes_to_canonical_relationship(tmp_path: Path) -> None:
    engine = _candidate_engine()
    path = _candidate_file(
        tmp_path,
        {
            "source_plant_slug": "bean",
            "target_plant_slug": "tomato",
            "relationship_type": "nutrient_support",
            "confidence": "low",
            "evidence_type": "generated_inference",
            "rationale": "Legume support candidate.",
            "relationship_direction": "one_way",
            "generation_rule": "legume_nitrogen_support_candidate",
            "review_status": "needs_review",
        },
    )
    with Session(engine) as session:
        _seed_plants(session)
        import_candidate_jsonl(path, session)
        candidate = session.scalar(select(CompanionRelationshipCandidate))

        relationship = promote_candidate(candidate.candidate_slug, reviewed_by="test-reviewer", reviewer_notes="Looks reasonable.", db=session)
        legacy = session.scalars(select(PlantCompanion)).all()
        relationship_type = relationship.relationship_type
        promoted_id = relationship.id
        review_status = candidate.review_status
        duplicate_id = candidate.duplicate_of_canonical_relationship_id
        canonical_id = candidate.canonical_relationship_id
        promoted = candidate.promoted_to_canonical

    assert relationship_type == "nutrient_support"
    assert legacy
    assert review_status == "approved"
    assert duplicate_id == promoted_id
    assert canonical_id == promoted_id
    assert promoted is True


def test_review_csv_export_and_import_decisions(tmp_path: Path) -> None:
    engine = _candidate_engine()
    csv_path = tmp_path / "review.csv"
    with Session(engine) as session:
        _seed_plants(session)
        session.add_all(
            [
                _candidate("bean-tomato-review", "bean", "tomato", "needs_review"),
                _candidate("tomato-bean-research", "tomato", "bean", "needs_more_research"),
                _candidate("bean-tomato-rejected", "bean", "tomato", "rejected"),
            ]
        )
        session.commit()

        summary = export_review_csv(csv_path, session)

    rows = list(csv.DictReader(csv_path.open()))
    assert summary["exported"] == 2
    assert set(rows[0].keys()) == set(REVIEW_CSV_COLUMNS)
    assert {row["candidate_slug"] for row in rows} == {"bean-tomato-review", "tomato-bean-research"}
    assert all(row["reviewer_decision"] == "" for row in rows)

    rows[0]["reviewer_decision"] = "approve"
    rows[0]["reviewer_notes"] = "Source reviewed."
    rows[1]["reviewer_decision"] = "reject"
    rows[1]["reviewer_notes"] = "Too speculative."
    _write_review_csv(csv_path, rows)

    with Session(engine) as session:
        summary = import_review_csv(csv_path, session)
        approved = session.scalar(select(CompanionRelationshipCandidate).where(CompanionRelationshipCandidate.candidate_slug == rows[0]["candidate_slug"]))
        rejected = session.scalar(select(CompanionRelationshipCandidate).where(CompanionRelationshipCandidate.candidate_slug == rows[1]["candidate_slug"]))
        canonical_count = len(session.scalars(select(PlantCompanionRelationship)).all())

    assert summary["approved"] == 1
    assert summary["rejected"] == 1
    assert approved.review_status == "approved"
    assert approved.reviewer_notes == "Source reviewed."
    assert approved.reviewed_at is not None
    assert rejected.review_status == "rejected"
    assert canonical_count == 0


def test_review_csv_edit_marks_candidate_as_edited_approved(tmp_path: Path) -> None:
    engine = _candidate_engine()
    csv_path = tmp_path / "review.csv"
    with Session(engine) as session:
        _seed_plants(session)
        session.add(_candidate("bean-tomato-edit", "bean", "tomato", "needs_review"))
        session.commit()
        export_review_csv(csv_path, session)

    rows = list(csv.DictReader(csv_path.open()))
    rows[0]["reviewer_decision"] = "edit"
    rows[0]["relationship_type"] = "spatial_compatibility"
    rows[0]["rationale"] = "Edited by reviewer."
    rows[0]["reviewer_notes"] = "Changed relationship type."
    _write_review_csv(csv_path, rows)

    with Session(engine) as session:
        summary = import_review_csv(csv_path, session)
        candidate = session.scalar(select(CompanionRelationshipCandidate).where(CompanionRelationshipCandidate.candidate_slug == "bean-tomato-edit"))

    assert summary["edited"] == 1
    assert candidate.review_status == "edited-approved"
    assert candidate.relationship_type == "spatial_compatibility"
    assert candidate.rationale == "Edited by reviewer."


def test_import_approved_candidates_promotes_only_approved_statuses() -> None:
    engine = _candidate_engine()
    with Session(engine) as session:
        _seed_plants(session)
        session.add_all(
            [
                _candidate("bean-tomato-approved", "bean", "tomato", "approved"),
                _candidate("tomato-bean-edited", "tomato", "bean", "edited-approved"),
                _candidate("bean-tomato-research", "bean", "tomato", "needs_more_research"),
                _candidate("tomato-bean-rejected", "tomato", "bean", "rejected"),
            ]
        )
        session.commit()

        first = promote_approved_candidates(session)
        second = promote_approved_candidates(session)
        candidates = session.scalars(select(CompanionRelationshipCandidate)).all()
        canonical = session.scalars(select(PlantCompanionRelationship)).all()

    promoted = [candidate for candidate in candidates if candidate.promoted_to_canonical]
    assert first["promoted"] == 2
    assert second["promoted"] == 0
    assert second["already_promoted"] == 2
    assert len(promoted) == 2
    assert len(canonical) == 2


def test_import_approved_candidates_holds_conflicts_for_more_research() -> None:
    engine = _candidate_engine()
    with Session(engine) as session:
        _seed_plants(session)
        session.add(
            PlantCompanionRelationship(
                source_plant_id=2,
                target_plant_id=1,
                relationship_type="competition",
                confidence="medium",
                evidence_type="extension_service",
                rationale="Existing risk relationship.",
                source_name="Extension",
                relationship_direction="symmetric",
            )
        )
        session.add(_candidate("bean-tomato-approved-conflict", "bean", "tomato", "approved", relationship_type="nutrient_support"))
        session.commit()

        summary = promote_approved_candidates(session)
        candidate = session.scalar(select(CompanionRelationshipCandidate).where(CompanionRelationshipCandidate.candidate_slug == "bean-tomato-approved-conflict"))
        canonical = session.scalars(select(PlantCompanionRelationship)).all()

    assert summary["held_for_conflict"] == 1
    assert summary["promoted"] == 0
    assert candidate.review_status == "needs_more_research"
    assert candidate.promoted_to_canonical is False
    assert candidate.canonical_relationship_id is None
    assert "conflicts with canonical relationship" in candidate.conflict_notes
    assert len(canonical) == 1


def _find(candidates: list[dict], source: str, target: str, relationship_type: str) -> bool:
    return any(
        candidate["source_plant_slug"] == source
        and candidate["target_plant_slug"] == target
        and candidate["relationship_type"] == relationship_type
        for candidate in candidates
    )


def _find_pair(candidates: list[dict], first: str, second: str, relationship_type: str) -> bool:
    return _find(candidates, first, second, relationship_type) or _find(candidates, second, first, relationship_type)


def _candidate_engine():
    engine = create_engine("sqlite:///:memory:", future=True)
    for table in [Plant.__table__, PlantCultivar.__table__, PlantCompanion.__table__, PlantCompanionRelationship.__table__, CompanionRelationshipCandidate.__table__]:
        table.create(engine)
    return engine


def _candidate_file(tmp_path: Path, row: dict) -> Path:
    path = tmp_path / "candidates.jsonl"
    path.write_text(json.dumps(row) + "\n")
    return path


def _seed_plants(session: Session) -> None:
    session.add_all([_plant(1, "bean", "Bean"), _plant(2, "tomato", "Tomato")])
    session.commit()


def _candidate(slug: str, source: str, target: str, status: str, *, relationship_type: str = "nutrient_support") -> CompanionRelationshipCandidate:
    return CompanionRelationshipCandidate(
        candidate_slug=slug,
        source_plant_slug=source,
        target_plant_slug=target,
        relationship_type=relationship_type,
        confidence="low",
        evidence_type="generated_inference",
        rationale="Review candidate.",
        relationship_direction="one_way",
        generation_rule="test_rule",
        review_status=status,
    )


def _write_review_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


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
