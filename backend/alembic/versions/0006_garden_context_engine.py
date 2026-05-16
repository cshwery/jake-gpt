"""garden context engine

Revision ID: 0006_garden_context_engine
Revises: 0005_candidate_csv_review
Create Date: 2026-05-16
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_garden_context_engine"
down_revision = "0005_candidate_csv_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("gardens", sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.execute("UPDATE gardens SET updated_at = created_at WHERE updated_at IS NULL")
    op.alter_column("gardens", "updated_at", nullable=False)

    op.add_column("garden_contexts", sa.Column("centroid_lat", sa.Float(), nullable=True))
    op.add_column("garden_contexts", sa.Column("centroid_lon", sa.Float(), nullable=True))
    op.add_column("garden_contexts", sa.Column("bbox_min_lat", sa.Float(), nullable=True))
    op.add_column("garden_contexts", sa.Column("bbox_min_lon", sa.Float(), nullable=True))
    op.add_column("garden_contexts", sa.Column("bbox_max_lat", sa.Float(), nullable=True))
    op.add_column("garden_contexts", sa.Column("bbox_max_lon", sa.Float(), nullable=True))
    op.add_column("garden_contexts", sa.Column("area_sq_m", sa.Float(), nullable=True))
    op.add_column("garden_contexts", sa.Column("area_sq_ft", sa.Float(), nullable=True))
    op.add_column("garden_contexts", sa.Column("hardiness_zone_source", sa.String(length=100), nullable=True))
    op.add_column("garden_contexts", sa.Column("hardiness_zone_confidence", sa.String(length=20), nullable=True))
    op.add_column("garden_contexts", sa.Column("estimated_last_frost_date", sa.Date(), nullable=True))
    op.add_column("garden_contexts", sa.Column("estimated_first_frost_date", sa.Date(), nullable=True))
    op.add_column("garden_contexts", sa.Column("frost_date_source", sa.String(length=100), nullable=True))
    op.add_column("garden_contexts", sa.Column("frost_date_confidence", sa.String(length=20), nullable=True))
    op.add_column("garden_contexts", sa.Column("growing_season_days", sa.Integer(), nullable=True))
    op.add_column("garden_contexts", sa.Column("expected_annual_precipitation_mm", sa.Float(), nullable=True))
    op.add_column("garden_contexts", sa.Column("expected_growing_season_precipitation_mm", sa.Float(), nullable=True))
    op.add_column("garden_contexts", sa.Column("precipitation_source", sa.String(length=100), nullable=True))
    op.add_column("garden_contexts", sa.Column("precipitation_confidence", sa.String(length=20), nullable=True))
    op.add_column("garden_contexts", sa.Column("sunlight_category", sa.String(length=20), nullable=True))
    op.add_column("garden_contexts", sa.Column("sunlight_estimate_method", sa.String(length=40), nullable=True))
    op.add_column("garden_contexts", sa.Column("sunlight_confidence", sa.String(length=20), nullable=True))
    op.add_column("garden_contexts", sa.Column("user_sunlight_override", sa.String(length=20), nullable=True))
    op.add_column("garden_contexts", sa.Column("assumptions", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("garden_contexts", sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("garden_contexts", sa.Column("raw_context", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("garden_contexts", sa.Column("created_at", sa.DateTime(), nullable=True))
    op.add_column("garden_contexts", sa.Column("updated_at", sa.DateTime(), nullable=True))

    op.execute(
        """
        UPDATE garden_contexts
        SET
          centroid_lat = 0,
          centroid_lon = 0,
          bbox_min_lat = 0,
          bbox_min_lon = 0,
          bbox_max_lat = 0,
          bbox_max_lon = 0,
          area_sq_m = 0,
          area_sq_ft = 0,
          hardiness_zone_source = source,
          hardiness_zone_confidence = 'low',
          estimated_last_frost_date = last_frost_date,
          frost_date_source = source,
          frost_date_confidence = 'low',
          precipitation_source = source,
          precipitation_confidence = 'low',
          sunlight_category = lower(replace(sunlight_estimate, ' ', '_')),
          sunlight_estimate_method = 'user_reported',
          sunlight_confidence = 'medium',
          user_sunlight_override = lower(replace(sunlight_estimate, ' ', '_')),
          assumptions = '["Legacy context row migrated; regenerate for full geometry and climate summary."]'::jsonb,
          warnings = '["Context should be recalculated with the Garden Context Engine."]'::jsonb,
          raw_context = jsonb_build_object('legacy_source', source, 'legacy_notes', notes),
          created_at = now(),
          updated_at = now()
        """
    )

    for column in [
        "centroid_lat",
        "centroid_lon",
        "bbox_min_lat",
        "bbox_min_lon",
        "bbox_max_lat",
        "bbox_max_lon",
        "area_sq_m",
        "area_sq_ft",
        "assumptions",
        "warnings",
        "raw_context",
        "created_at",
        "updated_at",
    ]:
        op.alter_column("garden_contexts", column, nullable=False)

    op.alter_column("garden_contexts", "hardiness_zone", nullable=True)
    op.alter_column("garden_contexts", "precipitation_category", type_=sa.String(length=20), nullable=True)
    op.drop_column("garden_contexts", "last_frost_date")
    op.drop_column("garden_contexts", "sunlight_estimate")
    op.drop_column("garden_contexts", "source")
    op.drop_column("garden_contexts", "notes")


def downgrade() -> None:
    op.add_column("garden_contexts", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("garden_contexts", sa.Column("source", sa.String(length=100), nullable=True))
    op.add_column("garden_contexts", sa.Column("sunlight_estimate", sa.String(length=50), nullable=True))
    op.add_column("garden_contexts", sa.Column("last_frost_date", sa.Date(), nullable=True))
    op.execute(
        """
        UPDATE garden_contexts
        SET
          source = COALESCE(hardiness_zone_source, frost_date_source, precipitation_source, 'mock'),
          sunlight_estimate = COALESCE(user_sunlight_override, sunlight_category, 'unknown'),
          last_frost_date = estimated_last_frost_date,
          notes = array_to_string(ARRAY(SELECT jsonb_array_elements_text(warnings)), ' ')
        """
    )
    op.alter_column("garden_contexts", "source", nullable=False)
    op.alter_column("garden_contexts", "sunlight_estimate", nullable=False)
    op.alter_column("garden_contexts", "last_frost_date", nullable=False)
    op.alter_column("garden_contexts", "hardiness_zone", nullable=False)
    op.alter_column("garden_contexts", "precipitation_category", type_=sa.String(length=50), nullable=False)

    for column in [
        "updated_at",
        "created_at",
        "raw_context",
        "warnings",
        "assumptions",
        "user_sunlight_override",
        "sunlight_confidence",
        "sunlight_estimate_method",
        "sunlight_category",
        "precipitation_confidence",
        "precipitation_source",
        "expected_growing_season_precipitation_mm",
        "expected_annual_precipitation_mm",
        "growing_season_days",
        "frost_date_confidence",
        "frost_date_source",
        "estimated_first_frost_date",
        "estimated_last_frost_date",
        "hardiness_zone_confidence",
        "hardiness_zone_source",
        "area_sq_ft",
        "area_sq_m",
        "bbox_max_lon",
        "bbox_max_lat",
        "bbox_min_lon",
        "bbox_min_lat",
        "centroid_lon",
        "centroid_lat",
    ]:
        op.drop_column("garden_contexts", column)

    op.drop_column("gardens", "updated_at")
