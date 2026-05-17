from datetime import date, datetime

from geoalchemy2 import Geography
from sqlalchemy import Date, DateTime, Float, ForeignKey, JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Garden(Base):
    __tablename__ = "gardens"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), default="Garden")
    polygon_geojson: Mapped[dict] = mapped_column(JSON)
    polygon = mapped_column(Geography(geometry_type="POLYGON", srid=4326), nullable=False)
    area_sq_m: Mapped[float] = mapped_column(Float)
    area_sq_ft: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    property = relationship("Property", back_populates="gardens")
    context = relationship("GardenContext", back_populates="garden", uselist=False)
    plans = relationship("GardenPlan", back_populates="garden")
    layouts = relationship("GardenLayout", back_populates="garden", cascade="all, delete-orphan")


class GardenContext(Base):
    __tablename__ = "garden_contexts"

    id: Mapped[int] = mapped_column(primary_key=True)
    garden_id: Mapped[int] = mapped_column(ForeignKey("gardens.id"), unique=True, index=True)
    centroid_lat: Mapped[float] = mapped_column(Float)
    centroid_lon: Mapped[float] = mapped_column(Float)
    bbox_min_lat: Mapped[float] = mapped_column(Float)
    bbox_min_lon: Mapped[float] = mapped_column(Float)
    bbox_max_lat: Mapped[float] = mapped_column(Float)
    bbox_max_lon: Mapped[float] = mapped_column(Float)
    area_sq_m: Mapped[float] = mapped_column(Float)
    area_sq_ft: Mapped[float] = mapped_column(Float)
    hardiness_zone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    hardiness_zone_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hardiness_zone_confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)
    estimated_last_frost_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    estimated_first_frost_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    frost_date_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    frost_date_confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)
    growing_season_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expected_annual_precipitation_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_growing_season_precipitation_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    precipitation_category: Mapped[str | None] = mapped_column(String(20), nullable=True)
    precipitation_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    precipitation_confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sunlight_category: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sunlight_estimate_method: Mapped[str | None] = mapped_column(String(40), nullable=True)
    sunlight_confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)
    user_sunlight_override: Mapped[str | None] = mapped_column(String(20), nullable=True)
    assumptions: Mapped[list[str]] = mapped_column(JSON, default=list)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    raw_context: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    garden = relationship("Garden", back_populates="context")


class GardenRecommendationRun(Base):
    __tablename__ = "garden_recommendation_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    garden_id: Mapped[int] = mapped_column(ForeignKey("gardens.id"), index=True)
    input: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    layouts = relationship("GardenLayout", back_populates="recommendation_run")


class GardenLayout(Base):
    __tablename__ = "garden_layouts"

    id: Mapped[int] = mapped_column(primary_key=True)
    garden_id: Mapped[int] = mapped_column(ForeignKey("gardens.id"), index=True)
    garden_plan_id: Mapped[int | None] = mapped_column(ForeignKey("garden_plans.id"), nullable=True, index=True)
    recommendation_run_id: Mapped[int | None] = mapped_column(ForeignKey("garden_recommendation_runs.id"), nullable=True, index=True)
    layout_version: Mapped[str] = mapped_column(String(40), default="v1")
    input: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    score_total: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    explanations: Mapped[list[str]] = mapped_column(JSON, default=list)
    assumptions: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    garden = relationship("Garden", back_populates="layouts")
    garden_plan = relationship("GardenPlan", back_populates="layouts")
    recommendation_run = relationship("GardenRecommendationRun", back_populates="layouts")
    placements = relationship("LayoutPlacement", back_populates="garden_layout", cascade="all, delete-orphan")


class LayoutPlacement(Base):
    __tablename__ = "layout_placements"

    id: Mapped[int] = mapped_column(primary_key=True)
    garden_layout_id: Mapped[int] = mapped_column(ForeignKey("garden_layouts.id"), index=True)
    plant_id: Mapped[int] = mapped_column(ForeignKey("plants.id"), index=True)
    cultivar_id: Mapped[int | None] = mapped_column(ForeignKey("plant_cultivars.id"), nullable=True, index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    grid_cells: Mapped[list[str]] = mapped_column(JSON, default=list)
    row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    col: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width: Mapped[int] = mapped_column(Integer, default=1)
    height: Mapped[int] = mapped_column(Integer, default=1)
    x_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    y_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    spacing_inches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    row_spacing_inches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    placement_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    garden_layout = relationship("GardenLayout", back_populates="placements")
    plant = relationship("Plant")
    cultivar = relationship("PlantCultivar")
