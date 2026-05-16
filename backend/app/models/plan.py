from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class GardenPlan(Base):
    __tablename__ = "garden_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    garden_id: Mapped[int] = mapped_column(ForeignKey("gardens.id"), index=True)
    summary: Mapped[str] = mapped_column(Text)
    layout_grid: Mapped[dict] = mapped_column(JSON)
    companion_notes: Mapped[list] = mapped_column(JSON, default=list)
    goals: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    garden = relationship("Garden", back_populates="plans")
    items = relationship("PlanItem", back_populates="plan", cascade="all, delete-orphan")


class PlanItem(Base):
    __tablename__ = "plan_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("garden_plans.id"), index=True)
    plant_id: Mapped[int] = mapped_column(ForeignKey("plants.id"))
    label: Mapped[str] = mapped_column(String(120))
    row: Mapped[int] = mapped_column(Integer)
    col: Mapped[int] = mapped_column(Integer)
    width: Mapped[int] = mapped_column(Integer, default=1)
    height: Mapped[int] = mapped_column(Integer, default=1)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    x_pct: Mapped[float] = mapped_column(Float)
    y_pct: Mapped[float] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    plan = relationship("GardenPlan", back_populates="items")
    plant = relationship("Plant")
