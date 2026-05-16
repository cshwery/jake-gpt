"""graph aware recommendations

Revision ID: 0007_graph_aware_recommendations
Revises: 0006_garden_context_engine
Create Date: 2026-05-16
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0007_graph_aware_recommendations"
down_revision = "0006_garden_context_engine"
branch_labels = None
depends_on = None


FAMILIES = [
    ("solanaceae", "Solanaceae", "nightshade family", ["tomato", "pepper", "eggplant", "potato"]),
    ("cucurbitaceae", "Cucurbitaceae", "gourd family", ["cucumber", "squash", "pumpkin", "melon", "zucchini"]),
    ("brassicaceae", "Brassicaceae", "mustard family", ["cabbage", "kale", "broccoli", "cauliflower", "radish", "turnip"]),
    ("fabaceae", "Fabaceae", "legume family", ["bean", "beans", "pea", "peas", "clover", "vetch", "hairy_vetch", "crimson_clover"]),
    ("apiaceae", "Apiaceae", "carrot family", ["carrot", "dill", "parsley", "cilantro", "fennel"]),
    ("amaryllidaceae", "Amaryllidaceae", "onion family", ["onion", "garlic", "leek", "chives"]),
    ("asteraceae", "Asteraceae", "daisy family", ["lettuce", "sunflower", "zinnia", "calendula"]),
    ("lamiaceae", "Lamiaceae", "mint family", ["basil", "mint", "thyme", "oregano", "rosemary", "lavender", "sage"]),
    ("rosaceae", "Rosaceae", "rose family", ["apple", "apple_tree", "pear", "strawberry", "raspberry"]),
    ("poaceae", "Poaceae", "grass family", ["corn", "rye", "oats"]),
    ("amaranthaceae", "Amaranthaceae", "amaranth family", ["spinach", "beet", "swiss_chard"]),
]


def upgrade() -> None:
    op.create_table(
        "plant_families",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("common_name", sa.String(180), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_plant_families_slug", "plant_families", ["slug"], unique=True)
    op.add_column("plants", sa.Column("plant_family_id", sa.Integer(), nullable=True))
    op.create_index("ix_plants_plant_family_id", "plants", ["plant_family_id"])
    op.create_foreign_key("fk_plants_plant_family_id", "plants", "plant_families", ["plant_family_id"], ["id"])

    for slug, name, common_name, plant_slugs in FAMILIES:
        op.execute(
            f"""
            INSERT INTO plant_families (slug, name, common_name, notes, created_at, updated_at)
            VALUES ('{slug}', '{name}', '{common_name}', 'Seeded for JakeGPT recommendation family-risk logic.', now(), now())
            """
        )
        quoted_slugs = ", ".join(f"'{plant_slug}'" for plant_slug in plant_slugs)
        op.execute(
            f"""
            UPDATE plants
            SET plant_family_id = (SELECT id FROM plant_families WHERE slug = '{slug}')
            WHERE slug IN ({quoted_slugs})
            """
        )

    op.create_table(
        "garden_recommendation_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("garden_id", sa.Integer(), sa.ForeignKey("gardens.id"), nullable=False),
        sa.Column("input", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_garden_recommendation_runs_garden_id", "garden_recommendation_runs", ["garden_id"])


def downgrade() -> None:
    op.drop_table("garden_recommendation_runs")
    op.drop_constraint("fk_plants_plant_family_id", "plants", type_="foreignkey")
    op.drop_index("ix_plants_plant_family_id", table_name="plants")
    op.drop_column("plants", "plant_family_id")
    op.drop_table("plant_families")
