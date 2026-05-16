from app.models import Garden, Plant
from app.schemas.plan import PlanItemRead
from app.services.companions import CompanionGraphService
from app.services.layout.layout_config import MAX_PLANT_QUANTITY, STRONG_NEGATIVE_TYPES


class PlacementPlanner:
    def order_plants(self, plants: list[Plant], companion_graph: CompanionGraphService | None = None) -> tuple[list[Plant], list[str]]:
        ordered = sorted(plants, key=lambda plant: (0 if _is_tall(plant) else 1, plant.common_name))
        warnings: list[str] = []
        if companion_graph is None:
            return ordered, warnings

        ordered = self._bring_beneficial_neighbors_together(ordered, companion_graph)
        ordered, negative_warnings = self._separate_strong_negatives(ordered, companion_graph)
        warnings.extend(negative_warnings)
        return ordered, warnings

    def build_items(self, garden: Garden, plants: list[Plant], rows: int, cols: int) -> list[PlanItemRead]:
        items: list[PlanItemRead] = []
        for idx, plant in enumerate(plants):
            row = idx // cols
            col = idx % cols
            if _is_tall(plant):
                row = 0
            items.append(
                PlanItemRead(
                    plant_id=plant.id,
                    label=plant.common_name.title(),
                    row=row,
                    col=col,
                    quantity=self.estimate_quantity(garden, plant, len(plants)),
                    x_pct=(col + 0.5) / cols * 100,
                    y_pct=(row + 0.5) / rows * 100,
                    notes=f"{plant.spacing_inches} in spacing; {plant.planting_notes}",
                )
            )
        return items

    def estimate_quantity(self, garden: Garden, plant: Plant, plant_count: int) -> int:
        footprint_sq_ft = max(plant.spacing_inches * plant.row_spacing_inches / 144, 1)
        quantity = max(1, int((garden.area_sq_ft / footprint_sq_ft) // max(plant_count, 1)))
        return min(quantity, MAX_PLANT_QUANTITY)

    def _bring_beneficial_neighbors_together(self, plants: list[Plant], companion_graph: CompanionGraphService) -> list[Plant]:
        ordered = list(plants)
        slug_by_id = {plant.id: _plant_slug(plant) for plant in ordered}
        for idx, plant in enumerate(list(ordered)):
            plant_slug = slug_by_id.get(plant.id)
            if not plant_slug:
                continue
            for jdx, other in enumerate(ordered):
                other_slug = slug_by_id.get(other.id)
                if idx <= jdx or not other_slug:
                    continue
                relationship = companion_graph.get_relationship(plant_slug, other_slug)
                if relationship and relationship.relationship_type == "beneficial":
                    ordered.insert(jdx + 1, ordered.pop(idx))
                    break
        return ordered

    def _separate_strong_negatives(self, plants: list[Plant], companion_graph: CompanionGraphService) -> tuple[list[Plant], list[str]]:
        ordered = list(plants)
        warnings: list[str] = []
        for idx in range(len(ordered) - 1):
            current = ordered[idx]
            nxt = ordered[idx + 1]
            current_slug = _plant_slug(current)
            next_slug = _plant_slug(nxt)
            if not current_slug or not next_slug:
                continue
            relationship = companion_graph.get_relationship(current_slug, next_slug)
            if relationship and relationship.relationship_type in STRONG_NEGATIVE_TYPES and relationship.score < 0:
                swap_idx = self._find_safe_swap(ordered, idx, companion_graph)
                if swap_idx is not None:
                    negative_plant = ordered.pop(idx + 1)
                    ordered.append(negative_plant)
                    warnings.append(f"Separated {current.common_name.title()} and {nxt.common_name.title()} due to {relationship.relationship_type}.")
                elif idx > 0:
                    negative_plant = ordered.pop(idx + 1)
                    ordered.insert(0, negative_plant)
                    warnings.append(f"Separated {current.common_name.title()} and {nxt.common_name.title()} due to {relationship.relationship_type}.")
                else:
                    warnings.append(f"{current.common_name.title()} and {nxt.common_name.title()} have a {relationship.relationship_type} relationship; v0 layout could not fully separate them.")
        return ordered, warnings

    def _find_safe_swap(self, plants: list[Plant], idx: int, companion_graph: CompanionGraphService) -> int | None:
        current_slug = _plant_slug(plants[idx])
        if not current_slug:
            return None
        for swap_idx in range(idx + 2, len(plants)):
            candidate_slug = _plant_slug(plants[swap_idx])
            if not candidate_slug:
                continue
            relationship = companion_graph.get_relationship(current_slug, candidate_slug)
            if relationship is None or relationship.relationship_type not in STRONG_NEGATIVE_TYPES:
                return swap_idx
        return None


def _is_tall(plant: Plant) -> bool:
    return bool(getattr(plant, "tree", False) or getattr(plant, "is_tree", False) or (getattr(plant, "typical_height_inches", None) or 0) >= 72)


def _plant_slug(plant: Plant) -> str:
    return getattr(plant, "slug", None) or plant.common_name.lower().replace(" ", "-")
