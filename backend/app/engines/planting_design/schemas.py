from typing import Literal

from pydantic import BaseModel, Field


OrganizationStyle = Literal["raised_beds", "rows", "chaos", "intensive_grid", "mixed", "grid"]
PlantDesignRole = Literal[
    "primary_crop",
    "companion_herb",
    "pollinator_flower",
    "border_plant",
    "filler_crop",
    "trellised_crop",
    "tall_crop",
    "sprawling_crop",
    "root_crop",
    "leafy_green",
    "perennial",
    "tree",
    "shrub",
    "cover_crop",
    "avoid_or_isolate",
]
PlantGroupType = Literal[
    "companion_cluster",
    "pollinator_border",
    "trellis_row",
    "leafy_green_patch",
    "root_crop_row",
    "sprawling_edge",
    "tree_shrub_zone",
    "filler_group",
    "chaos_mix",
]
SeparationSeverity = Literal["low", "medium", "high"]
SeparationGuidance = Literal["keep_far_apart", "do_not_cluster", "isolate", "containerize", "warn_only"]


class PlantRole(BaseModel):
    plant_slug: str
    cultivar_slug: str | None = None
    role: PlantDesignRole
    rationale: str


class PlantGroup(BaseModel):
    group_id: str
    group_type: PlantGroupType
    primary_plants: list[str] = Field(default_factory=list)
    support_plants: list[str] = Field(default_factory=list)
    placement_strategy: str
    notes: list[str] = Field(default_factory=list)


class CompanionCluster(BaseModel):
    cluster_id: str
    anchor_plant_slug: str
    companion_plant_slugs: list[str] = Field(default_factory=list)
    border_plant_slugs: list[str] = Field(default_factory=list)
    filler_plant_slugs: list[str] = Field(default_factory=list)
    rationale: str
    placement_guidance: str


class SeparationRule(BaseModel):
    plant_slugs: list[str]
    relationship_type: str
    severity: SeparationSeverity
    placement_guidance: SeparationGuidance
    rationale: str


class PlacementGuidance(BaseModel):
    rows_guidance: list[str] = Field(default_factory=list)
    raised_beds_guidance: list[str] = Field(default_factory=list)
    chaos_guidance: list[str] = Field(default_factory=list)
    north_south_guidance: list[str] = Field(default_factory=list)
    border_guidance: list[str] = Field(default_factory=list)
    spacing_guidance: list[str] = Field(default_factory=list)


class PlantingDesignPlan(BaseModel):
    organization_style: OrganizationStyle = "rows"
    summary: str
    plant_roles: list[PlantRole] = Field(default_factory=list)
    plant_groups: list[PlantGroup] = Field(default_factory=list)
    companion_clusters: list[CompanionCluster] = Field(default_factory=list)
    pollinator_border: list[str] = Field(default_factory=list)
    separation_rules: list[SeparationRule] = Field(default_factory=list)
    placement_guidance: PlacementGuidance = Field(default_factory=PlacementGuidance)
    warnings: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)

