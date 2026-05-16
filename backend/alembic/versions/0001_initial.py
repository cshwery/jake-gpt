"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-08
"""

from alembic import op
import geoalchemy2
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "plants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("common_name", sa.String(120), nullable=False),
        sa.Column("scientific_name", sa.String(160), nullable=True),
        sa.Column("plant_type", sa.String(80), nullable=False),
        sa.Column("edible", sa.Boolean(), nullable=False),
        sa.Column("flower", sa.Boolean(), nullable=False),
        sa.Column("tree", sa.Boolean(), nullable=False),
        sa.Column("perennial", sa.Boolean(), nullable=False),
        sa.Column("min_zone", sa.Integer(), nullable=False),
        sa.Column("max_zone", sa.Integer(), nullable=False),
        sa.Column("sunlight_requirement", sa.String(50), nullable=False),
        sa.Column("water_requirement", sa.String(50), nullable=False),
        sa.Column("spacing_inches", sa.Integer(), nullable=False),
        sa.Column("row_spacing_inches", sa.Integer(), nullable=False),
        sa.Column("days_to_maturity", sa.Integer(), nullable=True),
        sa.Column("maintenance_level", sa.String(50), nullable=False),
        sa.Column("planting_notes", sa.Text(), nullable=False),
    )
    op.create_index("ix_plants_common_name", "plants", ["common_name"], unique=True)
    op.create_table(
        "properties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("address_raw", sa.String(500), nullable=False),
        sa.Column("normalized_address", sa.String(500), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("point", geoalchemy2.Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_properties_user_id", "properties", ["user_id"])
    op.create_table(
        "plant_companions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plant_id", sa.Integer(), sa.ForeignKey("plants.id"), nullable=False),
        sa.Column("companion_plant_id", sa.Integer(), sa.ForeignKey("plants.id"), nullable=False),
        sa.Column("relationship_type", sa.String(30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.UniqueConstraint("plant_id", "companion_plant_id", name="uq_plant_companion_pair"),
    )
    op.create_index("ix_plant_companions_plant_id", "plant_companions", ["plant_id"])
    op.create_index("ix_plant_companions_companion_plant_id", "plant_companions", ["companion_plant_id"])
    op.create_table(
        "gardens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("polygon_geojson", sa.JSON(), nullable=False),
        sa.Column("polygon", geoalchemy2.Geography(geometry_type="POLYGON", srid=4326), nullable=False),
        sa.Column("area_sq_m", sa.Float(), nullable=False),
        sa.Column("area_sq_ft", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_gardens_property_id", "gardens", ["property_id"])
    op.create_table(
        "garden_contexts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("garden_id", sa.Integer(), sa.ForeignKey("gardens.id"), nullable=False),
        sa.Column("hardiness_zone", sa.String(20), nullable=False),
        sa.Column("last_frost_date", sa.Date(), nullable=False),
        sa.Column("precipitation_category", sa.String(50), nullable=False),
        sa.Column("sunlight_estimate", sa.String(50), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_garden_contexts_garden_id", "garden_contexts", ["garden_id"], unique=True)
    op.create_table(
        "garden_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("garden_id", sa.Integer(), sa.ForeignKey("gardens.id"), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("layout_grid", sa.JSON(), nullable=False),
        sa.Column("companion_notes", sa.JSON(), nullable=False),
        sa.Column("goals", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_garden_plans_garden_id", "garden_plans", ["garden_id"])
    op.create_table(
        "plan_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("garden_plans.id"), nullable=False),
        sa.Column("plant_id", sa.Integer(), sa.ForeignKey("plants.id"), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("row", sa.Integer(), nullable=False),
        sa.Column("col", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("x_pct", sa.Float(), nullable=False),
        sa.Column("y_pct", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_plan_items_plan_id", "plan_items", ["plan_id"])


def downgrade() -> None:
    op.drop_table("plan_items")
    op.drop_table("garden_plans")
    op.drop_table("garden_contexts")
    op.drop_table("gardens")
    op.drop_table("plant_companions")
    op.drop_table("properties")
    op.drop_table("plants")
    op.drop_table("users")
