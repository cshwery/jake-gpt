from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Plant, PlantCompanion, PlantCompanionRelationship, PlantCultivar
from app.plant_kb.seed_data import NOW, plant_records

DEFAULT_COMPANION_JSONL = Path(__file__).resolve().parents[2] / "data" / "companion_relationships_seed.jsonl"

RELATIONSHIP_TYPES = {
    "beneficial",
    "avoid",
    "neutral",
    "guild",
    "trap_crop",
    "pollinator_support",
    "pest_deterrent",
    "nutrient_support",
    "shade_support",
    "succession",
    "spatial_compatibility",
    "disease_risk",
    "pest_risk",
    "allelopathy",
    "competition",
}
BENEFICIAL_TYPES = {
    "beneficial",
    "guild",
    "trap_crop",
    "pollinator_support",
    "pest_deterrent",
    "nutrient_support",
    "shade_support",
    "succession",
    "spatial_compatibility",
}
CONFIDENCE_VALUES = {"low", "medium", "high"}
EVIDENCE_TYPES = {
    "extension_service",
    "peer_reviewed",
    "master_gardener",
    "traditional",
    "seed_catalog",
    "generated_inference",
    "manual",
}
DIRECTIONS = {"one_way", "symmetric"}

REQUIRED_FIELDS = {
    "source_plant_slug",
    "target_plant_slug",
    "relationship_type",
    "evidence_type",
    "confidence",
    "rationale",
    "relationship_direction",
    "source_name",
    "source_notes",
}


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: list[str]
    count: int
    symmetric_count: int


def load_relationship_seed(path: Path = DEFAULT_COMPANION_JSONL) -> list[dict[str, Any]]:
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


def validate_relationship_seed(path: Path = DEFAULT_COMPANION_JSONL, plant_slugs: set[str] | None = None) -> ValidationResult:
    plant_slugs = plant_slugs or {plant["slug"] for plant in plant_records()}
    errors: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    pair_types: dict[frozenset[str], set[str]] = {}
    rows = load_relationship_seed(path)

    for row in rows:
        line = row["_line"]
        missing = sorted(field for field in REQUIRED_FIELDS if not str(row.get(field, "")).strip())
        if missing:
            errors.append(f"line {line}: missing required fields: {', '.join(missing)}")

        source = row.get("source_plant_slug")
        target = row.get("target_plant_slug")
        rel_type = row.get("relationship_type")
        confidence = row.get("confidence")
        evidence_type = row.get("evidence_type")
        direction = row.get("relationship_direction")

        if source not in plant_slugs:
            errors.append(f"line {line}: unknown source_plant_slug {source!r}")
        if target not in plant_slugs:
            errors.append(f"line {line}: unknown target_plant_slug {target!r}")
        if source == target:
            errors.append(f"line {line}: source and target plant cannot be the same")
        if rel_type not in RELATIONSHIP_TYPES:
            errors.append(f"line {line}: invalid relationship_type {rel_type!r}")
        if confidence not in CONFIDENCE_VALUES:
            errors.append(f"line {line}: invalid confidence {confidence!r}")
        if evidence_type not in EVIDENCE_TYPES:
            errors.append(f"line {line}: invalid evidence_type {evidence_type!r}")
        if direction not in DIRECTIONS:
            errors.append(f"line {line}: invalid relationship_direction {direction!r}")

        key = (str(source), str(target), str(rel_type))
        if key in seen:
            errors.append(f"line {line}: duplicate source-target-relationship_type row {key}")
        seen.add(key)

        if isinstance(row.get("min_distance_inches"), int) and isinstance(row.get("max_distance_inches"), int):
            if row["min_distance_inches"] > row["max_distance_inches"]:
                errors.append(f"line {line}: min_distance_inches cannot exceed max_distance_inches")

        if source and target and rel_type in RELATIONSHIP_TYPES:
            pair_key = frozenset((str(source), str(target)))
            pair_types.setdefault(pair_key, set()).add(str(rel_type))

    for pair, rel_types in pair_types.items():
        if "avoid" in rel_types and rel_types & BENEFICIAL_TYPES:
            errors.append(f"pair {sorted(pair)}: avoid relationship conflicts with beneficial-like relationship(s) {sorted(rel_types)}")
        if ("disease_risk" in rel_types or "pest_risk" in rel_types or "allelopathy" in rel_types or "competition" in rel_types) and rel_types & BENEFICIAL_TYPES:
            errors.append(f"pair {sorted(pair)}: risk relationship conflicts with beneficial-like relationship(s) {sorted(rel_types)}")

    symmetric_count = sum(1 for row in rows if row.get("relationship_direction") == "symmetric")
    if symmetric_count == 0 and rows:
        errors.append("no symmetric relationships present; query-both-ways behavior cannot be validated")

    return ValidationResult(ok=not errors, errors=errors, count=len(rows), symmetric_count=symmetric_count)


def relationship_seed_for_sqlite(path: Path = DEFAULT_COMPANION_JSONL) -> list[dict[str, Any]]:
    result = validate_relationship_seed(path)
    if not result.ok:
        raise ValueError("Invalid companion relationship seed:\n" + "\n".join(result.errors))
    rows = load_relationship_seed(path)
    return [{key: value for key, value in row.items() if key != "_line"} for row in rows]


def import_relationship_seed(path: Path = DEFAULT_COMPANION_JSONL, db: Session | None = None) -> dict[str, int]:
    result = validate_relationship_seed(path)
    if not result.ok:
        raise ValueError("Invalid companion relationship seed:\n" + "\n".join(result.errors))

    owns_session = db is None
    session = db or SessionLocal()
    rows = load_relationship_seed(path)
    summary = {"relationships_upserted": 0, "legacy_relationships_upserted": 0}
    try:
        queued_legacy_pairs: set[tuple[int, int]] = set()
        plants = {plant.slug: plant for plant in session.scalars(select(Plant)).all() if plant.slug}
        cultivars = {cultivar.slug: cultivar for cultivar in session.scalars(select(PlantCultivar)).all()}
        managed_source_names = {row["source_name"] for row in rows}
        session.execute(delete(PlantCompanion))
        session.execute(delete(PlantCompanionRelationship).where(PlantCompanionRelationship.source_name.in_(managed_source_names | {"JakeGPT curated starter plant knowledge"})))
        for row in rows:
            source = plants[row["source_plant_slug"]]
            target = plants[row["target_plant_slug"]]
            source_cultivar = _optional_cultivar(cultivars, row.get("source_cultivar_slug"))
            target_cultivar = _optional_cultivar(cultivars, row.get("target_cultivar_slug"))
            values = {
                "source_plant_id": source.id,
                "target_plant_id": target.id,
                "source_cultivar_id": source_cultivar.id if source_cultivar else None,
                "target_cultivar_id": target_cultivar.id if target_cultivar else None,
                "relationship_type": row["relationship_type"],
                "confidence": row["confidence"],
                "evidence_type": row["evidence_type"],
                "rationale": row["rationale"],
                "source_name": row["source_name"],
                "source_url": row.get("source_url"),
                "source_notes": row["source_notes"],
                "relationship_direction": row["relationship_direction"],
                "min_distance_inches": row.get("min_distance_inches"),
                "max_distance_inches": row.get("max_distance_inches"),
            }
            rel = session.scalar(
                select(PlantCompanionRelationship).where(
                    PlantCompanionRelationship.source_plant_id == values["source_plant_id"],
                    PlantCompanionRelationship.target_plant_id == values["target_plant_id"],
                    _nullable_eq(PlantCompanionRelationship.source_cultivar_id, values["source_cultivar_id"]),
                    _nullable_eq(PlantCompanionRelationship.target_cultivar_id, values["target_cultivar_id"]),
                    PlantCompanionRelationship.relationship_type == values["relationship_type"],
                )
            )
            if rel is None:
                session.add(PlantCompanionRelationship(**values))
            else:
                for key, value in values.items():
                    setattr(rel, key, value)
                rel.updated_at = datetime.utcnow()
            _upsert_legacy_companion(session, values, queued_legacy_pairs)
            summary["relationships_upserted"] += 1
            summary["legacy_relationships_upserted"] += 1
        session.commit()
        return summary
    except Exception:
        session.rollback()
        raise
    finally:
        if owns_session:
            session.close()


def _optional_cultivar(cultivars: dict[str, PlantCultivar], slug: str | None) -> PlantCultivar | None:
    if not slug:
        return None
    if slug not in cultivars:
        raise ValueError(f"unknown cultivar slug {slug!r}")
    return cultivars[slug]


def _nullable_eq(column: Any, value: Any) -> Any:
    return column.is_(None) if value is None else column == value


def _upsert_legacy_companion(session: Session, values: dict[str, Any], queued_pairs: set[tuple[int, int]] | None = None) -> None:
    pair = (values["source_plant_id"], values["target_plant_id"])
    if queued_pairs is not None and pair in queued_pairs:
        return
    existing = session.scalar(
        select(PlantCompanion).where(
            PlantCompanion.plant_id == pair[0],
            PlantCompanion.companion_plant_id == pair[1],
        )
    )
    if existing is None:
        if queued_pairs is not None:
            queued_pairs.add(pair)
        session.add(
            PlantCompanion(
                plant_id=pair[0],
                companion_plant_id=pair[1],
                relationship_type=values["relationship_type"],
                notes=values["rationale"],
            )
        )
    else:
        existing.relationship_type = values["relationship_type"]
        existing.notes = values["rationale"]


def validate_main() -> None:
    parser = argparse.ArgumentParser(description="Validate companion relationship JSONL seed data.")
    parser.add_argument("--path", type=Path, default=DEFAULT_COMPANION_JSONL)
    args = parser.parse_args()
    result = validate_relationship_seed(args.path)
    print(f"relationships: {result.count}")
    print(f"symmetric_relationships: {result.symmetric_count}")
    if result.ok:
        print("OK: companion relationship seed is valid")
        return
    for error in result.errors:
        print(f"ERROR: {error}")
    raise SystemExit(1)


def import_main() -> None:
    parser = argparse.ArgumentParser(description="Import companion relationship JSONL seed data into PostgreSQL.")
    parser.add_argument("--path", type=Path, default=DEFAULT_COMPANION_JSONL)
    args = parser.parse_args()
    summary = import_relationship_seed(args.path)
    for key, value in summary.items():
        print(f"{key}: {value}")
