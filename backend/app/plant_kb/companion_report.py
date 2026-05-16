from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import CompanionRelationshipCandidate, Plant, PlantCompanionRelationship
from app.plant_kb.companion_relationships import BENEFICIAL_TYPES, DEFAULT_COMPANION_JSONL, load_relationship_seed
from app.plant_kb.generate_companion_candidates import DEFAULT_CANDIDATE_JSONL, NIGHTSHADES
from app.plant_kb.seed_data import plant_records

DEFAULT_REPORT_PATH = Path(__file__).resolve().parents[2] / "reports" / "companion_relationship_report.md"
DEFAULT_CANDIDATE_REPORT_PATH = Path(__file__).resolve().parents[2] / "reports" / "companion_candidate_review_report.md"
RISK_TYPES = {"avoid", "disease_risk", "pest_risk", "allelopathy", "competition"}
HIGH_PRIORITY_COMMON_PLANTS = {
    "tomato",
    "pepper",
    "potato",
    "cucumber",
    "summer_squash",
    "winter_squash",
    "squash",
    "bean",
    "beans",
    "pea",
    "peas",
    "corn",
    "lettuce",
    "cabbage",
    "basil",
    "marigold",
    "onion",
    "carrot",
    "apple",
    "blueberry",
    "strawberry",
}


def build_report(
    relationship_path: Path = DEFAULT_COMPANION_JSONL,
    candidate_path: Path = DEFAULT_CANDIDATE_JSONL,
    report_path: Path = DEFAULT_REPORT_PATH,
    db: Session | None = None,
) -> str:
    if db is None:
        relationships = [{key: value for key, value in row.items() if key != "_line"} for row in load_relationship_seed(relationship_path)]
    else:
        relationships = _canonical_rows_from_db(db)
    plants = {plant["slug"]: plant for plant in plant_records()}

    lines = _canonical_markdown(relationships, plants)
    content = "\n".join(lines) + "\n"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(content)
    return content


def build_candidate_report(report_path: Path = DEFAULT_CANDIDATE_REPORT_PATH, db: Session | None = None) -> str:
    owns_session = db is None
    session = db or SessionLocal()
    try:
        candidates = _candidate_rows_from_db(session)
        canonical = _canonical_rows_from_db(session)
        plants = {plant["slug"]: plant for plant in plant_records()}
        lines = _candidate_markdown(candidates, canonical, plants)
        content = "\n".join(lines) + "\n"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(content)
        return content
    finally:
        if owns_session:
            session.close()


def build_reports(
    canonical_report_path: Path = DEFAULT_REPORT_PATH,
    candidate_report_path: Path = DEFAULT_CANDIDATE_REPORT_PATH,
    db: Session | None = None,
) -> dict[str, str]:
    owns_session = db is None
    session = db or SessionLocal()
    try:
        canonical = build_report(report_path=canonical_report_path, db=session)
        candidates = build_candidate_report(report_path=candidate_report_path, db=session)
        return {"canonical": canonical, "candidates": candidates}
    finally:
        if owns_session:
            session.close()


def _canonical_markdown(relationships: list[dict[str, Any]], plants: dict[str, dict]) -> list[str]:
    by_type = Counter(row["relationship_type"] for row in relationships)
    by_confidence = Counter(row["confidence"] for row in relationships)
    by_evidence = Counter(row["evidence_type"] for row in relationships)
    most_beneficial = _plant_counts(relationships, BENEFICIAL_TYPES, symmetric=True).most_common(10)
    most_avoid = _plant_counts(relationships, RISK_TYPES, symmetric=True).most_common(10)
    missing_rationale = [row for row in relationships if _blank(row.get("rationale"))]
    missing_source = [row for row in relationships if _blank(row.get("source_name")) or _blank(row.get("source_notes"))]
    conflicts = _conflicts(relationships)
    same_family = _same_family_risks(relationships)

    lines = [
        "# Canonical Companion Relationship Report",
        "",
        "## 1. Summary",
        "",
        f"- Total canonical relationships: {len(relationships)}",
        "",
        "### Count by relationship_type",
        *_counter_lines(by_type),
        "",
        "### Count by confidence",
        *_counter_lines(by_confidence),
        "",
        "### Count by evidence_type",
        *_counter_lines(by_evidence),
        "",
        "### Plants with the most beneficial relationships",
        *_rank_lines(most_beneficial, plants),
        "",
        "### Plants with the most avoid/risk relationships",
        *_rank_lines(most_avoid, plants),
        "",
        "## 2. High-confidence relationships",
        *_relationship_lines([row for row in relationships if row["confidence"] == "high"], plants, limit=25),
        "",
        "## 3. Medium-confidence relationships",
        *_relationship_lines([row for row in relationships if row["confidence"] == "medium"], plants, limit=35),
        "",
        "## 4. Low-confidence/generated relationships",
        *_relationship_lines([row for row in relationships if row["confidence"] == "low" or row["evidence_type"] == "generated_inference"], plants, limit=35),
        "",
        "## 5. Avoid relationships",
        *_relationship_lines([row for row in relationships if row["relationship_type"] in RISK_TYPES], plants, limit=50),
        "",
        "## 6. Conflicts needing review",
        *(_relationship_lines(conflicts, plants, limit=50) if conflicts else ["- None found."]),
        "",
        "### Same-family disease/pest risk relationships",
        *(_relationship_lines(same_family, plants, limit=50) if same_family else ["- None found."]),
        "",
        "## 7. Missing data",
        "",
        f"- Relationships missing rationale: {len(missing_rationale)}",
        *_relationship_lines(missing_rationale, plants, limit=20),
        "",
        f"- Relationships missing source information: {len(missing_source)}",
        *_relationship_lines(missing_source, plants, limit=20),
        "",
        "## 8. Suggested next research targets",
        *_canonical_research_targets(relationships, plants),
    ]
    return lines


def _candidate_markdown(candidates: list[dict[str, Any]], canonical: list[dict[str, Any]], plants: dict[str, dict]) -> list[str]:
    by_status = Counter(row["review_status"] for row in candidates)
    by_type = Counter(row["relationship_type"] for row in candidates)
    by_confidence = Counter(row["confidence"] for row in candidates)
    by_evidence = Counter(row["evidence_type"] for row in candidates)
    by_rule = Counter(row.get("generation_rule") or "unknown" for row in candidates)
    needs_review = [row for row in candidates if row["review_status"] == "needs_review"]
    approved_not_promoted = [row for row in candidates if row["review_status"] in {"approved", "edited-approved"} and not row.get("promoted_to_canonical")]
    rejected = [row for row in candidates if row["review_status"] == "rejected"]
    needs_more_research = [row for row in candidates if row["review_status"] == "needs_more_research"]
    duplicates = [row for row in candidates if row.get("duplicate_of_canonical_relationship_id") or _canonical_duplicate(row, canonical)]
    canonical_conflicts = _candidate_canonical_conflicts(candidates, canonical)
    pair_conflicts = _candidate_pair_conflicts(candidates)
    missing_rationale = [row for row in candidates if _blank(row.get("rationale"))]
    missing_source = [row for row in candidates if _blank(row.get("source_name")) or _blank(row.get("source_url"))]
    low_generated = [row for row in candidates if row["confidence"] == "low" and row["evidence_type"] == "generated_inference"]
    high_priority = _high_priority_candidates(candidates)

    return [
        "# Companion Candidate Review Report",
        "",
        "## 1. Summary",
        "",
        f"- Total candidate relationships: {len(candidates)}",
        "",
        "### Count by review_status",
        *_counter_lines(by_status),
        "",
        "### Count by relationship_type",
        *_counter_lines(by_type),
        "",
        "### Count by confidence",
        *_counter_lines(by_confidence),
        "",
        "### Count by evidence_type",
        *_counter_lines(by_evidence),
        "",
        "### Count by generation_rule",
        *_counter_lines(by_rule),
        "",
        "## 2. Candidates Needing Review",
        *_candidate_lines(needs_review, plants, limit=50),
        "",
        "## 3. Approved Candidates Not Yet Promoted",
        *_candidate_lines(approved_not_promoted, plants, limit=50),
        "",
        "## 4. Rejected Candidates",
        *_candidate_lines(rejected, plants, limit=50),
        "",
        "## 5. Needs More Research",
        *_candidate_lines(needs_more_research, plants, limit=50),
        "",
        "## 6. Duplicate Canonical Relationships",
        *_candidate_lines(duplicates, plants, limit=50),
        "",
        "## 7. Conflicts With Canonical Relationships",
        *_candidate_lines(canonical_conflicts, plants, limit=50),
        "",
        "## 8. Candidate Pair Conflicts",
        *_candidate_lines(pair_conflicts, plants, limit=50),
        "",
        "## 9. Missing Data",
        "",
        f"- Candidates missing rationale: {len(missing_rationale)}",
        *_candidate_lines(missing_rationale, plants, limit=30),
        "",
        f"- Candidates missing source_name or source_url: {len(missing_source)}",
        *_candidate_lines(missing_source, plants, limit=30),
        "",
        "## 10. Low-Confidence Generated Candidates",
        *_candidate_lines(low_generated, plants, limit=50),
        "",
        "## 11. High-Priority Review Candidates",
        *_candidate_lines(high_priority, plants, limit=75),
    ]


def _counter_lines(counter: Counter[str]) -> list[str]:
    if not counter:
        return ["- None"]
    return [f"- `{key}`: {value}" for key, value in sorted(counter.items())]


def _rank_lines(rows: list[tuple[str, int]], plants: dict[str, dict]) -> list[str]:
    if not rows:
        return ["- None"]
    return [f"- {_display(plants, slug)}: {count}" for slug, count in rows]


def _relationship_lines(rows: list[dict[str, Any]], plants: dict[str, dict], *, limit: int) -> list[str]:
    if not rows:
        return ["- None"]
    lines = []
    for row in rows[:limit]:
        lines.append(
            f"- {_display(plants, row['source_plant_slug'])} -> {_display(plants, row['target_plant_slug'])}: "
            f"`{row['relationship_type']}`, `{row['confidence']}`, `{row['evidence_type']}`. {row.get('rationale', '').strip()}"
        )
    if len(rows) > limit:
        lines.append(f"- ...and {len(rows) - limit} more.")
    return lines


def _candidate_lines(rows: list[dict[str, Any]], plants: dict[str, dict], *, limit: int) -> list[str]:
    if not rows:
        return ["- None"]
    lines = []
    for row in rows[:limit]:
        lines.append(
            f"- {_display(plants, row['source_plant_slug'])} -> {_display(plants, row['target_plant_slug'])}: "
            f"`{row['relationship_type']}`, `{row.get('review_status', 'unknown')}`, rule `{row.get('generation_rule') or row.get('rule_name') or 'unknown'}`. {row.get('rationale', '').strip()}"
        )
    if len(rows) > limit:
        lines.append(f"- ...and {len(rows) - limit} more.")
    return lines


def _plant_counts(rows: list[dict[str, Any]], relationship_types: set[str], *, symmetric: bool) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in rows:
        if row["relationship_type"] not in relationship_types:
            continue
        counts[row["source_plant_slug"]] += 1
        if symmetric or row.get("relationship_direction") == "symmetric":
            counts[row["target_plant_slug"]] += 1
    return counts


def _conflicts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_pair: dict[frozenset[str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_pair[frozenset((row["source_plant_slug"], row["target_plant_slug"]))].append(row)
    conflicts = []
    for pair_rows in by_pair.values():
        types = {row["relationship_type"] for row in pair_rows}
        if "avoid" in types and types & BENEFICIAL_TYPES:
            conflicts.extend(pair_rows)
        elif types & RISK_TYPES and types & BENEFICIAL_TYPES:
            conflicts.extend(pair_rows)
    return conflicts


def _same_family_risks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if row.get("source_plant_slug") in NIGHTSHADES
        and row.get("target_plant_slug") in NIGHTSHADES
        and row.get("source_plant_slug") != row.get("target_plant_slug")
        and row.get("relationship_type") in {"disease_risk", "pest_risk"}
    ]


def _canonical_research_targets(relationships: list[dict[str, Any]], plants: dict[str, dict]) -> list[str]:
    low_confidence_types = Counter(row["relationship_type"] for row in relationships if row["confidence"] == "low")
    lines = [
        "- Review low-confidence canonical relationship types:",
        *_counter_lines(low_confidence_types),
        "- Audit canonical avoid/risk claims for source strength before using them as hard planning constraints.",
        "- Prioritize extension-service or peer-reviewed sources for relationships currently marked `traditional` or `generated_inference`.",
    ]
    return lines


def _canonical_rows_from_db(session: Session) -> list[dict[str, Any]]:
    plants_by_id = {plant.id: plant for plant in session.scalars(select(Plant)).all()}
    rows = []
    for rel in session.scalars(select(PlantCompanionRelationship).order_by(PlantCompanionRelationship.id)).all():
        source = plants_by_id.get(rel.source_plant_id)
        target = plants_by_id.get(rel.target_plant_id)
        if source is None or target is None or not source.slug or not target.slug:
            continue
        rows.append(
            {
                "id": rel.id,
                "source_plant_slug": source.slug,
                "target_plant_slug": target.slug,
                "relationship_type": rel.relationship_type,
                "confidence": rel.confidence,
                "evidence_type": rel.evidence_type,
                "rationale": rel.rationale,
                "source_name": rel.source_name,
                "source_url": rel.source_url,
                "source_notes": rel.source_notes,
                "relationship_direction": rel.relationship_direction,
                "min_distance_inches": rel.min_distance_inches,
                "max_distance_inches": rel.max_distance_inches,
            }
        )
    return rows


def _candidate_rows_from_db(session: Session) -> list[dict[str, Any]]:
    rows = []
    for candidate in session.scalars(select(CompanionRelationshipCandidate).order_by(CompanionRelationshipCandidate.candidate_slug)).all():
        rows.append(
            {
                "id": candidate.id,
                "candidate_slug": candidate.candidate_slug,
                "source_plant_slug": candidate.source_plant_slug,
                "target_plant_slug": candidate.target_plant_slug,
                "relationship_type": candidate.relationship_type,
                "confidence": candidate.confidence,
                "evidence_type": candidate.evidence_type,
                "rationale": candidate.rationale,
                "source_name": candidate.source_name,
                "source_url": candidate.source_url,
                "source_notes": candidate.source_notes,
                "relationship_direction": candidate.relationship_direction,
                "generation_rule": candidate.generation_rule,
                "duplicate_of_canonical_relationship_id": candidate.duplicate_of_canonical_relationship_id,
                "canonical_relationship_id": candidate.canonical_relationship_id,
                "promoted_to_canonical": candidate.promoted_to_canonical,
                "conflict_notes": candidate.conflict_notes,
                "review_status": candidate.review_status,
            }
        )
    return rows


def _canonical_duplicate(candidate: dict[str, Any], canonical: list[dict[str, Any]]) -> bool:
    for row in canonical:
        if candidate["relationship_type"] != row["relationship_type"]:
            continue
        if candidate["source_plant_slug"] == row["source_plant_slug"] and candidate["target_plant_slug"] == row["target_plant_slug"]:
            return True
        if row.get("relationship_direction") == "symmetric" and candidate["source_plant_slug"] == row["target_plant_slug"] and candidate["target_plant_slug"] == row["source_plant_slug"]:
            return True
    return False


def _candidate_canonical_conflicts(candidates: list[dict[str, Any]], canonical: list[dict[str, Any]]) -> list[dict[str, Any]]:
    conflicts = []
    canonical_by_pair: dict[frozenset[str], set[str]] = defaultdict(set)
    for row in canonical:
        canonical_by_pair[frozenset((row["source_plant_slug"], row["target_plant_slug"]))].add(row["relationship_type"])
    for candidate in candidates:
        canonical_types = canonical_by_pair.get(frozenset((candidate["source_plant_slug"], candidate["target_plant_slug"])), set())
        if not canonical_types:
            continue
        candidate_type = candidate["relationship_type"]
        if candidate_type in BENEFICIAL_TYPES and canonical_types & RISK_TYPES:
            conflicts.append(candidate)
        elif candidate_type in RISK_TYPES and canonical_types & BENEFICIAL_TYPES:
            conflicts.append(candidate)
    return conflicts


def _candidate_pair_conflicts(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_pair: dict[frozenset[str], list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        by_pair[frozenset((row["source_plant_slug"], row["target_plant_slug"]))].append(row)
    conflicts = []
    for rows in by_pair.values():
        types = {row["relationship_type"] for row in rows}
        if types & BENEFICIAL_TYPES and types & RISK_TYPES:
            conflicts.extend(rows)
    return conflicts


def _high_priority_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored = []
    for row in candidates:
        score = 0
        if row["relationship_type"] in {"avoid", "allelopathy", "disease_risk", "pest_risk"}:
            score += 6
        if row["source_plant_slug"] in HIGH_PRIORITY_COMMON_PLANTS or row["target_plant_slug"] in HIGH_PRIORITY_COMMON_PLANTS:
            score += 3
        if row["confidence"] == "high":
            score += 3
        elif row["confidence"] == "medium":
            score += 2
        if row.get("source_name"):
            score += 2
        if row["review_status"] in {"needs_review", "needs_more_research"}:
            score += 1
        if score:
            scored.append((score, row))
    return [row for _, row in sorted(scored, key=lambda item: (-item[0], item[1]["source_plant_slug"], item[1]["target_plant_slug"], item[1]["relationship_type"]))]


def _display(plants: dict[str, dict], slug: str) -> str:
    return plants.get(slug, {}).get("common_name", slug.replace("_", " ").title())


def _blank(value: Any) -> bool:
    return value is None or not str(value).strip()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open() as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a markdown companion relationship review report.")
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--candidate-report-path", type=Path, default=DEFAULT_CANDIDATE_REPORT_PATH)
    args = parser.parse_args()
    reports = build_reports(args.report_path, args.candidate_report_path)
    print(reports["canonical"])
    print(reports["candidates"])
    print(f"Report written to {args.report_path}")
    print(f"Candidate report written to {args.candidate_report_path}")


if __name__ == "__main__":
    main()
