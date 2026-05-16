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
