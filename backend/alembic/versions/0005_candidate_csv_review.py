"""candidate csv review promotion tracking

Revision ID: 0005_candidate_csv_review
Revises: 0004_comp_candidate_review
Create Date: 2026-05-11
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_candidate_csv_review"
down_revision = "0004_comp_candidate_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("companion_relationship_candidates", sa.Column("canonical_relationship_id", sa.Integer(), nullable=True))
    op.add_column("companion_relationship_candidates", sa.Column("promoted_to_canonical", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_foreign_key(
        "fk_companion_candidates_canonical_relationship",
        "companion_relationship_candidates",
        "plant_companion_relationships",
        ["canonical_relationship_id"],
        ["id"],
    )
    op.create_index(op.f("ix_companion_relationship_candidates_canonical_relationship_id"), "companion_relationship_candidates", ["canonical_relationship_id"], unique=False)
    op.create_index(op.f("ix_companion_relationship_candidates_promoted_to_canonical"), "companion_relationship_candidates", ["promoted_to_canonical"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_companion_relationship_candidates_promoted_to_canonical"), table_name="companion_relationship_candidates")
    op.drop_index(op.f("ix_companion_relationship_candidates_canonical_relationship_id"), table_name="companion_relationship_candidates")
    op.drop_constraint("fk_companion_candidates_canonical_relationship", "companion_relationship_candidates", type_="foreignkey")
    op.drop_column("companion_relationship_candidates", "promoted_to_canonical")
    op.drop_column("companion_relationship_candidates", "canonical_relationship_id")
