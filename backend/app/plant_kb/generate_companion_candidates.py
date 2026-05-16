from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.plant_kb.companion_candidates import candidate_slug_for
from app.plant_kb.seed_data import plant_records

DEFAULT_CANDIDATE_JSONL = Path(__file__).resolve().parents[2] / "data" / "generated_companion_candidates.jsonl"

LEGUMES = {"bean", "pea", "clover", "crimson_clover", "hairy_vetch"}
HEAVY_FEEDERS = {
    "tomato",
    "pepper",
    "eggplant",
    "corn",
    "cucumber",
    "summer_squash",
    "winter_squash",
    "pumpkin",
    "broccoli",
    "cabbage",
    "cauliflower",
    "brussels_sprouts",
}
FRUITING_AND_ORCHARD = {
    "tomato",
    "pepper",
    "eggplant",
    "cucumber",
    "summer_squash",
    "winter_squash",
    "pumpkin",
    "apple",
    "pear",
    "peach",
    "plum",
    "cherry",
    "blueberry",
    "strawberry",
    "raspberry",
    "blackberry",
    "grape",
}
POLLINATOR_SUPPORTERS = {"marigold", "calendula", "zinnia", "sunflower", "borage", "lavender", "dill", "cilantro", "alyssum"}
AROMATIC_HERBS = {"basil", "rosemary", "thyme", "sage", "dill", "cilantro", "mint"}
PEST_PRONE_VEGETABLES = {"tomato", "pepper", "eggplant", "cucumber", "summer_squash", "winter_squash", "pumpkin", "cabbage", "broccoli", "kale", "potato"}
TALL_SHADE_PLANTS = {"corn", "sunflower"}
HEAT_SENSITIVE_GREENS = {"lettuce", "spinach", "cilantro", "arugula", "bok_choy", "mustard_greens", "endive", "radicchio"}
SPREADING_GROUND_COVERS = {"summer_squash", "winter_squash", "pumpkin"}
TALL_GUILD_TARGETS = {"corn", "sunflower"}
NIGHTSHADES = {"tomato", "pepper", "eggplant", "potato", "tomatillo", "ground_cherry"}
FENNEL_SENSITIVE_VEGETABLES = {
    "tomato",
    "pepper",
    "eggplant",
    "potato",
    "bean",
    "pea",
    "carrot",
    "lettuce",
    "cucumber",
    "cabbage",
    "broccoli",
    "kale",
}
AGGRESSIVE_SPREADERS = {"mint", "lemon_balm"}
LOW_CROPS = {"lettuce", "spinach", "arugula", "strawberry", "carrot", "radish", "beet"}
APIACEAE_SEED_SAVING_CROPS = {
    "carrot",
    "celery",
    "cilantro",
    "dill",
    "fennel",
    "parsley",
    "parsnip",
}
APIACEAE_SEED_SAVING_PRIORITY_PAIRS = {
    frozenset(("cilantro", "dill")),
    frozenset(("cilantro", "fennel")),
    frozenset(("dill", "fennel")),
}


def generate_candidates(plants: list[dict] | None = None) -> list[dict[str, Any]]:
    plants = plants or plant_records()
    slugs = {plant["slug"] for plant in plants}
    by_slug = {plant["slug"]: plant for plant in plants}
    candidates: list[dict[str, Any]] = []

    for legume in sorted(LEGUMES & slugs):
        for heavy_feeder in sorted((HEAVY_FEEDERS & slugs) - {legume}):
            candidates.append(
                _candidate(
                    legume,
                    heavy_feeder,
                    "nutrient_support",
                    "legume_nitrogen_support_candidate",
                    f"{_name(by_slug, legume)} is a legume and may support soil nitrogen cycling near heavy feeders, but short-term benefit is not assumed.",
                    "one_way",
                    min_distance_inches=6,
                    max_distance_inches=36,
                )
            )

    pollinator_supporters = {slug for slug in POLLINATOR_SUPPORTERS & slugs if (by_slug[slug].get("pollinator_value_score") or 0) >= 7}
    for supporter in sorted(pollinator_supporters):
        for target in sorted((FRUITING_AND_ORCHARD & slugs) - {supporter}):
            candidates.append(
                _candidate(
                    supporter,
                    target,
                    "pollinator_support",
                    "high_pollinator_value_support_candidate",
                    f"{_name(by_slug, supporter)} has high pollinator value and may support pollinator activity near fruiting crops.",
                    "symmetric",
                    min_distance_inches=12,
                    max_distance_inches=72,
                )
            )

    for herb in sorted(AROMATIC_HERBS & slugs):
        for target in sorted((PEST_PRONE_VEGETABLES & slugs) - {herb}):
            candidates.append(
                _candidate(
                    herb,
                    target,
                    "pest_deterrent",
                    "aromatic_diversity_candidate",
                    f"{_name(by_slug, herb)} is aromatic and may add pest-confusion diversity near pest-prone vegetables; this is not treated as proven control.",
                    "symmetric",
                    min_distance_inches=8,
                    max_distance_inches=36,
                )
            )

    for tall in sorted(TALL_SHADE_PLANTS & slugs):
        for green in sorted((HEAT_SENSITIVE_GREENS & slugs) - {tall}):
            candidates.append(
                _candidate(
                    tall,
                    green,
                    "shade_support",
                    "tall_crop_partial_shade_candidate",
                    f"{_name(by_slug, tall)} can cast partial shade that may help heat-sensitive greens in hot conditions if placed to avoid excessive shade.",
                    "one_way",
                    min_distance_inches=18,
                    max_distance_inches=60,
                )
            )

    for spreader in sorted(SPREADING_GROUND_COVERS & slugs):
        for target in sorted((TALL_GUILD_TARGETS & slugs) - {spreader}):
            candidates.append(
                _candidate(
                    spreader,
                    target,
                    "guild",
                    "spreading_crop_ground_cover_candidate",
                    f"{_name(by_slug, spreader)} can shade soil below taller crops and may contribute to weed suppression when spacing is managed.",
                    "symmetric",
                    min_distance_inches=24,
                    max_distance_inches=72,
                )
            )

    nightshades = sorted(NIGHTSHADES & slugs)
    for index, source in enumerate(nightshades):
        for target in nightshades[index + 1 :]:
            candidates.append(
                _candidate(
                    source,
                    target,
                    "disease_risk",
                    "same_family_nightshade_disease_risk",
                    "Nightshade crops can share disease and pest pressure; close clustering should be flagged as a risk rather than a beneficial pairing.",
                    "symmetric",
                    min_distance_inches=36,
                    max_distance_inches=None,
                )
            )

    if "fennel" in slugs:
        for target in sorted(FENNEL_SENSITIVE_VEGETABLES & slugs):
            candidates.append(
                _candidate(
                    "fennel",
                    target,
                    "allelopathy",
                    "fennel_isolation_candidate",
                    "Fennel is commonly isolated from vegetable beds because of reported suppressive effects; treat as a review-needed allelopathy candidate.",
                    "one_way",
                    min_distance_inches=48,
                    max_distance_inches=None,
                )
            )

    for spreader in sorted(AGGRESSIVE_SPREADERS & slugs):
        for target in sorted((LOW_CROPS & slugs) - {spreader}):
            candidates.append(
                _candidate(
                    spreader,
                    target,
                    "competition",
                    "aggressive_spreader_competition_candidate",
                    f"{_name(by_slug, spreader)} spreads aggressively and may compete with low-growing crops unless contained or separated.",
                    "one_way",
                    min_distance_inches=36,
                    max_distance_inches=None,
                )
            )

    apiaceae_seed_crops = sorted(APIACEAE_SEED_SAVING_CROPS & slugs)
    for index, source in enumerate(apiaceae_seed_crops):
        for target in apiaceae_seed_crops[index + 1 :]:
            priority_pair = frozenset((source, target)) in APIACEAE_SEED_SAVING_PRIORITY_PAIRS
            min_distance = 600 if priority_pair else 240
            candidates.append(
                _candidate(
                    source,
                    target,
                    "avoid",
                    "apiaceae_seed_saving_isolation_candidate",
                    (
                        f"{_name(by_slug, source)} and {_name(by_slug, target)} are Apiaceae crops that can attract insect pollinators when flowering; "
                        "flag close co-flowering plantings for seed-saving review. This is a seed-purity caution, not a claim that edible leaf harvests are incompatible."
                    ),
                    "symmetric",
                    min_distance_inches=min_distance,
                    max_distance_inches=None,
                )
            )

    return _dedupe(candidates)


def write_candidates(path: Path = DEFAULT_CANDIDATE_JSONL) -> list[dict[str, Any]]:
    candidates = generate_candidates()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for candidate in candidates:
            handle.write(json.dumps(candidate, sort_keys=True) + "\n")
    return candidates


def _candidate(
    source: str,
    target: str,
    relationship_type: str,
    rule_name: str,
    rationale: str,
    relationship_direction: str,
    *,
    min_distance_inches: int | None,
    max_distance_inches: int | None,
) -> dict[str, Any]:
    candidate_slug = candidate_slug_for(source, target, relationship_type, "generated_inference", generation_rule=rule_name)
    return {
        "candidate_slug": candidate_slug,
        "source_plant_slug": source,
        "target_plant_slug": target,
        "relationship_type": relationship_type,
        "confidence": "low",
        "evidence_type": "generated_inference",
        "rationale": rationale,
        "generation_rule": rule_name,
        "generated_by": "trait_candidate_generator",
        "rule_name": rule_name,
        "review_status": "needs_review",
        "relationship_direction": relationship_direction,
        "min_distance_inches": min_distance_inches,
        "max_distance_inches": max_distance_inches,
    }


def _dedupe(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str, str]] = set()
    unique: list[dict[str, Any]] = []
    for candidate in candidates:
        key = (
            candidate["source_plant_slug"],
            candidate["target_plant_slug"],
            candidate["relationship_type"],
            candidate["candidate_slug"],
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return sorted(unique, key=lambda item: (item["generation_rule"], item["source_plant_slug"], item["target_plant_slug"], item["relationship_type"]))


def _name(plants: dict[str, dict], slug: str) -> str:
    return plants.get(slug, {}).get("common_name", slug.replace("_", " ").title())


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate review-needed companion relationship candidates from plant traits.")
    parser.add_argument("--path", type=Path, default=DEFAULT_CANDIDATE_JSONL)
    args = parser.parse_args()
    candidates = write_candidates(args.path)
    print(f"Wrote {len(candidates)} generated companion candidates to {args.path}")


if __name__ == "__main__":
    main()
