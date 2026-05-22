# Jakerton's Garden Planning Tool

JakeGPT is a V0 garden planning web app for drawing a garden on a real property, collecting garden context, choosing goals and plants, and generating a deterministic planting grid.

## V0 Status

This branch is a viable V0, not a production release.

- Login is implemented with manually provisioned users only.
- Address lookup can use Mapbox when configured. Hardiness zone, frost date, precipitation, and sunlight context are mock-backed or user-assisted.
- The planner is deterministic and rule-based. No LLM agent behavior is required for V0.
- Map drawing supports free-form corner polygons and lasso-style drawing.
- The product flow now runs in this order: Address / Draw Garden -> Garden Context -> Goals & Setup -> Plant Selection -> Recommendations -> Layout -> Plan.
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

## Architecture

JakeGPT remains a single-repo modular monolith. Keep `backend/`, `frontend/`, `infra/`, and `docs/` together while the product boundaries are still evolving. Do not split engines into separate repositories yet.

Backend engines are logically separated under `backend/app/engines/`, with compatibility imports kept under `backend/app/services/` while the codebase migrates gradually. The main deterministic flow is:

```text
GardenContextDTO
-> GardenRecommendationResult
-> PlantingDesignPlan
-> LayoutBlueprint
-> LayoutResult
-> future ActionPlan
```

The Planting Design layer sits between recommendations and layout. It assigns plant roles, builds companion clusters, creates pollinator-border guidance, and produces gardener-friendly separation rules.

`LayoutBlueprint` is the concrete design instruction layer produced from `PlantingDesignPlan`: rows, raised-bed plantings, chaos guidance, tree/shrub sections, symbols, and placement rules. `LayoutResult` is the persisted/renderable result returned to the frontend.

Planting design concepts:

- Plant roles: primary crops, companion herbs, pollinator flowers, border plants, filler crops, trellised crops, tall crops, sprawling crops, leafy greens, root crops, perennials, trees, shrubs, and plants to isolate.
- Companion clusters: explainable groups such as tomato with basil nearby and marigolds repeated along bed edges or row ends.
- Separation rules: user-facing keep-apart guidance for disease risk, pest risk, allelopathy, competition, aggressive spreaders such as mint, and crops like fennel that are best isolated.
- Chaos mode: advisory guidance rather than a detailed placement map. It emphasizes resilient, lower-maintenance, direct-sow-friendly plants, pollinator support, and separation warnings.
- Raised-bed tree behavior: trees are not recommended for raised beds unless cultivar data confirms a dwarf or compact variety.
- Hardiness filtering: incompatible perennial, tree, shrub, and berry candidates are hidden from normal plant search and excluded from recommendations when garden context has a hardiness zone. Annual vegetables and flowers are not excluded solely by perennial hardiness-zone mismatch.

The future Action Plan engine should consume `LayoutResult`, `LayoutBlueprint`, and `PlantingDesignPlan`, but watering calendars, planting calendars, shopping lists, affiliate links, and nursery commerce are intentionally out of scope for the current V0 work.

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
make import-plant-kb
make import-companion-relationships
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

Set these values to use the real Mapbox-backed address and map flow:

Backend `backend/.env`:

```bash
GEOCODER_PROVIDER=mapbox
MAPBOX_ACCESS_TOKEN=pk_or_secret_mapbox_token
```

Frontend `frontend/.env.local`:

```bash
NEXT_PUBLIC_MAPBOX_TOKEN=pk_mapbox_token
```

The backend geocoding implementation is behind `app.services.geocoding`. `GEOCODER_PROVIDER=mapbox` calls the Mapbox Geocoding API and persists provider metadata with the property. `GEOCODER_PROVIDER=mock`, or a missing backend token, uses the deterministic mock geocoder for local development and tests.

The frontend uses Mapbox satellite tiles, Mapbox navigation/scale controls, and `@mapbox/mapbox-gl-draw` when `NEXT_PUBLIC_MAPBOX_TOKEN` is configured.

If no token is set, the frontend uses a local mock satellite panel with a sample polygon button so the happy path still works.

## Garden Drawing Workflow

The map flow is designed to prevent accidental parcel-sized gardens:

1. Enter an address and confirm the normalized property returned by the backend geocoder.
2. Open the satellite map at yard-level zoom, usually zoom 18 or 19.
3. Zoom in until the intended planting area is clearly visible.
4. Draw only the actual garden boundary with the polygon tool.
5. Review live Turf.js area feedback, then save the boundary.
6. The backend validates and stores the GeoJSON polygon, calculates authoritative area, and returns the saved garden.

Area categories:

- Tiny: less than 25 sq ft
- Small: 25-100 sq ft
- Medium: 100-500 sq ft
- Large: 500-2,000 sq ft
- Very Large: 2,000-10,000 sq ft
- Probably Accidental: more than 10,000 sq ft

The UI warns when a garden is unusually small, larger than 2,000 sq ft, or larger than 10,000 sq ft. These warnings are guardrails only; the backend still validates geometry shape and area before persistence.

## Happy Path

1. Login with the seeded user.
2. Enter an address and confirm the geocoded property. Without Mapbox configuration, the backend uses the mock geocoder.
3. Draw one garden polygon on the satellite map or use the mock polygon fallback.
4. Review simulated garden context and save sunlight context.
5. Complete the Goals & Setup step, including raised beds, rows, and indoor-start preferences.
6. Select garden plants and cultivars.
7. Generate recommendations, then generate a deterministic layout.
8. Generate and save the plan.

## Usability Conventions

- Recommendation cards show fit labels instead of raw numeric scores in the UI.
- Layout cards show layout quality labels instead of raw numeric layout scores in the UI.
- Garden area is grouped into Tiny, Small, Medium, Large, Very Large, and Probably Accidental.
- The top of the layout grid represents north.
- Layout and Plan tabs render from the same canonical layout data and shared grid component.
- Free-text preferences remain available, with a placeholder such as: `I want to have some food each week rather than one big harvest`.
- Raised beds are captured in goals/setup for now; draggable raised-bed placement is a future feature.

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

`RuleBasedGardenPlanner` still preserves the v0 happy path and `POST /api/plans/generate` response shape, but physical placement now lives in `LayoutEngine`. The planner owns plan orchestration and companion notes; `LayoutEngine` owns grid creation, candidate layouts, plant placement, score breakdowns, warnings, explanations, assumptions, and optional persistence.

LayoutEngine v1 adds persisted layout records:

- `garden_layouts`: stores layout inputs, full result JSON, score totals, score breakdowns, warnings, explanations, assumptions, and optional links to recommendation runs or garden plans.
- `layout_placements`: stores each plant/cultivar placement, quantity, grid cells, row/column, percentage location, spacing, role, notes, and warnings.

New layout endpoints:

- `POST /api/gardens/{garden_id}/layouts/generate`
- `GET /api/gardens/{garden_id}/layouts/latest`
- `GET /api/layouts/{layout_id}`

The layout generate endpoint requires existing garden context. If context is missing, it returns: `Generate garden context before creating a layout.`

Current v1 layout behavior is deterministic and heuristic-based:

- approximates the drawn polygon as a rectangular north-up grid
- labels cells `A1`, `A2`, `B1`, etc.
- adds access paths for medium and large gardens
- uses cultivar spacing overrides, then species spacing, then category defaults
- keeps tall plants toward the north/top edge where possible
- places pollinator and border flowers near edges where possible
- places positive companions and guilds near each other when simple
- separates avoid, allelopathy, disease-risk, pest-risk, and competition relationships as far as the v1 grid allows
- caps quantities to keep the layout readable

Score breakdowns are transparent:

- `spacing_score`
- `companion_score`
- `conflict_score`
- `access_score`
- `sunlight_score`
- `size_fit_score`
- `diversity_score`
- `total_score`

The companion score uses `CompanionGraphService`; negative relationships are not hidden by weak positive relationships. Strong negative relationships near each other reduce `conflict_score` and produce warnings or explanations.

Current limitations:

- irregular polygons are approximated as rectangles
- sunlight is treated as uniform across the garden
- layout search is a small deterministic candidate set, not an optimizer
- persisted layouts are renderable, but manual drag/drop editing is not implemented yet
- satellite overlay alignment still uses the existing simple grid projection

Future work:

- true polygon clipping
- manual drag/drop layout editing
- per-cell sunlight zones
- improved satellite overlay rendering
- optimization-based layout search
- persisted garden layout revisions and placement history

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
