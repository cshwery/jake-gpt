from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import CompanionRelationshipCandidate, Plant, PlantCompanion, PlantCompanionRelationship, PlantCultivar
from app.plant_kb.companion_relationships import BENEFICIAL_TYPES, CONFIDENCE_VALUES, DIRECTIONS, EVIDENCE_TYPES, RELATIONSHIP_TYPES

DEFAULT_REVIEW_CSV = Path(__file__).resolve().parents[2] / "reports" / "companion_candidate_review.csv"
RISK_TYPES = {"avoid", "disease_risk", "pest_risk", "allelopathy", "competition"}
REVIEW_STATUSES = {"needs_review", "approved", "rejected", "needs_more_research", "edited", "edited-approved"}
REVIEW_DECISIONS = {"", "approve", "reject", "needs_more_research", "edit"}
REVIEW_CSV_COLUMNS = [
    "candidate_slug",
    "source_plant_slug",
    "target_plant_slug",
    "relationship_type",
    "confidence",
    "evidence_type",
    "rationale",
    "relationship_direction",
    "min_distance_inches",
    "max_distance_inches",
    "source_name",
    "source_url",
    "source_notes",
    "generation_rule",
    "conflict_notes",
    "review_status",
    "reviewer_decision",
    "reviewer_notes",
]


@dataclass(frozen=True)
class CandidateImportSummary:
    inserted: int = 0
    updated: int = 0
    skipped_rejected: int = 0
    duplicates_of_canonical: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "inserted": self.inserted,
            "updated": self.updated,
            "skipped_rejected": self.skipped_rejected,
            "duplicates_of_canonical": self.duplicates_of_canonical,
        }


def candidate_slug_for(
    source_plant_slug: str,
    target_plant_slug: str,
    relationship_type: str,
    evidence_type: str,
    generation_rule: str | None = None,
    source_name: str | None = None,
) -> str:
    basis = [source_plant_slug, target_plant_slug, relationship_type, evidence_type, generation_rule or source_name or "unsourced"]
    return _slugify("__".join(basis))[:240]


def load_candidate_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"line {line_number}: invalid JSON: {exc.msg}") from exc
            row["_line"] = line_number
            rows.append(row)
    return rows


def normalize_candidate_row(row: dict[str, Any]) -> dict[str, Any]:
    generation_rule = row.get("generation_rule") or row.get("rule_name")
    values = {
        "candidate_slug": row.get("candidate_slug")
        or candidate_slug_for(
            row["source_plant_slug"],
            row["target_plant_slug"],
            row["relationship_type"],
            row["evidence_type"],
            generation_rule=generation_rule,
            source_name=row.get("source_name"),
        ),
        "source_plant_slug": row["source_plant_slug"],
        "target_plant_slug": row["target_plant_slug"],
        "source_cultivar_slug": row.get("source_cultivar_slug"),
        "target_cultivar_slug": row.get("target_cultivar_slug"),
        "relationship_type": row["relationship_type"],
        "confidence": row["confidence"],
        "evidence_type": row["evidence_type"],
        "rationale": row["rationale"],
        "relationship_direction": row["relationship_direction"],
        "min_distance_inches": row.get("min_distance_inches"),
        "max_distance_inches": row.get("max_distance_inches"),
        "source_name": row.get("source_name"),
        "source_url": row.get("source_url"),
        "source_notes": row.get("source_notes"),
        "generated_by": row.get("generated_by"),
        "generation_rule": generation_rule,
        "conflict_notes": row.get("conflict_notes"),
        "review_status": row.get("review_status", "needs_review"),
    }
    _validate_candidate_values(values, line=row.get("_line"))
    return values


def import_candidate_jsonl(path: Path, db: Session | None = None) -> dict[str, int]:
    owns_session = db is None
    session = db or SessionLocal()
    rows = [normalize_candidate_row(row) for row in load_candidate_jsonl(path)]
    plants = {plant.slug: plant for plant in session.scalars(select(Plant)).all() if plant.slug}
    cultivars = {cultivar.slug: cultivar for cultivar in session.scalars(select(PlantCultivar)).all()}
    summary = {"inserted": 0, "updated": 0, "skipped_rejected": 0, "duplicates_of_canonical": 0}
    try:
        for values in rows:
            _resolve_plant_and_cultivar_slugs(values, plants, cultivars)
            duplicate = _find_canonical_relationship(session, values, plants, cultivars)
            if duplicate:
                values["duplicate_of_canonical_relationship_id"] = duplicate.id
                summary["duplicates_of_canonical"] += 1
            existing = session.scalar(select(CompanionRelationshipCandidate).where(CompanionRelationshipCandidate.candidate_slug == values["candidate_slug"]))
            if existing is None:
                session.add(CompanionRelationshipCandidate(**values))
                summary["inserted"] += 1
            elif existing.review_status == "rejected":
                summary["skipped_rejected"] += 1
            elif existing.review_status in {"needs_review", "needs_more_research", "edited"}:
                preserved_review = _preserved_review_values(existing)
                for key, value in values.items():
                    setattr(existing, key, value)
                for key, value in preserved_review.items():
                    setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                summary["updated"] += 1
        session.commit()
        return summary
    except Exception:
        session.rollback()
        raise
    finally:
        if owns_session:
            session.close()


def promote_candidate(candidate_slug: str, *, reviewed_by: str | None = None, reviewer_notes: str | None = None, db: Session | None = None) -> PlantCompanionRelationship:
    owns_session = db is None
    session = db or SessionLocal()
    try:
        candidate = session.scalar(select(CompanionRelationshipCandidate).where(CompanionRelationshipCandidate.candidate_slug == candidate_slug))
        if candidate is None:
            raise ValueError(f"unknown companion relationship candidate {candidate_slug!r}")
        if candidate.review_status == "rejected":
            raise ValueError(f"rejected candidate {candidate_slug!r} cannot be promoted")

        plants = {plant.slug: plant for plant in session.scalars(select(Plant)).all() if plant.slug}
        cultivars = {cultivar.slug: cultivar for cultivar in session.scalars(select(PlantCultivar)).all()}
        values = _canonical_values(candidate, plants, cultivars)
        conflict = _find_conflicting_canonical_relationship(session, values)
        if conflict is not None:
            _mark_candidate_conflicted(candidate, conflict)
            session.commit()
            raise ValueError(f"candidate {candidate_slug!r} conflicts with canonical relationship {conflict.id}; marked needs_more_research")
        relationship = _find_canonical_relationship(session, values, plants, cultivars)
        if relationship is None:
            relationship = PlantCompanionRelationship(**values)
            session.add(relationship)
            session.flush()
        else:
            for key, value in values.items():
                setattr(relationship, key, value)
            relationship.updated_at = datetime.utcnow()
        _upsert_legacy_companion(session, values)

        candidate.review_status = "approved"
        candidate.reviewed_by = reviewed_by
        candidate.reviewer_notes = reviewer_notes
        candidate.reviewed_at = datetime.utcnow()
        candidate.duplicate_of_canonical_relationship_id = relationship.id
        candidate.canonical_relationship_id = relationship.id
        candidate.promoted_to_canonical = True
        candidate.updated_at = datetime.utcnow()
        session.commit()
        return relationship
    except Exception:
        session.rollback()
        raise
    finally:
        if owns_session:
            session.close()


def export_review_csv(path: Path = DEFAULT_REVIEW_CSV, db: Session | None = None) -> dict[str, int | str]:
    owns_session = db is None
    session = db or SessionLocal()
    try:
        candidates = session.scalars(
            select(CompanionRelationshipCandidate)
            .where(CompanionRelationshipCandidate.review_status.in_(["needs_review", "needs_more_research"]))
            .order_by(CompanionRelationshipCandidate.source_plant_slug, CompanionRelationshipCandidate.target_plant_slug, CompanionRelationshipCandidate.relationship_type)
        ).all()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=REVIEW_CSV_COLUMNS)
            writer.writeheader()
            for candidate in candidates:
                writer.writerow(_candidate_to_review_csv_row(candidate))
        return {"exported": len(candidates), "path": str(path)}
    finally:
        if owns_session:
            session.close()


def import_review_csv(path: Path = DEFAULT_REVIEW_CSV, db: Session | None = None) -> dict[str, int]:
    owns_session = db is None
    session = db or SessionLocal()
    summary = {"approved": 0, "rejected": 0, "needs_more_research": 0, "edited": 0, "skipped": 0}
    try:
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            missing = [column for column in REVIEW_CSV_COLUMNS if column not in (reader.fieldnames or [])]
            if missing:
                raise ValueError(f"review CSV missing required columns: {', '.join(missing)}")
            for line_number, row in enumerate(reader, start=2):
                decision = (row.get("reviewer_decision") or "").strip()
                if decision not in REVIEW_DECISIONS:
                    raise ValueError(f"line {line_number}: invalid reviewer_decision {decision!r}")
                if not decision:
                    summary["skipped"] += 1
                    continue
                candidate = session.scalar(select(CompanionRelationshipCandidate).where(CompanionRelationshipCandidate.candidate_slug == row["candidate_slug"]))
                if candidate is None:
                    raise ValueError(f"line {line_number}: unknown candidate_slug {row['candidate_slug']!r}")
                if decision == "approve":
                    candidate.review_status = "approved"
                    candidate.reviewed_at = datetime.utcnow()
                    summary["approved"] += 1
                elif decision == "reject":
                    candidate.review_status = "rejected"
                    candidate.reviewed_at = datetime.utcnow()
                    summary["rejected"] += 1
                elif decision == "needs_more_research":
                    candidate.review_status = "needs_more_research"
                    summary["needs_more_research"] += 1
                elif decision == "edit":
                    _apply_editable_csv_fields(candidate, row, line_number=line_number)
                    candidate.review_status = "edited-approved"
                    summary["edited"] += 1
                candidate.reviewer_notes = row.get("reviewer_notes") or None
                candidate.updated_at = datetime.utcnow()
        session.commit()
        return summary
    except Exception:
        session.rollback()
        raise
    finally:
        if owns_session:
            session.close()


def promote_approved_candidates(db: Session | None = None) -> dict[str, int]:
    owns_session = db is None
    session = db or SessionLocal()
    summary = {"promoted": 0, "already_promoted": 0, "held_for_conflict": 0, "skipped": 0}
    try:
        candidates = session.scalars(
            select(CompanionRelationshipCandidate)
            .where(CompanionRelationshipCandidate.review_status.in_(["approved", "edited-approved"]))
            .order_by(CompanionRelationshipCandidate.candidate_slug)
        ).all()
        plants = {plant.slug: plant for plant in session.scalars(select(Plant)).all() if plant.slug}
        cultivars = {cultivar.slug: cultivar for cultivar in session.scalars(select(PlantCultivar)).all()}
        for candidate in candidates:
            if candidate.promoted_to_canonical and candidate.canonical_relationship_id:
                summary["already_promoted"] += 1
                continue
            values = _canonical_values(candidate, plants, cultivars)
            conflict = _find_conflicting_canonical_relationship(session, values)
            if conflict is not None:
                _mark_candidate_conflicted(candidate, conflict)
                summary["held_for_conflict"] += 1
                continue
            relationship = _find_canonical_relationship(session, values, plants, cultivars)
            if relationship is None:
                relationship = PlantCompanionRelationship(**values)
                session.add(relationship)
                session.flush()
            else:
                for key, value in values.items():
                    setattr(relationship, key, value)
                relationship.updated_at = datetime.utcnow()
            _upsert_legacy_companion(session, values)
            candidate.canonical_relationship_id = relationship.id
            candidate.duplicate_of_canonical_relationship_id = relationship.id
            candidate.promoted_to_canonical = True
            candidate.updated_at = datetime.utcnow()
            summary["promoted"] += 1
        session.commit()
        return summary
    except Exception:
        session.rollback()
        raise
    finally:
        if owns_session:
            session.close()


def import_main() -> None:
    from app.plant_kb.generate_companion_candidates import DEFAULT_CANDIDATE_JSONL

    parser = argparse.ArgumentParser(description="Import generated companion relationship candidates for human review.")
    parser.add_argument("--path", type=Path, default=DEFAULT_CANDIDATE_JSONL)
    args = parser.parse_args()
    summary = import_candidate_jsonl(args.path)
    for key, value in summary.items():
        print(f"{key}: {value}")


def export_review_csv_main() -> None:
    parser = argparse.ArgumentParser(description="Export reviewable companion relationship candidates to CSV.")
    parser.add_argument("--path", type=Path, default=DEFAULT_REVIEW_CSV)
    args = parser.parse_args()
    summary = export_review_csv(args.path)
    for key, value in summary.items():
        print(f"{key}: {value}")


def import_review_csv_main() -> None:
    parser = argparse.ArgumentParser(description="Import companion relationship candidate reviewer decisions from CSV.")
    parser.add_argument("--path", type=Path, default=DEFAULT_REVIEW_CSV)
    args = parser.parse_args()
    summary = import_review_csv(args.path)
    for key, value in summary.items():
        print(f"{key}: {value}")


def promote_approved_main() -> None:
    parser = argparse.ArgumentParser(description="Promote approved companion relationship candidates into canonical relationships.")
    parser.parse_args()
    summary = promote_approved_candidates()
    for key, value in summary.items():
        print(f"{key}: {value}")


def promote_main() -> None:
    parser = argparse.ArgumentParser(description="Promote an approved companion relationship candidate into canonical relationships.")
    parser.add_argument("candidate_slug")
    parser.add_argument("--reviewed-by", default=None)
    parser.add_argument("--reviewer-notes", default=None)
    args = parser.parse_args()
    relationship = promote_candidate(args.candidate_slug, reviewed_by=args.reviewed_by, reviewer_notes=args.reviewer_notes)
    print(f"promoted_relationship_id: {relationship.id}")


def _validate_candidate_values(values: dict[str, Any], *, line: int | None = None) -> None:
    prefix = f"line {line}: " if line else ""
    required = ["candidate_slug", "source_plant_slug", "target_plant_slug", "relationship_type", "confidence", "evidence_type", "rationale", "relationship_direction", "review_status"]
    missing = [field for field in required if not str(values.get(field) or "").strip()]
    if missing:
        raise ValueError(f"{prefix}missing required candidate fields: {', '.join(missing)}")
    if values["relationship_type"] not in RELATIONSHIP_TYPES:
        raise ValueError(f"{prefix}invalid relationship_type {values['relationship_type']!r}")
    if values["confidence"] not in CONFIDENCE_VALUES:
        raise ValueError(f"{prefix}invalid confidence {values['confidence']!r}")
    if values["evidence_type"] not in EVIDENCE_TYPES:
        raise ValueError(f"{prefix}invalid evidence_type {values['evidence_type']!r}")
    if values["relationship_direction"] not in DIRECTIONS:
        raise ValueError(f"{prefix}invalid relationship_direction {values['relationship_direction']!r}")
    if values["review_status"] not in REVIEW_STATUSES:
        raise ValueError(f"{prefix}invalid review_status {values['review_status']!r}")


def _preserved_review_values(candidate: CompanionRelationshipCandidate) -> dict[str, Any]:
    if candidate.review_status == "needs_review":
        return {}
    return {
        "review_status": candidate.review_status,
        "reviewer_notes": candidate.reviewer_notes,
        "reviewed_by": candidate.reviewed_by,
        "reviewed_at": candidate.reviewed_at,
        "conflict_notes": candidate.conflict_notes,
        "duplicate_of_canonical_relationship_id": candidate.duplicate_of_canonical_relationship_id,
        "canonical_relationship_id": candidate.canonical_relationship_id,
        "promoted_to_canonical": candidate.promoted_to_canonical,
    }


def _candidate_to_review_csv_row(candidate: CompanionRelationshipCandidate) -> dict[str, Any]:
    return {
        "candidate_slug": candidate.candidate_slug,
        "source_plant_slug": candidate.source_plant_slug,
        "target_plant_slug": candidate.target_plant_slug,
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
        "generation_rule": candidate.generation_rule,
        "conflict_notes": candidate.conflict_notes,
        "review_status": candidate.review_status,
        "reviewer_decision": "",
        "reviewer_notes": candidate.reviewer_notes,
    }


def _apply_editable_csv_fields(candidate: CompanionRelationshipCandidate, row: dict[str, str], *, line_number: int) -> None:
    values = {
        "candidate_slug": row["candidate_slug"],
        "source_plant_slug": row["source_plant_slug"],
        "target_plant_slug": row["target_plant_slug"],
        "relationship_type": row["relationship_type"],
        "confidence": row["confidence"],
        "evidence_type": row["evidence_type"],
        "rationale": row["rationale"],
        "relationship_direction": row["relationship_direction"],
        "min_distance_inches": _optional_int(row.get("min_distance_inches"), line_number=line_number, field="min_distance_inches"),
        "max_distance_inches": _optional_int(row.get("max_distance_inches"), line_number=line_number, field="max_distance_inches"),
        "source_name": row.get("source_name") or None,
        "source_url": row.get("source_url") or None,
        "source_notes": row.get("source_notes") or None,
        "generation_rule": row.get("generation_rule") or None,
        "conflict_notes": row.get("conflict_notes") or None,
        "review_status": "edited-approved",
    }
    _validate_candidate_values(values, line=line_number)
    for field in [
        "source_plant_slug",
        "target_plant_slug",
        "relationship_type",
        "confidence",
        "evidence_type",
        "rationale",
        "relationship_direction",
        "min_distance_inches",
        "max_distance_inches",
        "source_name",
        "source_url",
        "source_notes",
        "generation_rule",
        "conflict_notes",
    ]:
        setattr(candidate, field, values[field])


def _optional_int(value: str | None, *, line_number: int, field: str) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"line {line_number}: {field} must be an integer") from exc


def _resolve_plant_and_cultivar_slugs(values: dict[str, Any], plants: dict[str, Plant], cultivars: dict[str, PlantCultivar]) -> None:
    for field in ("source_plant_slug", "target_plant_slug"):
        if values[field] not in plants:
            raise ValueError(f"unknown {field} {values[field]!r}")
    for field in ("source_cultivar_slug", "target_cultivar_slug"):
        if values.get(field) and values[field] not in cultivars:
            raise ValueError(f"unknown {field} {values[field]!r}")


def _canonical_values(candidate: CompanionRelationshipCandidate, plants: dict[str, Plant], cultivars: dict[str, PlantCultivar]) -> dict[str, Any]:
    values = {
        "source_plant_slug": candidate.source_plant_slug,
        "target_plant_slug": candidate.target_plant_slug,
        "source_cultivar_slug": candidate.source_cultivar_slug,
        "target_cultivar_slug": candidate.target_cultivar_slug,
    }
    _resolve_plant_and_cultivar_slugs(values, plants, cultivars)
    return {
        "source_plant_id": plants[candidate.source_plant_slug].id,
        "target_plant_id": plants[candidate.target_plant_slug].id,
        "source_cultivar_id": cultivars[candidate.source_cultivar_slug].id if candidate.source_cultivar_slug else None,
        "target_cultivar_id": cultivars[candidate.target_cultivar_slug].id if candidate.target_cultivar_slug else None,
        "relationship_type": candidate.relationship_type,
        "confidence": candidate.confidence,
        "evidence_type": candidate.evidence_type,
        "rationale": candidate.rationale,
        "source_name": candidate.source_name or "JakeGPT human-reviewed candidate",
        "source_url": candidate.source_url,
        "source_notes": candidate.source_notes or candidate.generation_rule or "Promoted from reviewed companion relationship candidate.",
        "relationship_direction": candidate.relationship_direction,
        "min_distance_inches": candidate.min_distance_inches,
        "max_distance_inches": candidate.max_distance_inches,
    }


def _find_canonical_relationship(session: Session, values: dict[str, Any], plants: dict[str, Plant], cultivars: dict[str, PlantCultivar]) -> PlantCompanionRelationship | None:
    canonical = values if "source_plant_id" in values else _canonical_values_from_slugs(values, plants, cultivars)
    return session.scalar(
        select(PlantCompanionRelationship).where(
            PlantCompanionRelationship.source_plant_id == canonical["source_plant_id"],
            PlantCompanionRelationship.target_plant_id == canonical["target_plant_id"],
            _nullable_eq(PlantCompanionRelationship.source_cultivar_id, canonical["source_cultivar_id"]),
            _nullable_eq(PlantCompanionRelationship.target_cultivar_id, canonical["target_cultivar_id"]),
            PlantCompanionRelationship.relationship_type == canonical["relationship_type"],
        )
    )


def _find_conflicting_canonical_relationship(session: Session, values: dict[str, Any]) -> PlantCompanionRelationship | None:
    candidate_type = values["relationship_type"]
    if candidate_type not in BENEFICIAL_TYPES and candidate_type not in RISK_TYPES:
        return None
    pair_relationships = session.scalars(
        select(PlantCompanionRelationship).where(
            (
                (PlantCompanionRelationship.source_plant_id == values["source_plant_id"])
                & (PlantCompanionRelationship.target_plant_id == values["target_plant_id"])
            )
            | (
                (PlantCompanionRelationship.relationship_direction == "symmetric")
                & (PlantCompanionRelationship.source_plant_id == values["target_plant_id"])
                & (PlantCompanionRelationship.target_plant_id == values["source_plant_id"])
            )
        )
    ).all()
    for relationship in pair_relationships:
        if relationship.relationship_type == candidate_type:
            continue
        if candidate_type in BENEFICIAL_TYPES and relationship.relationship_type in RISK_TYPES:
            return relationship
        if candidate_type in RISK_TYPES and relationship.relationship_type in BENEFICIAL_TYPES:
            return relationship
    return None


def _mark_candidate_conflicted(candidate: CompanionRelationshipCandidate, conflict: PlantCompanionRelationship) -> None:
    candidate.review_status = "needs_more_research"
    candidate.promoted_to_canonical = False
    candidate.canonical_relationship_id = None
    candidate.duplicate_of_canonical_relationship_id = conflict.id
    candidate.conflict_notes = (
        f"Promotion held because this candidate conflicts with canonical relationship {conflict.id} "
        f"({conflict.relationship_type}). Review source strength before promoting."
    )
    candidate.updated_at = datetime.utcnow()


def _canonical_values_from_slugs(values: dict[str, Any], plants: dict[str, Plant], cultivars: dict[str, PlantCultivar]) -> dict[str, Any]:
    return {
        "source_plant_id": plants[values["source_plant_slug"]].id,
        "target_plant_id": plants[values["target_plant_slug"]].id,
        "source_cultivar_id": cultivars[values["source_cultivar_slug"]].id if values.get("source_cultivar_slug") else None,
        "target_cultivar_id": cultivars[values["target_cultivar_slug"]].id if values.get("target_cultivar_slug") else None,
        "relationship_type": values["relationship_type"],
    }


def _nullable_eq(column: Any, value: Any) -> Any:
    return column.is_(None) if value is None else column == value


def _upsert_legacy_companion(session: Session, values: dict[str, Any]) -> None:
    existing = session.scalar(
        select(PlantCompanion).where(
            PlantCompanion.plant_id == values["source_plant_id"],
            PlantCompanion.companion_plant_id == values["target_plant_id"],
        )
    )
    if existing is None:
        session.add(
            PlantCompanion(
                plant_id=values["source_plant_id"],
                companion_plant_id=values["target_plant_id"],
                relationship_type=values["relationship_type"],
                notes=values["rationale"],
            )
        )
    else:
        existing.relationship_type = values["relationship_type"]
        existing.notes = values["rationale"]


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return re.sub(r"-+", "-", normalized)
