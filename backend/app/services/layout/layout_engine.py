from typing import Any

from sqlalchemy.orm import Session

from app.models import Garden, GardenContext, GardenLayout, LayoutPlacement, Plant, PlantCultivar
from app.engines.planting_design import PlantingDesignService
from app.engines.planting_design.schemas import PlantingDesignPlan
from app.services.companions import CompanionGraphService
from app.services.garden_recommendations import GardenRecommendationResult
from app.services.garden_area import area_category
from app.services.layout.grid_builder import GridBuilder
from app.services.layout.layout_explanation_builder import LayoutExplanationBuilder
from app.services.layout.layout_schemas import LayoutCandidate, LayoutOptions, LayoutResult, LayoutScoreBreakdown
from app.services.layout.layout_scorer import LayoutScorer
from app.services.layout.placement_planner import PlacementPlanner


class LayoutEngine:
    def __init__(
        self,
        grid_builder: GridBuilder | None = None,
        placement_planner: PlacementPlanner | None = None,
        layout_scorer: LayoutScorer | None = None,
        explanation_builder: LayoutExplanationBuilder | None = None,
    ) -> None:
        self.grid_builder = grid_builder or GridBuilder()
        self.placement_planner = placement_planner or PlacementPlanner()
        self.layout_scorer = layout_scorer or LayoutScorer()
        self.explanation_builder = explanation_builder or LayoutExplanationBuilder()

    def generate_layout(
        self,
        garden: Garden,
        plants: list[Plant],
        garden_context: GardenContext | Any | None = None,
        cultivars: list[PlantCultivar] | None = None,
        companion_graph: CompanionGraphService | None = None,
        recommendation_result: GardenRecommendationResult | None = None,
        options: LayoutOptions | None = None,
        design_plan: PlantingDesignPlan | None = None,
    ) -> LayoutResult:
        effective_options = options or LayoutOptions()
        design_plan = design_plan or PlantingDesignService().create_design_plan(
            garden_context=garden_context,
            plants=plants,
            cultivars=cultivars or [],
            companion_graph=companion_graph,
            garden_goals=None,
            recommendation_result=recommendation_result,
            organization_style="raised_beds" if effective_options.using_raised_beds else effective_options.layout_style,
        )
        candidates = self.generate_candidate_layouts(
            garden=garden,
            garden_context=garden_context,
            plants=plants,
            cultivars=cultivars,
            companion_graph=companion_graph,
            recommendation_result=recommendation_result,
            options=options,
            design_plan=design_plan,
        )
        return self.select_best_layout(candidates, garden=garden, garden_context=garden_context, design_plan=design_plan)

    def generate_candidate_layouts(
        self,
        garden: Garden,
        plants: list[Plant],
        garden_context: GardenContext | Any | None = None,
        cultivars: list[PlantCultivar] | None = None,
        companion_graph: CompanionGraphService | None = None,
        recommendation_result: GardenRecommendationResult | None = None,
        options: LayoutOptions | None = None,
        design_plan: PlantingDesignPlan | None = None,
    ) -> list[LayoutCandidate]:
        legacy_grid = garden_context is None and options is None
        options = options or LayoutOptions()
        strategies = ["baseline", "companion_clustered", "conflict_separated", "border_pollinator", "path_aware"][: max(1, options.max_candidates)]
        candidates: list[LayoutCandidate] = []
        for strategy in strategies:
            ordered, ordering_warnings = self.placement_planner.order_plants(plants, companion_graph, strategy=strategy)
            ordered = _apply_design_order(ordered, design_plan)
            grid = self.grid_builder.build_grid(
                len(ordered),
                garden=None if legacy_grid else garden,
                garden_context=garden_context,
                options=options,
            )
            placements, placement_warnings = self.placement_planner.plan_placements(garden, ordered, grid, cultivars=cultivars, companion_graph=companion_graph)
            paths = self.grid_builder.paths_for_grid(grid)
            warnings = _unique([*ordering_warnings, *placement_warnings, *(design_plan.warnings if design_plan else []), *self._sunlight_warnings(ordered, garden_context)])
            score = self.score_layout(
                LayoutCandidate(name=strategy, grid=grid, placements=placements, paths=paths, warnings=warnings),
                plants=ordered,
                companion_graph=companion_graph,
                garden_context=garden_context,
            )
            explanations = _unique([*self.explanation_builder.explanations(grid, placements, companion_graph), *_design_explanations(design_plan)])
            assumptions = _unique([*self.explanation_builder.assumptions(), *(design_plan.assumptions if design_plan else [])])
            candidates.append(
                LayoutCandidate(
                    name=strategy,
                    grid=grid,
                    placements=placements,
                    paths=paths,
                    warnings=warnings,
                    explanations=explanations,
                    assumptions=assumptions,
                    score_breakdown=score,
                )
            )
        return candidates

    def score_layout(
        self,
        candidate: LayoutCandidate,
        plants: list[Plant] | None = None,
        companion_graph: CompanionGraphService | None = None,
        garden_context: GardenContext | Any | None = None,
    ) -> LayoutScoreBreakdown:
        return self.layout_scorer.score(
            plants or [],
            candidate.warnings,
            grid=candidate.grid,
            placements=candidate.placements,
            companion_graph=companion_graph,
            garden_context=garden_context,
        )

    def select_best_layout(
        self,
        candidates: list[LayoutCandidate],
        garden: Garden | None = None,
        garden_id: int | None = None,
        garden_context: GardenContext | Any | None = None,
        design_plan: PlantingDesignPlan | None = None,
    ) -> LayoutResult:
        if not candidates:
            raise ValueError("At least one layout candidate is required.")
        best = sorted(candidates, key=lambda candidate: (-candidate.score_breakdown.total_score, candidate.name))[0]
        if best.grid.layout_style == "chaos":
            best.grid.layout_metadata.update(_chaos_metadata(best.placements, best.warnings))
        area_sq_ft = _area_sq_ft(garden, garden_context)
        grid_area_sq_ft = (best.grid.rows * best.grid.cols) * (best.grid.cell_size_ft ** 2)
        return LayoutResult(
            garden_id=garden_id or getattr(garden, "id", None),
            summary=_layout_summary(best, best.score_breakdown.total_score),
            area_sq_ft=area_sq_ft or None,
            area_category=area_category(area_sq_ft) if area_sq_ft else None,
            approximate_dimensions_ft={"width": round(best.grid.cols * best.grid.cell_size_ft, 1), "height": round(best.grid.rows * best.grid.cell_size_ft, 1), "grid_area_sq_ft": round(grid_area_sq_ft, 1)},
            grid=best.grid,
            placements=best.placements,
            paths=best.paths,
            score_breakdown=best.score_breakdown,
            design_plan=design_plan,
            warnings=best.warnings,
            explanations=best.explanations,
            assumptions=best.assumptions,
        )

    def persist_layout(
        self,
        layout_result: LayoutResult,
        db: Session,
        *,
        garden: Garden | None = None,
        garden_plan_id: int | None = None,
        recommendation_run_id: int | None = None,
        input_payload: dict | None = None,
    ) -> GardenLayout:
        garden_id = garden.id if garden is not None else layout_result.garden_id
        if garden_id is None:
            raise ValueError("Cannot persist a layout without a garden_id.")
        persisted = GardenLayout(
            garden_id=garden_id,
            garden_plan_id=garden_plan_id or layout_result.garden_plan_id,
            recommendation_run_id=recommendation_run_id or layout_result.recommendation_run_id,
            layout_version="v1",
            input=input_payload or {},
            result=layout_result.model_dump(mode="json"),
            score_total=layout_result.score_breakdown.total_score,
            score_breakdown=layout_result.score_breakdown.model_dump(mode="json"),
            warnings=layout_result.warnings,
            explanations=layout_result.explanations,
            assumptions=layout_result.assumptions,
        )
        db.add(persisted)
        db.flush()
        for placement in layout_result.placements:
            if placement.plant_id is None:
                continue
            db.add(
                LayoutPlacement(
                    garden_layout_id=persisted.id,
                    plant_id=placement.plant_id,
                    cultivar_id=placement.cultivar_id,
                    quantity=placement.quantity,
                    grid_cells=placement.grid_cells,
                    row=placement.row,
                    col=placement.col,
                    width=placement.width,
                    height=placement.height,
                    x_pct=placement.x_pct,
                    y_pct=placement.y_pct,
                    spacing_inches=placement.spacing_inches,
                    row_spacing_inches=placement.row_spacing_inches,
                    placement_role=placement.placement_role,
                    notes=placement.location_notes,
                    warnings=placement.warnings,
                )
            )
        db.flush()
        layout_result.layout_id = persisted.id
        persisted.result = layout_result.model_dump(mode="json")
        return persisted

    def _sunlight_warnings(self, plants: list[Plant], garden_context: GardenContext | Any | None) -> list[str]:
        sunlight = _sunlight(garden_context)
        if sunlight not in {"shade", "part_shade"}:
            return []
        warnings: list[str] = []
        for plant in plants:
            requirement = (getattr(plant, "sunlight_requirement", "") or "").lower()
            if "full" in requirement:
                warnings.append(f"{plant.common_name.title()} prefers full sun; this layout uses a {sunlight.replace('_', ' ')} garden context.")
        return warnings


def _sunlight(garden_context: GardenContext | Any | None) -> str | None:
    if garden_context is None:
        return None
    if hasattr(garden_context, "sunlight_category"):
        return garden_context.sunlight_category
    sunlight = getattr(garden_context, "sunlight", None)
    if sunlight is not None:
        return getattr(sunlight, "category", None)
    if isinstance(garden_context, dict):
        return garden_context.get("sunlight", {}).get("category") or garden_context.get("sunlight_category")
    return None


def _area_sq_ft(garden: Garden | None, garden_context: GardenContext | Any | None) -> float:
    if garden_context is not None:
        if hasattr(garden_context, "area_sq_ft"):
            return float(getattr(garden_context, "area_sq_ft", 0) or 0)
        geometry = getattr(garden_context, "geometry", None)
        if geometry is not None:
            return float(getattr(geometry, "area_sq_ft", 0) or 0)
        if isinstance(garden_context, dict):
            return float(garden_context.get("geometry", {}).get("area_sq_ft", 0) or garden_context.get("area_sq_ft", 0) or 0)
    return float(getattr(garden, "area_sq_ft", 0) or 0)


def _chaos_metadata(placements, warnings: list[str]) -> dict[str, Any]:
    groups = {
        "easy_direct_sow_crops": [],
        "pollinator_support_flowers": [],
        "herbs": [],
        "larger_sprawling_crops": [],
        "avoid_or_separate": [],
    }
    for placement in placements:
        name = placement.cultivar_name or placement.plant_common_name.title()
        spacing = placement.row_spacing_inches or placement.spacing_inches or 0
        if placement.placement_role in {"tree", "shrub"}:
            groups["avoid_or_separate"].append(name)
        elif placement.placement_role == "pollinator":
            groups["pollinator_support_flowers"].append(name)
        elif placement.placement_role == "companion" and "herb" in (placement.location_notes or "").lower():
            groups["herbs"].append(name)
        elif spacing >= 48:
            groups["larger_sprawling_crops"].append(name)
        else:
            groups["easy_direct_sow_crops"].append(name)
    return {
        "plant_groups": groups,
        "separation_warnings": warnings,
        "guidance": [
            "Scatter seed in small clusters instead of rows or a grid.",
            "Keep taller plants toward the north edge when practical.",
            "Use flowers and herbs around borders and between crop clusters.",
            "Separate plants with pest, disease, or size warnings instead of clustering them together.",
        ],
    }


def _apply_design_order(plants: list[Plant], design_plan: PlantingDesignPlan | None) -> list[Plant]:
    if design_plan is None:
        return plants
    role_priority = {
        "tree": 0,
        "shrub": 0,
        "tall_crop": 1,
        "trellised_crop": 2,
        "primary_crop": 3,
        "companion_herb": 4,
        "leafy_green": 5,
        "root_crop": 6,
        "sprawling_crop": 7,
        "pollinator_flower": 8,
        "border_plant": 8,
    }
    roles_by_slug: dict[str, set[str]] = {}
    for role in design_plan.plant_roles:
        roles_by_slug.setdefault(role.plant_slug, set()).add(role.role)
    return sorted(
        plants,
        key=lambda plant: (
            min([role_priority.get(role, 9) for role in roles_by_slug.get(getattr(plant, "slug", ""), set())] or [9]),
            getattr(plant, "common_name", ""),
        ),
    )


def _design_explanations(design_plan: PlantingDesignPlan | None) -> list[str]:
    if design_plan is None:
        return []
    messages = [design_plan.summary]
    messages.extend(cluster.placement_guidance for cluster in design_plan.companion_clusters[:4])
    messages.extend(design_plan.placement_guidance.rows_guidance[:3])
    messages.extend(design_plan.placement_guidance.raised_beds_guidance[:3])
    messages.extend(design_plan.placement_guidance.chaos_guidance[:3])
    messages.extend(design_plan.placement_guidance.border_guidance[:2])
    messages.extend(design_plan.placement_guidance.north_south_guidance[:2])
    return messages


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _layout_summary(candidate: LayoutCandidate, score: float) -> str:
    if candidate.grid.layout_style == "chaos":
        return f"Chaos Garden Guidance gives you a loose planting strategy instead of a precise map. Selected {candidate.name.replace('_', ' ')} with layout quality {score:.1f}."
    if candidate.grid.layout_style == "raised_beds":
        return f"Raised-bed layout mixes selected plants across beds for density and companion relationships. Selected {candidate.name.replace('_', ' ')} with layout quality {score:.1f}."
    if candidate.grid.layout_style == "rows":
        return f"Row layout places each crop in a horizontal planting row rather than a square grid. Selected {candidate.name.replace('_', ' ')} with layout quality {score:.1f}."
    return f"Grid layout selected the {candidate.name.replace('_', ' ')} candidate with layout quality {score:.1f}."
