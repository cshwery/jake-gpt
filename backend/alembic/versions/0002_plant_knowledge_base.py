"""plant knowledge base schema

Revision ID: 0002_plant_knowledge_base
Revises: 0001_initial
Create Date: 2026-05-09
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_plant_knowledge_base"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("plants", sa.Column("slug", sa.String(160), nullable=True))
    op.add_column("plants", sa.Column("plant_category", sa.String(40), nullable=True))
    op.add_column("plants", sa.Column("lifecycle", sa.String(40), nullable=True))
    op.add_column("plants", sa.Column("ornamental", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("plants", sa.Column("is_tree", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("plants", sa.Column("is_shrub", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("plants", sa.Column("is_native_option", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("plants", sa.Column("general_description", sa.Text(), nullable=True))
    op.add_column("plants", sa.Column("min_hardiness_zone", sa.Integer(), nullable=True))
    op.add_column("plants", sa.Column("max_hardiness_zone", sa.Integer(), nullable=True))
    op.add_column("plants", sa.Column("soil_ph_min", sa.Float(), nullable=True))
    op.add_column("plants", sa.Column("soil_ph_max", sa.Float(), nullable=True))
    op.add_column("plants", sa.Column("typical_spacing_inches", sa.Integer(), nullable=True))
    op.add_column("plants", sa.Column("typical_row_spacing_inches", sa.Integer(), nullable=True))
    op.add_column("plants", sa.Column("typical_height_inches", sa.Integer(), nullable=True))
    op.add_column("plants", sa.Column("typical_spread_inches", sa.Integer(), nullable=True))
    op.add_column("plants", sa.Column("typical_days_to_maturity_min", sa.Integer(), nullable=True))
    op.add_column("plants", sa.Column("typical_days_to_maturity_max", sa.Integer(), nullable=True))
    op.add_column("plants", sa.Column("frost_tolerance", sa.String(40), nullable=True))
    op.add_column("plants", sa.Column("direct_sow_allowed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("plants", sa.Column("transplant_recommended", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("plants", sa.Column("beginner_friendliness_score", sa.Integer(), nullable=True))
    op.add_column("plants", sa.Column("pollinator_value_score", sa.Integer(), nullable=True))
    op.add_column("plants", sa.Column("wildlife_value_score", sa.Integer(), nullable=True))
    op.add_column("plants", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column("plants", sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.add_column("plants", sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_index("ix_plants_slug", "plants", ["slug"], unique=True)

    op.create_table(
        "plant_cultivars",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plant_id", sa.Integer(), sa.ForeignKey("plants.id"), nullable=False),
        sa.Column("slug", sa.String(180), nullable=False),
        sa.Column("cultivar_name", sa.String(160), nullable=False),
        sa.Column("normalized_name", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("days_to_maturity_min", sa.Integer(), nullable=True),
        sa.Column("days_to_maturity_max", sa.Integer(), nullable=True),
        sa.Column("min_hardiness_zone", sa.Integer(), nullable=True),
        sa.Column("max_hardiness_zone", sa.Integer(), nullable=True),
        sa.Column("sunlight_requirement_override", sa.String(50), nullable=True),
        sa.Column("water_requirement_override", sa.String(50), nullable=True),
        sa.Column("spacing_inches_override", sa.Integer(), nullable=True),
        sa.Column("row_spacing_inches_override", sa.Integer(), nullable=True),
        sa.Column("height_inches_min", sa.Integer(), nullable=True),
        sa.Column("height_inches_max", sa.Integer(), nullable=True),
        sa.Column("spread_inches_min", sa.Integer(), nullable=True),
        sa.Column("spread_inches_max", sa.Integer(), nullable=True),
        sa.Column("flavor_profile", sa.Text(), nullable=True),
        sa.Column("common_uses", sa.Text(), nullable=True),
        sa.Column("disease_resistance", sa.Text(), nullable=True),
        sa.Column("heat_tolerance_score", sa.Integer(), nullable=True),
        sa.Column("cold_tolerance_score", sa.Integer(), nullable=True),
        sa.Column("drought_tolerance_score", sa.Integer(), nullable=True),
        sa.Column("container_friendly", sa.Boolean(), nullable=True),
        sa.Column("compact_variety", sa.Boolean(), nullable=True),
        sa.Column("heirloom", sa.Boolean(), nullable=True),
        sa.Column("hybrid", sa.Boolean(), nullable=True),
        sa.Column("open_pollinated", sa.Boolean(), nullable=True),
        sa.Column("seed_saving_friendly", sa.Boolean(), nullable=True),
        sa.Column("recommended_regions", sa.Text(), nullable=True),
        sa.Column("avoid_regions", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("plant_id", "slug", name="uq_plant_cultivars_plant_slug"),
    )
    op.create_index("ix_plant_cultivars_plant_id", "plant_cultivars", ["plant_id"])
    op.create_index("ix_plant_cultivars_slug", "plant_cultivars", ["slug"], unique=True)
    op.create_index("ix_plant_cultivars_normalized_name", "plant_cultivars", ["normalized_name"])

    op.create_table(
        "plant_companion_relationships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_plant_id", sa.Integer(), sa.ForeignKey("plants.id"), nullable=False),
        sa.Column("target_plant_id", sa.Integer(), sa.ForeignKey("plants.id"), nullable=False),
        sa.Column("source_cultivar_id", sa.Integer(), sa.ForeignKey("plant_cultivars.id"), nullable=True),
        sa.Column("target_cultivar_id", sa.Integer(), sa.ForeignKey("plant_cultivars.id"), nullable=True),
        sa.Column("relationship_type", sa.String(40), nullable=False),
        sa.Column("confidence", sa.String(20), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("relationship_direction", sa.String(20), nullable=False),
        sa.Column("min_distance_inches", sa.Integer(), nullable=True),
        sa.Column("max_distance_inches", sa.Integer(), nullable=True),
        sa.Column("source_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("source_plant_id", "target_plant_id", "source_cultivar_id", "target_cultivar_id", "relationship_type", name="uq_plant_companion_relationship_identity"),
    )
    op.create_index("ix_plant_companion_relationships_source_plant_id", "plant_companion_relationships", ["source_plant_id"])
    op.create_index("ix_plant_companion_relationships_target_plant_id", "plant_companion_relationships", ["target_plant_id"])

    op.create_table(
        "planting_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plant_id", sa.Integer(), sa.ForeignKey("plants.id"), nullable=False),
        sa.Column("cultivar_id", sa.Integer(), sa.ForeignKey("plant_cultivars.id"), nullable=True),
        sa.Column("rule_type", sa.String(40), nullable=False),
        sa.Column("relative_to", sa.String(40), nullable=False),
        sa.Column("offset_days_min", sa.Integer(), nullable=True),
        sa.Column("offset_days_max", sa.Integer(), nullable=True),
        sa.Column("min_soil_temp_f", sa.Integer(), nullable=True),
        sa.Column("max_soil_temp_f", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("plant_id", "cultivar_id", "rule_type", "relative_to", "offset_days_min", "offset_days_max", "min_soil_temp_f", name="uq_planting_rule_identity"),
    )
    op.create_index("ix_planting_rules_plant_id", "planting_rules", ["plant_id"])
    op.create_index("ix_planting_rules_cultivar_id", "planting_rules", ["cultivar_id"])

    op.create_table(
        "plant_region_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plant_id", sa.Integer(), sa.ForeignKey("plants.id"), nullable=False),
        sa.Column("cultivar_id", sa.Integer(), sa.ForeignKey("plant_cultivars.id"), nullable=True),
        sa.Column("hardiness_zone", sa.String(20), nullable=True),
        sa.Column("region_name", sa.String(120), nullable=True),
        sa.Column("recommended_start_date", sa.Date(), nullable=True),
        sa.Column("recommended_transplant_date", sa.Date(), nullable=True),
        sa.Column("recommended_direct_sow_date", sa.Date(), nullable=True),
        sa.Column("recommended_harvest_start", sa.Date(), nullable=True),
        sa.Column("recommended_harvest_end", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("plant_id", "cultivar_id", "hardiness_zone", "region_name", name="uq_plant_region_rule_identity"),
    )
    op.create_index("ix_plant_region_rules_plant_id", "plant_region_rules", ["plant_id"])
    op.create_index("ix_plant_region_rules_cultivar_id", "plant_region_rules", ["cultivar_id"])

    op.create_table(
        "data_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_name", sa.String(180), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("license_notes", sa.Text(), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_data_sources_source_name", "data_sources", ["source_name"], unique=True)


def downgrade() -> None:
    op.drop_table("data_sources")
    op.drop_table("plant_region_rules")
    op.drop_table("planting_rules")
    op.drop_table("plant_companion_relationships")
    op.drop_table("plant_cultivars")
    op.drop_index("ix_plants_slug", table_name="plants")
    for column in [
        "updated_at",
        "created_at",
        "notes",
        "wildlife_value_score",
        "pollinator_value_score",
        "beginner_friendliness_score",
        "transplant_recommended",
        "direct_sow_allowed",
        "frost_tolerance",
        "typical_days_to_maturity_max",
        "typical_days_to_maturity_min",
        "typical_spread_inches",
        "typical_height_inches",
        "typical_row_spacing_inches",
        "typical_spacing_inches",
        "soil_ph_max",
        "soil_ph_min",
        "max_hardiness_zone",
        "min_hardiness_zone",
        "general_description",
        "is_native_option",
        "is_shrub",
        "is_tree",
        "ornamental",
        "lifecycle",
        "plant_category",
        "slug",
    ]:
        op.drop_column("plants", column)
