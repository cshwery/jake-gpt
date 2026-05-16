# Jakerton's Garden Planning Tool

JakeGPT is a V0 garden planning web app for drawing a garden on a real property, collecting garden context, choosing goals and plants, and generating a deterministic planting grid.

## V0 Status

This branch is a viable V0, not a production release.

- Login is implemented with manually provisioned users only.
- Address lookup, hardiness zone, frost date, precipitation, and sunlight context are mock-backed or user-assisted.
- The planner is deterministic and rule-based. No LLM agent behavior is required for V0.
- Map drawing supports free-form corner polygons and lasso-style drawing.
- The app runs locally with Postgres/PostGIS, Redis, FastAPI, and Next.js.
- The companion planting pipeline is the most mature data workflow: generated candidates are reviewed before becoming canonical recommendation data.

## Stack

- Frontend: Next.js, TypeScript, Tailwind CSS, shadcn/ui-style local components
- Map: Mapbox GL JS with `@mapbox/mapbox-gl-draw`
- Area: Turf.js in the browser, PostGIS in the backend
- Backend: Python FastAPI, SQLAlchemy, Alembic, Pydantic
- Database: PostgreSQL with PostGIS
- Optional local service: Redis
- Backend package manager: `uv`

## Local Setup

Start infrastructure:

```bash
cd infra
docker compose up -d
```

Configure and start the backend:

```bash
cd ../backend
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run python -m app.seed.seed
uv run uvicorn app.main:app --reload
```

Configure and start the frontend:

```bash
cd ../frontend
cp .env.example .env.local
npm install
npm run dev
```

Open `http://localhost:3000`.

Seeded login:

- Email: `demo@jakegpt.ai`
- Password: `JakePass`

## Map Tokens

Set `NEXT_PUBLIC_MAPBOX_TOKEN` in `frontend/.env.local` to use real Mapbox satellite tiles and drawing.

If no token is set, the frontend uses a local mock satellite panel with a sample polygon button so the happy path still works.

## Happy Path

1. Login with the seeded user.
2. Enter an address. Without a geocoder key, the backend uses the mock geocoder.
3. Draw one garden polygon or use the mock polygon.
4. Review simulated garden context and save sunlight context.
5. Select garden goals and plants.
6. Generate a deterministic plan.
7. View the dimmed map with grid labels and save the plan.

## Companion Pipeline

Canonical companion relationships live in `plant_companion_relationships` and are used by recommendations and plan generation.

Candidate companion relationships live in `companion_relationship_candidates` and are not used by recommendations until reviewed and promoted.

Core workflow:

```bash
cd backend
make generate-companion-candidates
make import-companion-candidates
make export-companion-review-csv
# review backend/reports/companion_candidate_review.csv
make import-companion-review-csv
make import-approved-companion-candidates
make companion-report
```

Important behavior:

- Rejected and research-needed candidates remain stored so they are not repeatedly reintroduced as fresh suggestions.
- Promotion checks for risk/benefit conflicts and holds conflicting generated candidates for more research.
- `make import-approved-companion-candidates` also exports durable JSONL backups, validates them, rebuilds SQLite, and validates SQLite.

Durable artifacts:

- `backend/data/companion_relationships_seed.jsonl`: canonical relationship seed data
- `backend/data/companion_relationship_candidates_reviewed.jsonl`: candidate review history
- `backend/data/generated_companion_candidates.jsonl`: generated candidate suggestions
- `backend/data/jakegpt_plant_knowledge.sqlite`: rebuilt plant knowledge artifact
- `backend/reports/companion_relationship_report.md`: canonical relationship report
- `backend/reports/companion_candidate_review_report.md`: candidate review report

## Companion Graph

The backend exposes a `CompanionGraphService` that loads approved canonical rows from `plant_companion_relationships` and treats plants as graph nodes. Each relationship is an edge with source and target plant slugs, optional cultivar slugs, relationship type, confidence, evidence type, rationale, direction, distance guidance, and source notes.

Symmetric relationships are queryable in both directions. One-way relationships preserve their stored direction. V0 cultivar behavior falls back to parent plant relationships when cultivar-specific edges are absent.

Edge scores are deterministic:

```text
relationship_weight * confidence_multiplier * evidence_multiplier
```

Relationship weights:

- `beneficial`: `+20`
- `guild`: `+30`
- `pollinator_support`: `+12`
- `pest_deterrent`: `+10`
- `nutrient_support`: `+10`
- `shade_support`: `+8`
- `succession`: `+5`
- `neutral`: `0`
- `competition`: `-10`
- `pest_risk`: `-15`
- `disease_risk`: `-20`
- `avoid`: `-35`
- `allelopathy`: `-50`

Confidence multipliers are `high = 1.0`, `medium = 0.65`, and `low = 0.3`.

Evidence multipliers are `peer_reviewed = 1.0`, `extension_service = 1.0`, `master_gardener = 0.85`, `seed_catalog = 0.65`, `manual = 0.6`, `traditional = 0.5`, and `generated_inference = 0.25`.

Negative relationships are handled conservatively. `find_conflicts` reports `avoid`, `disease_risk`, `pest_risk`, `allelopathy`, and `competition` relationships among selected plants with a suggested action. `suggest_companions` scores candidates against selected plants, explains the relevant edges, and excludes candidates with strong negative relationships unless the caller explicitly includes them.

## Garden Context Engine

`GardenContextService` converts a saved garden polygon into structured context for recommendations, layout scoring, calendars, watering plans, warnings, and explanations.

The service orchestrates replaceable providers:

- `GardenGeometryService`: validates GeoJSON polygons and calculates area, centroid, and bounding box. PostGIS remains the preferred persisted area source when available; tests and fallback paths use a local Python approximation.
- `HardinessZoneProvider`: v0 uses `MockHardinessZoneProvider` with latitude bands. A v1 `LocalPostGISHardinessZoneProvider` should query imported USDA Plant Hardiness Zone polygons in PostGIS.
- `FrostDateProvider`: v0 uses `MockFrostDateProvider`, approximating last/first frost from hardiness zone. A later provider should calculate median or safety-percentile frost dates from historical daily minimum temperatures.
- `PrecipitationProvider`: v0 uses `MockPrecipitationProvider`, returning estimated annual and growing-season precipitation plus `low`, `medium`, or `high` category. A later provider should use historical daily precipitation.
- `SunlightProvider`: v0 uses `UserAssistedSunlightProvider`. The user should override sunlight because satellite imagery alone does not account for trees, buildings, fences, hills, or seasonal shade.

The context API returns nested DTOs:

- geometry: area, centroid, bounding box
- hardiness: zone, source, confidence
- frost: estimated last frost, first frost, growing-season days, source, confidence
- precipitation: annual/growing-season precipitation, category, source, confidence
- sunlight: category, method, confidence, user override
- assumptions, warnings, and raw provider metadata

Available endpoints:

```bash
POST /api/gardens/{garden_id}/context/generate
POST /api/gardens/{garden_id}/context/recalculate
GET /api/gardens/{garden_id}/context
PATCH /api/gardens/{garden_id}/context/sunlight
```

All v0 climate values are estimates or mock-backed. The UI labels provider source/confidence and displays assumptions and warnings instead of presenting false precision.

## Graph-Aware Recommendations

`GardenRecommendationService` generates deterministic, explainable plant and cultivar recommendations from `GardenContextDTO`, user goals, selected plants, plant/cultivar data, plant families, and the canonical companion graph.

The recommender combines these score categories:

- hardiness fit
- sunlight fit
- precipitation/water fit
- user goal fit
- maintenance preference
- garden size and spacing feasibility
- companion graph score
- plant-family disease/pest clustering risk
- cultivar fit
- beginner friendliness
- diversity for combination gardens

Each recommendation returns a `score_breakdown`, reason codes, warnings, cultivar suggestions, and a plain-language explanation. Scores are advisory; low-confidence companion claims have small impact, and strong negative companion relationships can override weak positive relationships.

Plant families are stored in `plant_families`, with `plants.plant_family_id` linking species to common crop families such as Solanaceae, Cucurbitaceae, Brassicaceae, Fabaceae, Apiaceae, Amaryllidaceae, Asteraceae, Lamiaceae, Rosaceae, Poaceae, and Amaranthaceae. Same-family plants are not automatically excluded, but they receive a light risk penalty and warnings for crop-rotation and disease-pressure planning. Known graph risks, such as tomato/potato disease pressure, remain stronger than generic family warnings.

Cultivar scoring uses cultivar-specific fields when present:

- days to maturity against the context growing season
- hardiness and spacing overrides
- disease resistance
- heat/cold/drought tolerance
- compact or container-friendly habit
- common uses and user goals

When cultivar fields are missing, the recommender falls back to species defaults and marks the recommendation with `FALLBACK_TO_SPECIES_DEFAULTS`.

Recommendation endpoints:

```bash
POST /api/gardens/{garden_id}/recommendations/generate
GET /api/gardens/{garden_id}/recommendations/latest
```

The generate endpoint requires existing garden context. If context has not been generated, it returns a helpful error instead of guessing. Recommendation runs are persisted in `garden_recommendation_runs` for later retrieval.

The legacy `POST /api/plants/suggest` endpoint remains available for the v0 happy path, but it now delegates internally to `GardenRecommendationService` and adapts the rich recommendation result back into the older `PlantSuggestion[]` response shape.

## Layout Engine

`RuleBasedGardenPlanner` delegates physical placement to `LayoutEngine`. The planner still owns the v0 plan orchestration and companion notes, while `LayoutEngine` owns grid creation, placement, quantity estimates, layout warnings, explanations, and assumptions.

`LayoutEngine` v0 intentionally preserves the existing deterministic grid behavior:

- default 4-column grid
- row count based on selected plant count
- trees and tall plants prefer the north/top row
- quantities are estimated from garden area and plant spacing, then capped
- layout output still converts to the existing `PlanItemRead` and `GeneratedPlan` response shape

The engine accepts an optional `CompanionGraphService` and uses it lightly to keep obvious beneficial companions near each other and separate strong negative pairs when the simple grid can do so. Future work can persist `garden_layouts`, add richer scoring, and optimize against the drawn polygon without changing the public plan response in this v0 refactor.

## Plant Knowledge Commands

```bash
cd backend
make build-plant-kb
make validate-plant-kb
make import-plant-kb
make validate-companion-relationships
make export-reviewed-companion-data
```

Runtime uses Postgres. SQLite is a durable local seed/build artifact that should be kept in sync after reviewed batch updates.

## Tests

Backend:

```bash
cd backend
uv run pytest
```

Frontend:

```bash
cd frontend
npm test
```

## Notes

Climate, hardiness, frost, precipitation, geocoding, and planning are intentionally behind replaceable service interfaces. Replace mocks with real integrations behind those service boundaries.

Do not use the deprecated Google Maps Drawing Library. The map drawing implementation is Mapbox-compatible.
