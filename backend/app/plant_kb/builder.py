from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from app.plant_kb.companion_relationships import relationship_seed_for_sqlite
from app.plant_kb.seed_data import REGION_RULES, NOW, SOURCE_VERSION, cultivar_records, data_sources, plant_records, planting_rules
from app.plant_kb.sqlite_schema import SCHEMA_SQL

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "jakegpt_plant_knowledge.sqlite"


def build_database(path: Path = DEFAULT_DB_PATH) -> dict[str, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA_SQL)
        plants = plant_records()
        cultivars = cultivar_records(plants)
        rules = planting_rules(plants)
        _insert_rows(conn, "plants", plants)
        plant_ids = {row["slug"]: row["id"] for row in conn.execute("SELECT id, slug FROM plants")}
        cultivar_rows = [{k: v for k, v in row.items() if k != "plant_slug"} | {"plant_id": plant_ids[row["plant_slug"]]} for row in cultivars]
        _insert_rows(conn, "plant_cultivars", cultivar_rows)
        cultivar_ids = {row["slug"]: row["id"] for row in conn.execute("SELECT id, slug FROM plant_cultivars")}
        companion_rows = []
        for row in relationship_seed_for_sqlite():
            companion_rows.append(
                {
                    "source_plant_id": plant_ids[row["source_plant_slug"]],
                    "target_plant_id": plant_ids[row["target_plant_slug"]],
                    "source_cultivar_id": cultivar_ids.get(row.get("source_cultivar_slug")),
                    "target_cultivar_id": cultivar_ids.get(row.get("target_cultivar_slug")),
                    "relationship_type": row["relationship_type"],
                    "confidence": row["confidence"],
                    "evidence_type": row["evidence_type"],
                    "rationale": row["rationale"],
                    "source_name": row["source_name"],
                    "source_url": row.get("source_url"),
                    "relationship_direction": row["relationship_direction"],
                    "min_distance_inches": row.get("min_distance_inches"),
                    "max_distance_inches": row.get("max_distance_inches"),
                    "source_notes": row["source_notes"],
                    "created_at": NOW,
                    "updated_at": NOW,
                }
            )
        _insert_rows(conn, "plant_companion_relationships", companion_rows)
        rule_rows = [
            {k: v for k, v in row.items() if k not in {"plant_slug", "cultivar_slug"}}
            | {"plant_id": plant_ids[row["plant_slug"]], "cultivar_id": cultivar_ids.get(row["cultivar_slug"])}
            for row in rules
        ]
        _insert_rows(conn, "planting_rules", rule_rows)
        region_rows = [
            {
                "plant_id": plant_ids[plant_slug],
                "cultivar_id": None,
                "hardiness_zone": zone,
                "region_name": region,
                "recommended_start_date": start,
                "recommended_transplant_date": transplant,
                "recommended_direct_sow_date": direct,
                "recommended_harvest_start": harvest_start,
                "recommended_harvest_end": harvest_end,
                "notes": "Starter regional rule; refine with local extension calendars.",
                "created_at": NOW,
                "updated_at": NOW,
            }
            for plant_slug, zone, region, start, transplant, direct, harvest_start, harvest_end in REGION_RULES
        ]
        _insert_rows(conn, "plant_region_rules", region_rows)
        _insert_rows(conn, "data_sources", data_sources())
        conn.execute(
            """
            INSERT INTO seed_import_runs (
                run_started_at, run_completed_at, source_version, plant_count, cultivar_count,
                companion_relationship_count, planting_rule_count, region_rule_count, status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (NOW, NOW, SOURCE_VERSION, len(plants), len(cultivars), len(companion_rows), len(rule_rows), len(region_rows), "completed", "SQLite plant KB rebuilt deterministically."),
        )
        conn.commit()
        return {
            "plants": len(plants),
            "cultivars": len(cultivars),
            "companion_relationships": len(companion_rows),
            "planting_rules": len(rule_rows),
            "region_rules": len(region_rows),
        }
    finally:
        conn.close()


def _insert_rows(conn: sqlite3.Connection, table: str, rows: list[dict]) -> None:
    if not rows:
        return
    columns = list(rows[0].keys())
    placeholders = ", ".join("?" for _ in columns)
    conn.executemany(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
        [[row.get(column) for column in columns] for row in rows],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the JakeGPT canonical SQLite plant knowledge base.")
    parser.add_argument("--path", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()
    counts = build_database(args.path)
    print(f"Built plant KB at {args.path}")
    for name, count in counts.items():
        print(f"{name}: {count}")


if __name__ == "__main__":
    main()
