from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.plan import PlanItemRead


PlacementRole = Literal["crop", "companion", "pollinator", "border", "path", "support", "tree", "shrub"]


class LayoutOptions(BaseModel):
    cell_size_ft: float = 2
    include_paths: bool = True
    layout_style: Literal["grid", "rows", "raised_beds", "intensive_grid", "mixed", "chaos"] = "grid"
    max_candidates: int = 10
    persist: bool = True
    using_raised_beds: bool | None = None
    raised_beds: dict[str, Any] | None = None


class LayoutGenerateRequest(BaseModel):
    recommendation_run_id: int | None = None
    selected_plant_slugs: list[str] = Field(default_factory=list)
    selected_cultivar_slugs: list[str] = Field(default_factory=list)
    accepted_recommendation_slugs: list[str] = Field(default_factory=list)
    accepted_cultivar_slugs: list[str] = Field(default_factory=list)
    options: LayoutOptions = Field(default_factory=LayoutOptions)


class GridCell(BaseModel):
    cell_id: str
    row: int
    col: int
    available: bool = True
    is_path: bool = False
    plant_slug: str | None = None
    cultivar_slug: str | None = None
    label: str | None = None
    placement_role: PlacementRole | None = None
    group_id: str | None = None
    group_label: str | None = None
    notes: list[str] = Field(default_factory=list)


class GardenGrid(BaseModel):
    rows: int
    cols: int
    cell_size_ft: float = 2
    orientation: str = "north_up"
    layout_style: str = "grid"
    layout_metadata: dict[str, Any] = Field(default_factory=dict)
    cells: list[GridCell] = Field(default_factory=list)
    access_paths: list[str] = Field(default_factory=list)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)


class LayoutPlacementDTO(BaseModel):
    plant_slug: str
    plant_common_name: str
    plant_id: int | None = None
    cultivar_slug: str | None = None
    cultivar_name: str | None = None
    cultivar_id: int | None = None
    quantity: int = 1
    grid_cells: list[str] = Field(default_factory=list)
    row: int | None = None
    col: int | None = None
    width: int = 1
    height: int = 1
    x_pct: float | None = None
    y_pct: float | None = None
    spacing_inches: int | None = None
    row_spacing_inches: int | None = None
    placement_role: PlacementRole | None = None
    location_notes: str | None = None
    warnings: list[str] = Field(default_factory=list)

    def to_plan_item(self) -> PlanItemRead:
        return PlanItemRead(
            plant_id=self.plant_id or 0,
            label=self.plant_common_name.title(),
            row=self.row or 0,
            col=self.col or 0,
            width=self.width,
            height=self.height,
            quantity=self.quantity,
            x_pct=self.x_pct or 0,
            y_pct=self.y_pct or 0,
            notes=self.location_notes,
        )


class LayoutPathDTO(BaseModel):
    path_id: str
    grid_cells: list[str]
    width_ft: float
    notes: str | None = None


class LayoutScoreBreakdown(BaseModel):
    spacing_score: float = 0
    companion_score: float = 0
    conflict_score: float = 0
    access_score: float = 0
    sunlight_score: float = 0
    size_fit_score: float = 0
    diversity_score: float = 0
    total_score: float = 0

    def __getitem__(self, key: str) -> float:
        return getattr(self, key)


class LayoutCandidate(BaseModel):
    name: str
    grid: GardenGrid
    placements: list[LayoutPlacementDTO]
    paths: list[LayoutPathDTO] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    explanations: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    score_breakdown: LayoutScoreBreakdown = Field(default_factory=LayoutScoreBreakdown)


class LayoutResult(BaseModel):
    layout_id: int | None = None
    garden_id: int | None = None
    garden_plan_id: int | None = None
    recommendation_run_id: int | None = None
    summary: str = "Deterministic JakeGPT layout."
    area_sq_ft: float | None = None
    area_category: str | None = None
    approximate_dimensions_ft: dict[str, float] | None = None
    grid: GardenGrid
    placements: list[LayoutPlacementDTO]
    paths: list[LayoutPathDTO] = Field(default_factory=list)
    score_breakdown: LayoutScoreBreakdown = Field(default_factory=LayoutScoreBreakdown)
    warnings: list[str] = Field(default_factory=list)
    explanations: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _legacy_layout_shape(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "layout_grid" not in data:
            return data
        layout_grid = data.get("layout_grid") or {}
        items = data.get("items") or []
        rows = layout_grid.get("rows", 1)
        cols = layout_grid.get("cols", 1)
        cells = [
            GridCell(cell_id=f"{chr(ord('A') + col)}{row + 1}", row=row, col=col)
            for row in range(rows)
            for col in range(cols)
        ]
        placements = []
        for item in items:
            item_data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
            row = item_data.get("row", 0)
            col = item_data.get("col", 0)
            placements.append(
                LayoutPlacementDTO(
                    plant_id=item_data.get("plant_id"),
                    plant_slug=item_data.get("label", "").lower().replace(" ", "-"),
                    plant_common_name=item_data.get("label", ""),
                    quantity=item_data.get("quantity", 1),
                    grid_cells=[f"{chr(ord('A') + col)}{row + 1}"],
                    row=row,
                    col=col,
                    width=item_data.get("width", 1),
                    height=item_data.get("height", 1),
                    x_pct=item_data.get("x_pct"),
                    y_pct=item_data.get("y_pct"),
                    location_notes=item_data.get("notes"),
                )
            )
        data = dict(data)
        data["grid"] = GardenGrid(
            rows=rows,
            cols=cols,
            cell_size_ft=layout_grid.get("cell_size_ft", 2),
            cells=cells,
            access_paths=layout_grid.get("access_paths", []),
        )
        data["placements"] = placements
        return data

    @property
    def layout_grid(self) -> dict[str, Any]:
        return {
            "rows": self.grid.rows,
            "cols": self.grid.cols,
            "cell_size_ft": self.grid.cell_size_ft,
            "orientation": self.grid.orientation,
            "layout_style": self.grid.layout_style,
            "layout_metadata": self.grid.layout_metadata,
            "cells": [cell.model_dump(mode="json") for cell in self.grid.cells],
            "access_paths": self.grid.access_paths,
        }

    @property
    def items(self) -> list[PlanItemRead]:
        return [placement.to_plan_item() for placement in self.placements]
