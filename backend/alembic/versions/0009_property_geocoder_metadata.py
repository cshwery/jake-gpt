"""property geocoder metadata

Revision ID: 0009_property_geocoder_metadata
Revises: 0008_persisted_layout_engine
Create Date: 2026-05-18 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_property_geocoder_metadata"
down_revision = "0008_persisted_layout_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("properties", sa.Column("geocoder_provider", sa.String(length=80), nullable=True))
    op.add_column("properties", sa.Column("geocoder_accuracy", sa.String(length=80), nullable=True))
    op.add_column("properties", sa.Column("geocoder_confidence", sa.String(length=80), nullable=True))
    op.add_column("properties", sa.Column("geocoder_bbox", sa.JSON(), nullable=True))
    op.add_column("properties", sa.Column("raw_geocoder_result", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("properties", "raw_geocoder_result")
    op.drop_column("properties", "geocoder_bbox")
    op.drop_column("properties", "geocoder_confidence")
    op.drop_column("properties", "geocoder_accuracy")
    op.drop_column("properties", "geocoder_provider")
