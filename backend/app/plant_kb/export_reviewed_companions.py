from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import CompanionRelationshipCandidate, Plant, PlantCompanionRelationship, PlantCultivar
from app.plant_kb.companion_relationships import DEFAULT_COMPANION_JSONL

DEFAULT_REVIEWED_CANDIDATES_JSONL = Path(__file__).resolve().parents[2] / "data" / "companion_relationship_candidates_reviewed.jsonl"


def export_reviewed_companion_data(
    *,
    relationship_path: Path = DEFAULT_COMPANION_JSONL,
    candidate_path: Path = DEFAULT_REVIEWED_CANDIDATES_JSONL,
    db: Session | None = None,
) -> dict[str, int]:
    owns_session = db is None
    session = db or SessionLocal()
    try:
        relationship_rows = _canonical_rows(session)
        candidate_rows = _candidate_rows(session)
        _write_jsonl(relationship_path, relationship_rows)
        _write_jsonl(candidate_path, candidate_rows)
        return {
            "canonical_relationships_exported": len(relationship_rows),
            "candidate_review_rows_exported": len(candidate_rows),
        }
    finally:
        if owns_session:
            session.close()


def _canonical_rows(session: Session) -> list[dict[str, Any]]:
    plants_by_id = {plant.id: plant for plant in session.scalars(select(Plant)).all()}
    cultivars_by_id = {cultivar.id: cultivar for cultivar in session.scalars(select(PlantCultivar)).all()}
    rows: list[dict[str, Any]] = []
    for rel in session.scalars(select(PlantCompanionRelationship).order_by(PlantCompanionRelationship.id)).all():
        source = plants_by_id.get(rel.source_plant_id)
        target = plants_by_id.get(rel.target_plant_id)
        if source is None or target is None or not source.slug or not target.slug:
            continue
        row = {
            "source_plant_slug": source.slug,
            "target_plant_slug": target.slug,
            "relationship_type": rel.relationship_type,
            "confidence": rel.confidence,
            "evidence_type": rel.evidence_type,
            "rationale": rel.rationale,
            "source_name": rel.source_name,
            "source_url": rel.source_url,
            "source_notes": rel.source_notes or "Exported from reviewed JakeGPT companion relationship workflow.",
            "relationship_direction": rel.relationship_direction,
            "min_distance_inches": rel.min_distance_inches,
            "max_distance_inches": rel.max_distance_inches,
        }
        if rel.source_cultivar_id:
            row["source_cultivar_slug"] = cultivars_by_id[rel.source_cultivar_id].slug
        if rel.target_cultivar_id:
            row["target_cultivar_slug"] = cultivars_by_id[rel.target_cultivar_id].slug
        rows.append(row)
    return sorted(rows, key=lambda row: (row["source_plant_slug"], row["target_plant_slug"], row["relationship_type"], row.get("source_cultivar_slug") or "", row.get("target_cultivar_slug") or ""))


def _candidate_rows(session: Session) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in session.scalars(select(CompanionRelationshipCandidate).order_by(CompanionRelationshipCandidate.candidate_slug)).all():
        rows.append(
            {
                "candidate_slug": candidate.candidate_slug,
                "source_plant_slug": candidate.source_plant_slug,
                "target_plant_slug": candidate.target_plant_slug,
                "source_cultivar_slug": candidate.source_cultivar_slug,
                "target_cultivar_slug": candidate.target_cultivar_slug,
                "relationship_type": candidate.relationship_type,
                "confidence": candidate.confidence,
                "evidence_type": candidate.evidence_type,
                "rationale": candidate.rationale,
                "relationship_direction": candidate.relationship_direction,
                "min_distance_inches": candidate.min_distance_inches,
                "max_distance_inches": candidate.max_distance_inches,
                "source_name": candidate.source_name,
                "source_url": candidate.source_url,
                "source_notes": candidate.source_notes,
                "generated_by": candidate.generated_by,
                "generation_rule": candidate.generation_rule,
                "duplicate_of_canonical_relationship_id": candidate.duplicate_of_canonical_relationship_id,
                "conflict_notes": candidate.conflict_notes,
                "review_status": candidate.review_status,
                "reviewer_notes": candidate.reviewer_notes,
                "reviewed_by": candidate.reviewed_by,
                "reviewed_at": candidate.reviewed_at.isoformat() if candidate.reviewed_at else None,
                "promoted_to_canonical": candidate.promoted_to_canonical,
                "canonical_relationship_id": candidate.canonical_relationship_id,
            }
        )
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export reviewed companion relationship state from PostgreSQL to durable JSONL seed files.")
    parser.add_argument("--relationship-path", type=Path, default=DEFAULT_COMPANION_JSONL)
    parser.add_argument("--candidate-path", type=Path, default=DEFAULT_REVIEWED_CANDIDATES_JSONL)
    args = parser.parse_args()
    summary = export_reviewed_companion_data(relationship_path=args.relationship_path, candidate_path=args.candidate_path)
    for key, value in summary.items():
        print(f"{key}: {value}")
    print(f"relationship_path: {args.relationship_path}")
    print(f"candidate_path: {args.candidate_path}")


if __name__ == "__main__":
    main()
