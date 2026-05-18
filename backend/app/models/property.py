from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    address_raw: Mapped[str] = mapped_column(String(500))
    normalized_address: Mapped[str] = mapped_column(String(500))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    geocoder_provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    geocoder_accuracy: Mapped[str | None] = mapped_column(String(80), nullable=True)
    geocoder_confidence: Mapped[str | None] = mapped_column(String(80), nullable=True)
    geocoder_bbox: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    raw_geocoder_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    point = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="properties")
    gardens = relationship("Garden", back_populates="property")
