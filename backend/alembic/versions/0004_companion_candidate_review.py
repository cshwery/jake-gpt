"""companion relationship candidate review workflow

Revision ID: 0004_comp_candidate_review
Revises: 0003_companion_sources
Create Date: 2026-05-11
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_comp_candidate_review"
down_revision = "0003_companion_sources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "companion_relationship_candidates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_slug", sa.String(length=240), nullable=False),
        sa.Column("source_plant_slug", sa.String(length=160), nullable=False),
        sa.Column("target_plant_slug", sa.String(length=160), nullable=False),
        sa.Column("source_cultivar_slug", sa.String(length=180), nullable=True),
        sa.Column("target_cultivar_slug", sa.String(length=180), nullable=True),
        sa.Column("relationship_type", sa.String(length=40), nullable=False),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column("evidence_type", sa.String(length=40), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("relationship_direction", sa.String(length=20), nullable=False),
        sa.Column("min_distance_inches", sa.Integer(), nullable=True),
        sa.Column("max_distance_inches", sa.Integer(), nullable=True),
        sa.Column("source_name", sa.String(length=180), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_notes", sa.Text(), nullable=True),
        sa.Column("generated_by", sa.String(length=120), nullable=True),
        sa.Column("generation_rule", sa.String(length=160), nullable=True),
        sa.Column("duplicate_of_canonical_relationship_id", sa.Integer(), nullable=True),
        sa.Column("conflict_notes", sa.Text(), nullable=True),
        sa.Column("review_status", sa.String(length=40), server_default="needs_review", nullable=False),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.String(length=180), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["duplicate_of_canonical_relationship_id"], ["plant_companion_relationships.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_companion_relationship_candidates_candidate_slug"), "companion_relationship_candidates", ["candidate_slug"], unique=True)
    op.create_index(op.f("ix_companion_relationship_candidates_duplicate_of_canonical_relationship_id"), "companion_relationship_candidates", ["duplicate_of_canonical_relationship_id"], unique=False)
    op.create_index(op.f("ix_companion_relationship_candidates_review_status"), "companion_relationship_candidates", ["review_status"], unique=False)
    op.create_index(op.f("ix_companion_relationship_candidates_source_plant_slug"), "companion_relationship_candidates", ["source_plant_slug"], unique=False)
    op.create_index(op.f("ix_companion_relationship_candidates_target_plant_slug"), "companion_relationship_candidates", ["target_plant_slug"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_companion_relationship_candidates_target_plant_slug"), table_name="companion_relationship_candidates")
    op.drop_index(op.f("ix_companion_relationship_candidates_source_plant_slug"), table_name="companion_relationship_candidates")
    op.drop_index(op.f("ix_companion_relationship_candidates_review_status"), table_name="companion_relationship_candidates")
    op.drop_index(op.f("ix_companion_relationship_candidates_duplicate_of_canonical_relationship_id"), table_name="companion_relationship_candidates")
    op.drop_index(op.f("ix_companion_relationship_candidates_candidate_slug"), table_name="companion_relationship_candidates")
    op.drop_table("companion_relationship_candidates")
