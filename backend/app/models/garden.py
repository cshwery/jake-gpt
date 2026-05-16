from datetime import date, datetime

from geoalchemy2 import Geography
from sqlalchemy import Date, DateTime, Float, ForeignKey, JSON, Integer, String
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
