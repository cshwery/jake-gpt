from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path

from app.plant_kb.builder import DEFAULT_DB_PATH
from app.plant_kb.companion_relationships import CONFIDENCE_VALUES, DIRECTIONS, EVIDENCE_TYPES, RELATIONSHIP_TYPES

SLUG_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
ENUMS = {
    "plant_category": {"vegetable", "fruit", "herb", "flower", "tree", "shrub", "cover_crop", "native", "ornamental"},
    "lifecycle": {"annual", "biennial", "perennial"},
    "sunlight_requirement": {"full_sun", "part_sun", "part_shade", "shade"},
    "water_requirement": {"low", "medium", "high"},
    "frost_tolerance": {"frost_tender", "light_frost_tolerant", "frost_hardy"},
    "maintenance_level": {"low", "moderate", "high"},
    "relationship_type": RELATIONSHIP_TYPES,
    "confidence": CONFIDENCE_VALUES,
    "evidence_type": EVIDENCE_TYPES,
    "relationship_direction": DIRECTIONS,
    "rule_type": {"direct_sow", "start_indoors", "transplant", "succession_plant", "fall_planting", "overwinter"},
    "relative_to": {"last_frost", "first_frost", "soil_temperature", "calendar_month"},
    "source_type": {"manual", "public_dataset", "extension_service", "nursery_catalog", "seed_catalog", "generated"},
}


def validate_database(path: Path = DEFAULT_DB_PATH) -> tuple[bool, list[str], dict[str, int]]:
    errors: list[str] = []
    counts: dict[str, int] = {}
    if not path.exists():
        return False, [f"Database does not exist: {path}"], counts
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        required_tables = [
            "plants",
            "plant_cultivars",
            "plant_companion_relationships",
            "planting_rules",
            "plant_region_rules",
            "data_sources",
            "seed_import_runs",
        ]
        existing = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table in required_tables:
            if table not in existing:
                errors.append(f"Missing table: {table}")
                continue
            counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        if errors:
            return False, errors, counts
        plants = list(conn.execute("SELECT * FROM plants"))
        cultivars = list(conn.execute("SELECT * FROM plant_cultivars"))
        plant_ids = {row["id"] for row in plants}
        cultivar_ids = {row["id"] for row in cultivars}
        for plant in plants:
            _require(errors, plant, ["slug", "common_name", "plant_category", "lifecycle", "sunlight_requirement", "water_requirement", "frost_tolerance", "maintenance_level"], "plants")
            _slug(errors, plant["slug"], f"plant {plant['id']}")
            _enum(errors, "plant_category", plant["plant_category"], f"plant {plant['slug']}")
            _enum(errors, "lifecycle", plant["lifecycle"], f"plant {plant['slug']}")
            _enum(errors, "sunlight_requirement", plant["sunlight_requirement"], f"plant {plant['slug']}")
            _enum(errors, "water_requirement", plant["water_requirement"], f"plant {plant['slug']}")
            _enum(errors, "frost_tolerance", plant["frost_tolerance"], f"plant {plant['slug']}")
            _enum(errors, "maintenance_level", plant["maintenance_level"], f"plant {plant['slug']}")
            _zone_range(errors, plant["min_hardiness_zone"], plant["max_hardiness_zone"], f"plant {plant['slug']}")
            _positive(errors, plant, ["typical_spacing_inches", "typical_row_spacing_inches", "typical_days_to_maturity_min", "typical_days_to_maturity_max"], f"plant {plant['slug']}")
        for cultivar in cultivars:
            _require(errors, cultivar, ["plant_id", "slug", "cultivar_name", "normalized_name"], "plant_cultivars")
            if cultivar["plant_id"] not in plant_ids:
                errors.append(f"cultivar {cultivar['slug']} references missing plant_id {cultivar['plant_id']}")
            _slug(errors, cultivar["slug"], f"cultivar {cultivar['id']}")
            _zone_range(errors, cultivar["min_hardiness_zone"], cultivar["max_hardiness_zone"], f"cultivar {cultivar['slug']}")
            _positive(errors, cultivar, ["spacing_inches_override", "row_spacing_inches_override", "days_to_maturity_min", "days_to_maturity_max"], f"cultivar {cultivar['slug']}")
        for rel in conn.execute("SELECT * FROM plant_companion_relationships"):
            if rel["source_plant_id"] not in plant_ids or rel["target_plant_id"] not in plant_ids:
                errors.append(f"companion relationship {rel['id']} has invalid plant reference")
            if rel["source_cultivar_id"] is not None and rel["source_cultivar_id"] not in cultivar_ids:
                errors.append(f"companion relationship {rel['id']} has invalid source cultivar")
            if rel["target_cultivar_id"] is not None and rel["target_cultivar_id"] not in cultivar_ids:
                errors.append(f"companion relationship {rel['id']} has invalid target cultivar")
            _enum(errors, "relationship_type", rel["relationship_type"], f"relationship {rel['id']}")
            _enum(errors, "confidence", rel["confidence"], f"relationship {rel['id']}")
            _enum(errors, "evidence_type", rel["evidence_type"], f"relationship {rel['id']}")
            _enum(errors, "relationship_direction", rel["relationship_direction"], f"relationship {rel['id']}")
            _require(errors, rel, ["rationale", "source_name", "source_notes"], "plant_companion_relationships")
            _positive(errors, rel, ["min_distance_inches", "max_distance_inches"], f"relationship {rel['id']}")
        for rule in conn.execute("SELECT * FROM planting_rules"):
            if rule["plant_id"] not in plant_ids:
                errors.append(f"planting rule {rule['id']} has invalid plant reference")
            if rule["cultivar_id"] is not None and rule["cultivar_id"] not in cultivar_ids:
                errors.append(f"planting rule {rule['id']} has invalid cultivar reference")
            _enum(errors, "rule_type", rule["rule_type"], f"planting rule {rule['id']}")
            _enum(errors, "relative_to", rule["relative_to"], f"planting rule {rule['id']}")
            _positive(errors, rule, ["min_soil_temp_f", "max_soil_temp_f"], f"planting rule {rule['id']}")
        for region_rule in conn.execute("SELECT * FROM plant_region_rules"):
            if region_rule["plant_id"] not in plant_ids:
                errors.append(f"region rule {region_rule['id']} has invalid plant reference")
            if region_rule["cultivar_id"] is not None and region_rule["cultivar_id"] not in cultivar_ids:
                errors.append(f"region rule {region_rule['id']} has invalid cultivar reference")
        for source in conn.execute("SELECT * FROM data_sources"):
            _enum(errors, "source_type", source["source_type"], f"data source {source['id']}")
    finally:
        conn.close()
    return not errors, errors, counts


def _require(errors: list[str], row: sqlite3.Row, fields: list[str], table: str) -> None:
    for field in fields:
        if row[field] is None or row[field] == "":
            errors.append(f"{table} row {row['id']} missing required field {field}")


def _slug(errors: list[str], value: str, label: str) -> None:
    if not value or not SLUG_RE.match(value):
        errors.append(f"{label} has invalid slug {value!r}")


def _enum(errors: list[str], enum_name: str, value: str, label: str) -> None:
    if value not in ENUMS[enum_name]:
        errors.append(f"{label} has invalid {enum_name}: {value!r}")


def _zone_range(errors: list[str], min_zone: int | None, max_zone: int | None, label: str) -> None:
    if min_zone is None and max_zone is None:
        return
    if min_zone is None or max_zone is None or min_zone < 1 or max_zone > 13 or min_zone > max_zone:
        errors.append(f"{label} has invalid hardiness zone range: {min_zone}-{max_zone}")


def _positive(errors: list[str], row: sqlite3.Row, fields: list[str], label: str) -> None:
    for field in fields:
        if row[field] is not None and row[field] <= 0:
            errors.append(f"{label} has non-positive {field}: {row[field]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the JakeGPT SQLite plant knowledge base.")
    parser.add_argument("--path", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    ok, errors, counts = validate_database(args.path)
    print(f"Validation report for {args.path}")
    for table, count in counts.items():
        print(f"- {table}: {count}")
    if errors:
        print("Errors:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("OK: plant knowledge base is valid")


if __name__ == "__main__":
    main()
