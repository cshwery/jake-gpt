from app.services.companions import CompanionGraphService
from app.services.layout.layout_config import NEGATIVE_TYPES, POSITIVE_TYPES
from app.services.layout.layout_schemas import GardenGrid, LayoutPlacementDTO


class LayoutExplanationBuilder:
    def assumptions(self, polygon_approximated: bool = True, uniform_sunlight: bool = True) -> list[str]:
        assumptions: list[str] = []
        if polygon_approximated:
            assumptions.append("The irregular garden boundary is approximated as a rectangular grid for v1.")
        if uniform_sunlight:
            assumptions.append("LayoutEngine v1 assumes sunlight is uniform across all grid cells.")
        assumptions.append("Candidate layouts are deterministic and heuristic-based; no LLM or external API is used.")
        return assumptions

    def explanations(
        self,
        grid: GardenGrid | None = None,
        placements: list[LayoutPlacementDTO] | None = None,
        companion_graph: CompanionGraphService | None = None,
    ) -> list[str]:
        explanations = ["Tall plants are placed toward the north/top edge when possible."]
        if grid and any(cell.is_path for cell in grid.cells):
            explanations.append("A path was added so the center of the garden remains reachable.")
        if placements and companion_graph:
            explanations.extend(self._relationship_explanations(placements, companion_graph))
        return _unique(explanations)

    def _relationship_explanations(self, placements: list[LayoutPlacementDTO], companion_graph: CompanionGraphService) -> list[str]:
        messages: list[str] = []
        for idx, placement in enumerate(placements):
            for other in placements[idx + 1 :]:
                relationship = companion_graph.get_relationship(placement.plant_slug, other.plant_slug) or companion_graph.get_relationship(other.plant_slug, placement.plant_slug)
                if relationship is None:
                    continue
                if relationship.relationship_type in POSITIVE_TYPES and _is_near(placement, other):
                    messages.append(
                        f"{placement.plant_common_name.title()} is placed near {other.plant_common_name.title()} because the companion graph contains a {relationship.relationship_type} relationship."
                    )
                if relationship.relationship_type in NEGATIVE_TYPES:
                    if not _is_near(placement, other):
                        messages.append(
                            f"{placement.plant_common_name.title()} and {other.plant_common_name.title()} are separated because they have a {relationship.relationship_type} relationship."
                        )
                    else:
                        messages.append(
                            f"{placement.plant_common_name.title()} and {other.plant_common_name.title()} could not be fully separated in this grid; review the {relationship.relationship_type} warning."
                        )
        return messages


def _is_near(first: LayoutPlacementDTO, second: LayoutPlacementDTO) -> bool:
    return abs((first.row or 0) - (second.row or 0)) + abs((first.col or 0) - (second.col or 0)) <= 1


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
