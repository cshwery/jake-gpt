"""persisted layout engine

Revision ID: 0008_persisted_layout_engine
Revises: 0007_graph_aware_recommendations
Create Date: 2026-05-17 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_persisted_layout_engine"
down_revision = "0007_graph_aware_recommendations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "garden_layouts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("garden_id", sa.Integer(), nullable=False),
        sa.Column("garden_plan_id", sa.Integer(), nullable=True),
        sa.Column("recommendation_run_id", sa.Integer(), nullable=True),
        sa.Column("layout_version", sa.String(length=40), nullable=False),
        sa.Column("input", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("score_total", sa.Float(), nullable=True),
        sa.Column("score_breakdown", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("explanations", sa.JSON(), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["garden_id"], ["gardens.id"]),
        sa.ForeignKeyConstraint(["garden_plan_id"], ["garden_plans.id"]),
        sa.ForeignKeyConstraint(["recommendation_run_id"], ["garden_recommendation_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_garden_layouts_garden_id"), "garden_layouts", ["garden_id"], unique=False)
    op.create_index(op.f("ix_garden_layouts_garden_plan_id"), "garden_layouts", ["garden_plan_id"], unique=False)
    op.create_index(op.f("ix_garden_layouts_recommendation_run_id"), "garden_layouts", ["recommendation_run_id"], unique=False)

    op.create_table(
        "layout_placements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("garden_layout_id", sa.Integer(), nullable=False),
        sa.Column("plant_id", sa.Integer(), nullable=False),
        sa.Column("cultivar_id", sa.Integer(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("grid_cells", sa.JSON(), nullable=False),
        sa.Column("row", sa.Integer(), nullable=True),
        sa.Column("col", sa.Integer(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("x_pct", sa.Float(), nullable=True),
        sa.Column("y_pct", sa.Float(), nullable=True),
        sa.Column("spacing_inches", sa.Integer(), nullable=True),
        sa.Column("row_spacing_inches", sa.Integer(), nullable=True),
        sa.Column("placement_role", sa.String(length=40), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["cultivar_id"], ["plant_cultivars.id"]),
        sa.ForeignKeyConstraint(["garden_layout_id"], ["garden_layouts.id"]),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_layout_placements_cultivar_id"), "layout_placements", ["cultivar_id"], unique=False)
    op.create_index(op.f("ix_layout_placements_garden_layout_id"), "layout_placements", ["garden_layout_id"], unique=False)
    op.create_index(op.f("ix_layout_placements_plant_id"), "layout_placements", ["plant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_layout_placements_plant_id"), table_name="layout_placements")
    op.drop_index(op.f("ix_layout_placements_garden_layout_id"), table_name="layout_placements")
    op.drop_index(op.f("ix_layout_placements_cultivar_id"), table_name="layout_placements")
    op.drop_table("layout_placements")
    op.drop_index(op.f("ix_garden_layouts_recommendation_run_id"), table_name="garden_layouts")
    op.drop_index(op.f("ix_garden_layouts_garden_plan_id"), table_name="garden_layouts")
    op.drop_index(op.f("ix_garden_layouts_garden_id"), table_name="garden_layouts")
    op.drop_table("garden_layouts")
