from typing import Any

from app.models import Plant
from app.services.companions import CompanionGraphService
from app.services.layout.layout_config import NEGATIVE_TYPES, POSITIVE_TYPES, SCORE_WEIGHTS, STRONG_NEGATIVE_TYPES
from app.services.layout.layout_schemas import GardenGrid, LayoutPlacementDTO, LayoutScoreBreakdown


class LayoutScorer:
    def score(
        self,
        plants: list[Plant],
        warnings: list[str],
        grid: GardenGrid | None = None,
        placements: list[LayoutPlacementDTO] | None = None,
        companion_graph: CompanionGraphService | None = None,
        garden_context: Any | None = None,
    ) -> LayoutScoreBreakdown:
        placements = placements or []
        grid = grid or GardenGrid(rows=1, cols=1, cells=[])
        spacing_score = self._spacing_score(placements, warnings)
        companion_score, conflict_score = self._relationship_scores(placements, companion_graph)
        access_score = self._access_score(grid)
        sunlight_score = self._sunlight_score(plants, garden_context)
        size_fit_score = self._size_fit_score(plants, warnings)
        diversity_score = self._diversity_score(plants)
        total = (
            spacing_score * SCORE_WEIGHTS["spacing"]
            + companion_score * SCORE_WEIGHTS["companion"]
            + conflict_score * SCORE_WEIGHTS["conflict"]
            + access_score * SCORE_WEIGHTS["access"]
            + sunlight_score * SCORE_WEIGHTS["sunlight"]
            + size_fit_score * SCORE_WEIGHTS["size_fit"]
            + diversity_score * SCORE_WEIGHTS["diversity"]
        )
        total_weight = sum(SCORE_WEIGHTS.values())
        return LayoutScoreBreakdown(
            spacing_score=round(spacing_score, 3),
            companion_score=round(companion_score, 3),
            conflict_score=round(conflict_score, 3),
            access_score=round(access_score, 3),
            sunlight_score=round(sunlight_score, 3),
            size_fit_score=round(size_fit_score, 3),
            diversity_score=round(diversity_score, 3),
            total_score=round(total / total_weight, 3),
        )

    def _spacing_score(self, placements: list[LayoutPlacementDTO], warnings: list[str]) -> float:
        score = 85.0
        score -= len([warning for warning in warnings if "capped" in warning.lower() or "too large" in warning.lower()]) * 8
        occupied = [cell for placement in placements for cell in placement.grid_cells]
        score -= max(0, len(occupied) - len(set(occupied))) * 20
        return _bounded(score)

    def _relationship_scores(self, placements: list[LayoutPlacementDTO], companion_graph: CompanionGraphService | None) -> tuple[float, float]:
        if companion_graph is None:
            return 0.0, 0.0
        companion_score = 60.0
        conflict_score = 85.0
        for idx, placement in enumerate(placements):
            for other in placements[idx + 1 :]:
                relationship = companion_graph.get_relationship(placement.plant_slug, other.plant_slug) or companion_graph.get_relationship(other.plant_slug, placement.plant_slug)
                if relationship is None:
                    continue
                distance = _distance(placement, other)
                near_multiplier = max(0, 4 - distance)
                if relationship.relationship_type in POSITIVE_TYPES:
                    companion_score += max(relationship.score, 1) * near_multiplier
                if relationship.relationship_type in NEGATIVE_TYPES:
                    conflict_score += min(relationship.score, -1) * near_multiplier
                    if relationship.relationship_type in STRONG_NEGATIVE_TYPES and distance > 1:
                        conflict_score += 12
        return _bounded(companion_score), _bounded(conflict_score)

    def _access_score(self, grid: GardenGrid) -> float:
        path_count = len([cell for cell in grid.cells if cell.is_path])
        if grid.layout_style in {"rows", "chaos"}:
            return 80
        if grid.rows * grid.cols < 24:
            return 75
        return 90 if path_count else 45

    def _sunlight_score(self, plants: list[Plant], garden_context: Any | None) -> float:
        sunlight = _sunlight(garden_context)
        if sunlight in {None, "unknown"}:
            return 0
        score = 75.0
        for plant in plants:
            requirement = (getattr(plant, "sunlight_requirement", "") or "").lower()
            if sunlight in {"shade", "part_shade"} and "full" in requirement:
                score -= 25
            elif sunlight == "full_sun" and ("full" in requirement or "sun" in requirement):
                score += 5
        return _bounded(score)

    def _size_fit_score(self, plants: list[Plant], warnings: list[str]) -> float:
        score = 85.0
        score -= len([warning for warning in warnings if "too large" in warning.lower()]) * 25
        return _bounded(score)

    def _diversity_score(self, plants: list[Plant]) -> float:
        buckets = set()
        for plant in plants:
            if getattr(plant, "edible", False):
                buckets.add("food")
            if getattr(plant, "flower", False) or getattr(plant, "ornamental", False):
                buckets.add("flower")
            if (getattr(plant, "plant_type", "") or "").lower() == "herb":
                buckets.add("herb")
            if getattr(plant, "is_tree", False) or getattr(plant, "tree", False):
                buckets.add("tree")
        return _bounded(min(len(buckets) * 22, 88))


def _distance(first: LayoutPlacementDTO, second: LayoutPlacementDTO) -> int:
    return abs((first.row or 0) - (second.row or 0)) + abs((first.col or 0) - (second.col or 0))


def _sunlight(garden_context: Any | None) -> str | None:
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


def _bounded(score: float) -> float:
    return max(0.0, min(100.0, score))
