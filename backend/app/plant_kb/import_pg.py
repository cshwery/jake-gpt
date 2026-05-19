from __future__ import annotations

import argparse
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import DataSource, Plant, PlantCompanion, PlantCompanionRelationship, PlantCultivar, PlantRegionRule, PlantingRule
from app.plant_kb.builder import DEFAULT_DB_PATH


def import_from_sqlite(path: Path = DEFAULT_DB_PATH, db: Session | None = None) -> dict[str, int]:
    owns_session = db is None
    session = db or SessionLocal()
    sqlite = sqlite3.connect(path)
    sqlite.row_factory = sqlite3.Row
    summary = {
        "plants_inserted": 0,
        "plants_updated": 0,
        "cultivars_inserted": 0,
        "cultivars_updated": 0,
        "companion_relationships_upserted": 0,
        "planting_rules_upserted": 0,
        "region_rules_upserted": 0,
        "data_sources_upserted": 0,
    }
    try:
        queued_legacy_pairs: set[tuple[int, int]] = set()
        plants_by_sqlite_id: dict[int, Plant] = {}
        for row in sqlite.execute("SELECT * FROM plants ORDER BY id"):
            values = _plant_values(row)
            plant = session.scalar(select(Plant).where(Plant.slug == row["slug"]))
            if plant is None:
                plant = Plant(**values)
                session.add(plant)
                summary["plants_inserted"] += 1
            else:
                for key, value in values.items():
                    setattr(plant, key, value)
                summary["plants_updated"] += 1
            session.flush()
            plants_by_sqlite_id[row["id"]] = plant
        cultivars_by_sqlite_id: dict[int, PlantCultivar] = {}
        for row in sqlite.execute("SELECT * FROM plant_cultivars ORDER BY id"):
            values = _row_values(row, exclude={"id", "plant_id"})
            values["plant_id"] = plants_by_sqlite_id[row["plant_id"]].id
            cultivar = session.scalar(select(PlantCultivar).where(PlantCultivar.slug == row["slug"]))
            if cultivar is None:
                cultivar = PlantCultivar(**values)
                session.add(cultivar)
                summary["cultivars_inserted"] += 1
            else:
                for key, value in values.items():
                    setattr(cultivar, key, value)
                summary["cultivars_updated"] += 1
            session.flush()
            cultivars_by_sqlite_id[row["id"]] = cultivar
        for row in sqlite.execute("SELECT * FROM plant_companion_relationships ORDER BY id"):
            values = _row_values(row, exclude={"id", "source_plant_id", "target_plant_id", "source_cultivar_id", "target_cultivar_id"})
            values.update(
                {
                    "source_plant_id": plants_by_sqlite_id[row["source_plant_id"]].id,
                    "target_plant_id": plants_by_sqlite_id[row["target_plant_id"]].id,
                    "source_cultivar_id": _mapped_id(cultivars_by_sqlite_id, row["source_cultivar_id"]),
                    "target_cultivar_id": _mapped_id(cultivars_by_sqlite_id, row["target_cultivar_id"]),
                }
            )
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
            _upsert_legacy_companion(session, values, queued_legacy_pairs)
            summary["companion_relationships_upserted"] += 1
        for row in sqlite.execute("SELECT * FROM planting_rules ORDER BY id"):
            values = _row_values(row, exclude={"id", "plant_id", "cultivar_id"})
            values.update({"plant_id": plants_by_sqlite_id[row["plant_id"]].id, "cultivar_id": _mapped_id(cultivars_by_sqlite_id, row["cultivar_id"])})
            rule = session.scalar(
                select(PlantingRule).where(
                    PlantingRule.plant_id == values["plant_id"],
                    _nullable_eq(PlantingRule.cultivar_id, values["cultivar_id"]),
                    PlantingRule.rule_type == values["rule_type"],
                    PlantingRule.relative_to == values["relative_to"],
                    _nullable_eq(PlantingRule.offset_days_min, values["offset_days_min"]),
                    _nullable_eq(PlantingRule.offset_days_max, values["offset_days_max"]),
                    _nullable_eq(PlantingRule.min_soil_temp_f, values["min_soil_temp_f"]),
                )
            )
            if rule is None:
                session.add(PlantingRule(**values))
            else:
                for key, value in values.items():
                    setattr(rule, key, value)
            summary["planting_rules_upserted"] += 1
        for row in sqlite.execute("SELECT * FROM plant_region_rules ORDER BY id"):
            values = _row_values(row, exclude={"id", "plant_id", "cultivar_id"}, date_fields={"recommended_start_date", "recommended_transplant_date", "recommended_direct_sow_date", "recommended_harvest_start", "recommended_harvest_end"})
            values.update({"plant_id": plants_by_sqlite_id[row["plant_id"]].id, "cultivar_id": _mapped_id(cultivars_by_sqlite_id, row["cultivar_id"])})
            region = session.scalar(
                select(PlantRegionRule).where(
                    PlantRegionRule.plant_id == values["plant_id"],
                    _nullable_eq(PlantRegionRule.cultivar_id, values["cultivar_id"]),
                    _nullable_eq(PlantRegionRule.hardiness_zone, values["hardiness_zone"]),
                    _nullable_eq(PlantRegionRule.region_name, values["region_name"]),
                )
            )
            if region is None:
                session.add(PlantRegionRule(**values))
            else:
                for key, value in values.items():
                    setattr(region, key, value)
            summary["region_rules_upserted"] += 1
        for row in sqlite.execute("SELECT * FROM data_sources ORDER BY id"):
            values = _row_values(row, exclude={"id"})
            source = session.scalar(select(DataSource).where(DataSource.source_name == row["source_name"]))
            if source is None:
                session.add(DataSource(**values))
            else:
                for key, value in values.items():
                    setattr(source, key, value)
            summary["data_sources_upserted"] += 1
        session.commit()
        return summary
    except Exception:
        session.rollback()
        raise
    finally:
        sqlite.close()
        if owns_session:
            session.close()


def _plant_values(row: sqlite3.Row) -> dict[str, Any]:
    values = _row_values(row, exclude={"id"})
    category = row["plant_category"]
    values.update(
        {
            "plant_type": category,
            "flower": bool(row["ornamental"] or row["pollinator_value_score"] >= 7),
            "tree": bool(row["is_tree"]),
            "perennial": row["lifecycle"] == "perennial",
            "min_zone": row["min_hardiness_zone"] or 1,
            "max_zone": row["max_hardiness_zone"] or 13,
            "spacing_inches": row["typical_spacing_inches"] or 12,
            "row_spacing_inches": row["typical_row_spacing_inches"] or 12,
            "days_to_maturity": row["typical_days_to_maturity_max"],
            "planting_notes": row["notes"] or row["general_description"] or "",
        }
    )
    return values


def _row_values(row: sqlite3.Row, *, exclude: set[str], date_fields: set[str] | None = None) -> dict[str, Any]:
    date_fields = date_fields or set()
    values = {}
    for key in row.keys():
        if key in exclude:
            continue
        value = row[key]
        if key in {"created_at", "updated_at", "retrieved_at"} and value:
            value = datetime.fromisoformat(value)
        elif key in date_fields and value:
            value = date.fromisoformat(value)
        values[key] = value
    return values


def _mapped_id(mapping: dict[int, Any], sqlite_id: int | None) -> int | None:
    if sqlite_id is None:
        return None
    return mapping[sqlite_id].id


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
    notes = values["rationale"]
    if existing is None:
        if queued_pairs is not None:
            queued_pairs.add(pair)
        session.add(
            PlantCompanion(
                plant_id=pair[0],
                companion_plant_id=pair[1],
                relationship_type=values["relationship_type"],
                notes=notes,
            )
        )
    else:
        existing.relationship_type = values["relationship_type"]
        existing.notes = notes


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the SQLite plant KB into PostgreSQL.")
    parser.add_argument("--path", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    summary = import_from_sqlite(args.path)
    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
