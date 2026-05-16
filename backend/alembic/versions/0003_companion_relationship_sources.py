"""companion relationship source metadata

Revision ID: 0003_companion_sources
Revises: 0002_plant_knowledge_base
Create Date: 2026-05-11
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_companion_sources"
down_revision = "0002_plant_knowledge_base"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("plant_companion_relationships", sa.Column("evidence_type", sa.String(40), nullable=True))
    op.add_column("plant_companion_relationships", sa.Column("source_name", sa.String(180), nullable=True))
    op.add_column("plant_companion_relationships", sa.Column("source_url", sa.Text(), nullable=True))
    op.execute("UPDATE plant_companion_relationships SET evidence_type = 'manual' WHERE evidence_type IS NULL")
    op.execute("UPDATE plant_companion_relationships SET source_name = 'JakeGPT curated starter plant knowledge' WHERE source_name IS NULL")
    op.alter_column("plant_companion_relationships", "evidence_type", nullable=False)
    op.alter_column("plant_companion_relationships", "source_name", nullable=False)


def downgrade() -> None:
    op.drop_column("plant_companion_relationships", "source_url")
    op.drop_column("plant_companion_relationships", "source_name")
    op.drop_column("plant_companion_relationships", "evidence_type")
