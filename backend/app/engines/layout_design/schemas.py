from typing import Literal

from pydantic import BaseModel, Field


class PlantSymbol(BaseModel):
    symbol: str
    plant_slug: str
    cultivar_slug: str | None = None
    display_name: str
    role: str


class PlacementRule(BaseModel):
    rule_type: Literal["place_near", "keep_apart", "border", "north_edge", "edge_sprawl", "separate_section", "interplant", "isolate"]
    plant_slugs: list[str]
    rationale: str
    priority: Literal["low", "medium", "high"] = "medium"


class DesignedRow(BaseModel):
    row_number: int
    row_label: str
    primary_plants: list[str] = Field(default_factory=list)
    companion_plants: list[str] = Field(default_factory=list)
    border_plants: list[str] = Field(default_factory=list)
    spacing_from_prior_row_inches: int | None = None
    in_row_spacing_inches: int | None = None
    row_role: Literal["primary_crop", "companion", "pollinator_border", "filler", "sprawling_edge", "trellis"] = "primary_crop"
    notes: list[str] = Field(default_factory=list)


class RowBlueprint(BaseModel):
    rows: list[DesignedRow] = Field(default_factory=list)
    row_spacing_notes: list[str] = Field(default_factory=list)
    diagram_label_frequency: int = 1
    north_orientation: str = "North ↑; row 1 is the northern row"
    tree_shrub_symbols: list[str] = Field(default_factory=list)


class DesignedPlanting(BaseModel):
    plant_slug: str
    cultivar_slug: str | None = None
    symbol: str
    quantity: int = 1
    role: str
    approximate_zone: Literal["north_edge", "south_edge", "center", "border", "corner", "interplanted", "separate"] = "center"
    near_plant_slugs: list[str] = Field(default_factory=list)
    keep_away_from_slugs: list[str] = Field(default_factory=list)
    rationale: str


class DesignedBed(BaseModel):
    bed_id: str
    bed_name: str
    length_ft: float
    width_ft: float
    symbol_legend: list[PlantSymbol] = Field(default_factory=list)
    plantings: list[DesignedPlanting] = Field(default_factory=list)
    border_plantings: list[DesignedPlanting] = Field(default_factory=list)
    companion_clusters: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class RaisedBedBlueprint(BaseModel):
    beds: list[DesignedBed] = Field(default_factory=list)
    unplaced_plants: list[str] = Field(default_factory=list)
    tree_shrub_symbols: list[str] = Field(default_factory=list)


class ChaosBlueprint(BaseModel):
    suggested_plant_count_range: str
    easy_direct_sow_plants: list[str] = Field(default_factory=list)
    low_maintenance_plants: list[str] = Field(default_factory=list)
    pollinator_support_plants: list[str] = Field(default_factory=list)
    plants_to_isolate: list[str] = Field(default_factory=list)
    keep_apart_notes: list[str] = Field(default_factory=list)
    scatter_guidance: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class TreeShrubItem(BaseModel):
    symbol: str
    plant_slug: str
    cultivar_slug: str | None = None
    display_name: str
    placement_guidance: str
    warning: str | None = None


class TreeShrubSection(BaseModel):
    items: list[TreeShrubItem] = Field(default_factory=list)


class LayoutBlueprint(BaseModel):
    layout_style: Literal["raised_beds", "rows", "chaos", "grid", "mixed"]
    summary: str
    plant_symbols: list[PlantSymbol] = Field(default_factory=list)
    row_blueprint: RowBlueprint | None = None
    raised_bed_blueprint: RaisedBedBlueprint | None = None
    chaos_blueprint: ChaosBlueprint | None = None
    tree_shrub_section: TreeShrubSection | None = None
    placement_rules: list[PlacementRule] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)

