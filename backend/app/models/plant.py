from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Plant(Base):
    __tablename__ = "plants"

    id: Mapped[int] = mapped_column(primary_key=True)
    plant_family_id: Mapped[int | None] = mapped_column(ForeignKey("plant_families.id"), nullable=True, index=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=True)
    common_name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    scientific_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    plant_category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    lifecycle: Mapped[str | None] = mapped_column(String(40), nullable=True)
    plant_type: Mapped[str] = mapped_column(String(80))
    edible: Mapped[bool] = mapped_column(Boolean, default=False)
    ornamental: Mapped[bool] = mapped_column(Boolean, default=False)
    is_tree: Mapped[bool] = mapped_column(Boolean, default=False)
    is_shrub: Mapped[bool] = mapped_column(Boolean, default=False)
    is_native_option: Mapped[bool] = mapped_column(Boolean, default=False)
    general_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    flower: Mapped[bool] = mapped_column(Boolean, default=False)
    tree: Mapped[bool] = mapped_column(Boolean, default=False)
    perennial: Mapped[bool] = mapped_column(Boolean, default=False)
    min_zone: Mapped[int] = mapped_column(Integer)
    max_zone: Mapped[int] = mapped_column(Integer)
    min_hardiness_zone: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_hardiness_zone: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sunlight_requirement: Mapped[str] = mapped_column(String(50))
    water_requirement: Mapped[str] = mapped_column(String(50))
    soil_ph_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    soil_ph_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    spacing_inches: Mapped[int] = mapped_column(Integer)
    row_spacing_inches: Mapped[int] = mapped_column(Integer)
    typical_spacing_inches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    typical_row_spacing_inches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    typical_height_inches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    typical_spread_inches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    typical_days_to_maturity_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    typical_days_to_maturity_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    days_to_maturity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frost_tolerance: Mapped[str | None] = mapped_column(String(40), nullable=True)
    direct_sow_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    transplant_recommended: Mapped[bool] = mapped_column(Boolean, default=False)
    beginner_friendliness_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    maintenance_level: Mapped[str] = mapped_column(String(50))
    pollinator_value_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wildlife_value_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    planting_notes: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    companions_from = relationship("PlantCompanion", foreign_keys="PlantCompanion.plant_id", back_populates="plant")
    cultivars = relationship("PlantCultivar", back_populates="plant", cascade="all, delete-orphan")
    family = relationship("PlantFamily", back_populates="plants")


class PlantFamily(Base):
    __tablename__ = "plant_families"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180))
    common_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    plants = relationship("Plant", back_populates="family")


class PlantCompanion(Base):
    __tablename__ = "plant_companions"
    __table_args__ = (UniqueConstraint("plant_id", "companion_plant_id", name="uq_plant_companion_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    plant_id: Mapped[int] = mapped_column(ForeignKey("plants.id"), index=True)
    companion_plant_id: Mapped[int] = mapped_column(ForeignKey("plants.id"), index=True)
    relationship_type: Mapped[str] = mapped_column(String(30))
    notes: Mapped[str] = mapped_column(Text)

    plant = relationship("Plant", foreign_keys=[plant_id], back_populates="companions_from")
    companion = relationship("Plant", foreign_keys=[companion_plant_id])


class PlantCultivar(Base):
    __tablename__ = "plant_cultivars"
    __table_args__ = (UniqueConstraint("plant_id", "slug", name="uq_plant_cultivars_plant_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    plant_id: Mapped[int] = mapped_column(ForeignKey("plants.id"), index=True)
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    cultivar_name: Mapped[str] = mapped_column(String(160))
    normalized_name: Mapped[str] = mapped_column(String(180), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    days_to_maturity_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    days_to_maturity_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_hardiness_zone: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_hardiness_zone: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sunlight_requirement_override: Mapped[str | None] = mapped_column(String(50), nullable=True)
    water_requirement_override: Mapped[str | None] = mapped_column(String(50), nullable=True)
    spacing_inches_override: Mapped[int | None] = mapped_column(Integer, nullable=True)
    row_spacing_inches_override: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_inches_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_inches_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    spread_inches_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    spread_inches_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    flavor_profile: Mapped[str | None] = mapped_column(Text, nullable=True)
    common_uses: Mapped[str | None] = mapped_column(Text, nullable=True)
    disease_resistance: Mapped[str | None] = mapped_column(Text, nullable=True)
    heat_tolerance_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cold_tolerance_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    drought_tolerance_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    container_friendly: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    compact_variety: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    heirloom: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    hybrid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    open_pollinated: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    seed_saving_friendly: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    recommended_regions: Mapped[str | None] = mapped_column(Text, nullable=True)
    avoid_regions: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    plant = relationship("Plant", back_populates="cultivars")


class PlantCompanionRelationship(Base):
    __tablename__ = "plant_companion_relationships"
    __table_args__ = (
        UniqueConstraint(
            "source_plant_id",
            "target_plant_id",
            "source_cultivar_id",
            "target_cultivar_id",
            "relationship_type",
            name="uq_plant_companion_relationship_identity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_plant_id: Mapped[int] = mapped_column(ForeignKey("plants.id"), index=True)
    target_plant_id: Mapped[int] = mapped_column(ForeignKey("plants.id"), index=True)
    source_cultivar_id: Mapped[int | None] = mapped_column(ForeignKey("plant_cultivars.id"), nullable=True, index=True)
    target_cultivar_id: Mapped[int | None] = mapped_column(ForeignKey("plant_cultivars.id"), nullable=True, index=True)
    relationship_type: Mapped[str] = mapped_column(String(40))
    confidence: Mapped[str] = mapped_column(String(20))
    evidence_type: Mapped[str] = mapped_column(String(40))
    rationale: Mapped[str] = mapped_column(Text)
    source_name: Mapped[str] = mapped_column(String(180))
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    relationship_direction: Mapped[str] = mapped_column(String(20))
    min_distance_inches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_distance_inches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CompanionRelationshipCandidate(Base):
    __tablename__ = "companion_relationship_candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_slug: Mapped[str] = mapped_column(String(240), unique=True, index=True)
    source_plant_slug: Mapped[str] = mapped_column(String(160), index=True)
    target_plant_slug: Mapped[str] = mapped_column(String(160), index=True)
    source_cultivar_slug: Mapped[str | None] = mapped_column(String(180), nullable=True)
    target_cultivar_slug: Mapped[str | None] = mapped_column(String(180), nullable=True)
    relationship_type: Mapped[str] = mapped_column(String(40))
    confidence: Mapped[str] = mapped_column(String(20))
    evidence_type: Mapped[str] = mapped_column(String(40))
    rationale: Mapped[str] = mapped_column(Text)
    relationship_direction: Mapped[str] = mapped_column(String(20))
    min_distance_inches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_distance_inches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    generation_rule: Mapped[str | None] = mapped_column(String(160), nullable=True)
    duplicate_of_canonical_relationship_id: Mapped[int | None] = mapped_column(ForeignKey("plant_companion_relationships.id"), nullable=True, index=True)
    canonical_relationship_id: Mapped[int | None] = mapped_column(ForeignKey("plant_companion_relationships.id"), nullable=True, index=True)
    promoted_to_canonical: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    conflict_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_status: Mapped[str] = mapped_column(String(40), default="needs_review", index=True)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(180), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    duplicate_of_canonical = relationship("PlantCompanionRelationship", foreign_keys=[duplicate_of_canonical_relationship_id])
    canonical_relationship = relationship("PlantCompanionRelationship", foreign_keys=[canonical_relationship_id])


class PlantingRule(Base):
    __tablename__ = "planting_rules"
    __table_args__ = (
        UniqueConstraint(
            "plant_id",
            "cultivar_id",
            "rule_type",
            "relative_to",
            "offset_days_min",
            "offset_days_max",
            "min_soil_temp_f",
            name="uq_planting_rule_identity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    plant_id: Mapped[int] = mapped_column(ForeignKey("plants.id"), index=True)
    cultivar_id: Mapped[int | None] = mapped_column(ForeignKey("plant_cultivars.id"), nullable=True, index=True)
    rule_type: Mapped[str] = mapped_column(String(40))
    relative_to: Mapped[str] = mapped_column(String(40))
    offset_days_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    offset_days_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_soil_temp_f: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_soil_temp_f: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlantRegionRule(Base):
    __tablename__ = "plant_region_rules"
    __table_args__ = (
        UniqueConstraint("plant_id", "cultivar_id", "hardiness_zone", "region_name", name="uq_plant_region_rule_identity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    plant_id: Mapped[int] = mapped_column(ForeignKey("plants.id"), index=True)
    cultivar_id: Mapped[int | None] = mapped_column(ForeignKey("plant_cultivars.id"), nullable=True, index=True)
    hardiness_zone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    region_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    recommended_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    recommended_transplant_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    recommended_direct_sow_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    recommended_harvest_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    recommended_harvest_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(40))
    license_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
