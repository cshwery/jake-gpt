from datetime import date, datetime

from geoalchemy2 import Geography
from sqlalchemy import Date, DateTime, Float, ForeignKey, JSON, String, Text
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

    property = relationship("Property", back_populates="gardens")
    context = relationship("GardenContext", back_populates="garden", uselist=False)
    plans = relationship("GardenPlan", back_populates="garden")


class GardenContext(Base):
    __tablename__ = "garden_contexts"

    id: Mapped[int] = mapped_column(primary_key=True)
    garden_id: Mapped[int] = mapped_column(ForeignKey("gardens.id"), unique=True, index=True)
    hardiness_zone: Mapped[str] = mapped_column(String(20))
    last_frost_date: Mapped[date] = mapped_column(Date)
    precipitation_category: Mapped[str] = mapped_column(String(50))
    sunlight_estimate: Mapped[str] = mapped_column(String(50))
    source: Mapped[str] = mapped_column(String(100), default="mock")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    garden = relationship("Garden", back_populates="context")
