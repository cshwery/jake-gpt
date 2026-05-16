.PHONY: build-plant-kb validate-plant-kb import-plant-kb export-reviewed-companion-data generate-companion-candidates import-companion-candidates export-companion-review-csv import-companion-review-csv import-approved-companion-candidates validate-companion-relationships import-companion-relationships companion-report test

build-plant-kb:
	uv run python -m app.plant_kb.builder

validate-plant-kb:
	uv run python -m app.plant_kb.validate

import-plant-kb:
	uv run python -m app.plant_kb.import_pg

export-reviewed-companion-data:
	uv run python -m app.plant_kb.export_reviewed_companions

generate-companion-candidates:
	uv run python -m app.plant_kb.generate_companion_candidates

import-companion-candidates:
	uv run python -m app.plant_kb.import_companion_candidates

export-companion-review-csv:
	uv run python -m app.plant_kb.export_companion_review_csv

import-companion-review-csv:
	uv run python -m app.plant_kb.import_companion_review_csv

import-approved-companion-candidates:
	uv run python -m app.plant_kb.import_approved_companion_candidates
	uv run python -m app.plant_kb.export_reviewed_companions
	uv run python -m app.plant_kb.validate_companions
	uv run python -m app.plant_kb.builder
	uv run python -m app.plant_kb.validate

validate-companion-relationships:
	uv run python -m app.plant_kb.validate_companions

import-companion-relationships:
	uv run python -m app.plant_kb.import_companions

companion-report:
	uv run python -m app.plant_kb.companion_report

test:
	uv run pytest
