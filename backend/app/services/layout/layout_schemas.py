from dataclasses import dataclass, field
from typing import Any

from app.schemas.plan import PlanItemRead


@dataclass(frozen=True)
class LayoutResult:
    layout_grid: dict[str, Any]
    items: list[PlanItemRead]
    score_breakdown: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    explanations: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
