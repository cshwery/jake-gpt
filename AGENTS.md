# JakeGPT Project Instructions

This project is a monorepo for Jakerton's Garden Planning Tool, branded as JakeGPT.

## Structure

- `frontend/`: Next.js, TypeScript, Tailwind CSS, shadcn/ui-style local components.
- `backend/`: FastAPI, SQLAlchemy, Alembic, PostGIS-backed persistence.
- `infra/`: local Docker Compose services.

## Engineering Notes

- Use GeoJSON between frontend and backend.
- Use Turf.js for frontend area feedback.
- Use PostGIS for backend authoritative garden area.
- Keep external providers behind service interfaces.
- Keep the v0 planner deterministic and rule-based.
- Do not add public registration until explicitly requested.
- Do not use the deprecated Google Maps Drawing Library.
- At logical checkpoints, such as completing a viable V0 or a major data pipeline, remind the user to commit and push before continuing.
- Follow GitHub flow: keep `main` protected, do new work on feature branches, and open pull requests into `main` instead of committing directly to `main`.

## Local Commands

- Backend tests: `cd backend && uv run pytest`
- Backend dev server: `cd backend && uv run uvicorn app.main:app --reload`
- Frontend dev server: `cd frontend && npm run dev`
- Infra: `cd infra && docker compose up -d`
