# JakeGPT Plant Knowledge Base

The canonical development plant knowledge artifact is:

`backend/data/jakegpt_plant_knowledge.sqlite`

Build it with:

```bash
make build-plant-kb
```

Validate it before import:

```bash
make validate-plant-kb
```

Import or sync it into the PostgreSQL runtime database:

```bash
make import-plant-kb
```

Companion relationship seed data lives in JSONL:

`backend/data/companion_relationships_seed.jsonl`

Validate and import only companion relationships with:

```bash
make validate-companion-relationships
make import-companion-relationships
```

Each JSONL row uses stable plant and cultivar slugs rather than database IDs, and carries relationship type, evidence type, confidence, rationale, source metadata, direction, and distance hints. Companion planting claims are intentionally confidence-scored because sources range from extension guidance to traditional practice and generated planning inferences.

Generate review-needed candidate relationships from plant traits with:

```bash
make generate-companion-candidates
make import-companion-candidates
```

This writes `backend/data/generated_companion_candidates.jsonl` and imports those rows into `companion_relationship_candidates` for human review. Candidate rows do not affect recommendations. Rejected candidates remain stored with `review_status = rejected` so the same suggestion can be suppressed on later imports.

Approved candidates are promoted into the canonical `plant_companion_relationships` table:

```bash
uv run python -m app.plant_kb.promote_companion_candidate <candidate_slug> --reviewed-by <name>
```

For spreadsheet-based review, export the pending candidate queue:

```bash
make export-companion-review-csv
```

Reviewers fill in `reviewer_decision` with `approve`, `reject`, `needs_more_research`, or `edit`, optionally add `reviewer_notes`, and then import decisions:

```bash
make import-companion-review-csv
make import-approved-companion-candidates
```

The approved-candidate import only promotes `approved` and `edited-approved` candidates. It records `canonical_relationship_id` and sets `promoted_to_canonical = true`, while leaving rejected and research-needed candidates out of canonical recommendation data. It also exports reviewed PostgreSQL state back to JSONL, validates the seed data, rebuilds SQLite, and validates the SQLite artifact so batch review imports keep backups current by default.

Generated rows are marked `evidence_type = generated_inference`, `confidence = low`, and `review_status = needs_review` until a reviewer approves, rejects, edits, or marks them as needing more research.

To refresh durable seed artifacts without promoting new candidates, export the reviewed PostgreSQL state and rebuild SQLite:

```bash
make export-reviewed-companion-data
make validate-companion-relationships
make build-plant-kb
make validate-plant-kb
```

This updates `backend/data/companion_relationships_seed.jsonl` for canonical relationships, writes candidate review history to `backend/data/companion_relationship_candidates_reviewed.jsonl`, and rebuilds `backend/data/jakegpt_plant_knowledge.sqlite`.

The import uses stable plant and cultivar slugs for idempotent upserts, so it is safe to run repeatedly.

## Species And Cultivars

Plants are modeled at two levels:

- `plants`: species or crop type defaults, such as `tomato`, `basil`, or `apple`
- `plant_cultivars`: child cultivar records, such as `tomato_sungold` or `apple_honeycrisp`

Cultivars are never standalone plants. A cultivar always points to a parent `plants.id`. Runtime helpers resolve cultivar-specific values first and fall back to species defaults when a cultivar field is missing.

## Adding Data

Seed data currently lives in `app/plant_kb/seed_data.py` and is compiled into SQLite by the builder. To add plants or cultivars:

1. Add or update the structured seed entries.
2. Run `make build-plant-kb`.
3. Run `make validate-plant-kb`.
4. Run `make import-plant-kb` when PostgreSQL is available.

Keep slugs stable. Existing slugs are the identity used for sync, backups, and future edits.
