from app.models import Garden, Plant, PlantCultivar
from app.schemas.plan import PlanItemRead
from app.services.companions import CompanionGraphService
from app.services.layout.layout_config import MAX_PLANT_QUANTITY, NEGATIVE_TYPES, POSITIVE_TYPES, SPACING_DEFAULTS, STRONG_NEGATIVE_TYPES
from app.services.layout.layout_schemas import GardenGrid, GridCell, LayoutPlacementDTO


class PlacementPlanner:
    def order_plants(self, plants: list[Plant], companion_graph: CompanionGraphService | None = None, strategy: str = "baseline") -> tuple[list[Plant], list[str]]:
        ordered = sorted(plants, key=lambda plant: (0 if _is_tall(plant) else 1, plant.common_name))
        warnings: list[str] = []
        if companion_graph is None:
            return ordered, warnings
        if strategy in {"companion_clustered", "border_pollinator"}:
            ordered = self._bring_beneficial_neighbors_together(ordered, companion_graph)
        if strategy in {"conflict_separated", "path_aware", "companion_clustered"}:
            ordered, negative_warnings = self._separate_strong_negatives(ordered, companion_graph)
            warnings.extend(negative_warnings)
        if strategy == "border_pollinator":
            ordered = sorted(ordered, key=lambda plant: (0 if _is_tall(plant) else 2 if _is_pollinator(plant) else 1, plant.common_name))
        return ordered, warnings

    def plan_placements(
        self,
        garden: Garden,
        plants: list[Plant],
        grid: GardenGrid,
        cultivars: list[PlantCultivar] | None = None,
        companion_graph: CompanionGraphService | None = None,
    ) -> tuple[list[LayoutPlacementDTO], list[str]]:
        cultivar_by_plant = {cultivar.plant_id: cultivar for cultivar in cultivars or []}
        available = [cell for cell in grid.cells if cell.available and not cell.is_path]
        placements: list[LayoutPlacementDTO] = []
        warnings: list[str] = []
        occupied: set[str] = set()

        for plant in plants:
            cultivar = cultivar_by_plant.get(plant.id)
            preferred = self._preferred_cells(plant, grid, available)
            cell = self._select_cell(plant, preferred, placements, companion_graph, occupied) or next((item for item in available if item.cell_id not in occupied), None)
            if cell is None:
                warnings.append(f"No open grid cell remained for {plant.common_name.title()}; quantity was reduced to zero.")
                continue
            occupied.add(cell.cell_id)
            spacing, row_spacing = spacing_for(plant, cultivar)
            quantity, quantity_warnings = self.estimate_quantity(garden, plant, len(plants), spacing, row_spacing)
            role = _placement_role(plant, companion_graph)
            cell.plant_slug = _plant_slug(plant)
            cell.cultivar_slug = cultivar.slug if cultivar else None
            cell.label = plant.common_name.title()
            notes = f"{spacing} in spacing; {plant.planting_notes}"
            if cultivar:
                notes = f"{cultivar.cultivar_name}: {notes}"
            warnings.extend(quantity_warnings)
            placement = LayoutPlacementDTO(
                plant_id=plant.id,
                plant_slug=_plant_slug(plant),
                plant_common_name=plant.common_name,
                cultivar_id=cultivar.id if cultivar else None,
                cultivar_slug=cultivar.slug if cultivar else None,
                cultivar_name=cultivar.cultivar_name if cultivar else None,
                quantity=quantity,
                grid_cells=[cell.cell_id],
                row=cell.row,
                col=cell.col,
                x_pct=(cell.col + 0.5) / grid.cols * 100,
                y_pct=(cell.row + 0.5) / grid.rows * 100,
                spacing_inches=spacing,
                row_spacing_inches=row_spacing,
                placement_role=role,
                location_notes=notes,
                warnings=quantity_warnings,
            )
            placements.append(placement)
        return placements, warnings

    def build_items(self, garden: Garden, plants: list[Plant], rows: int, cols: int) -> list[PlanItemRead]:
        grid = GardenGrid(rows=rows, cols=cols, cells=[])
        grid.cells = [
            GridCell(cell_id=f"{row}-{col}", row=row, col=col)
            for row in range(rows)
            for col in range(cols)
        ]
        placements, _ = self.plan_placements(garden, plants, grid)
        return [placement.to_plan_item() for placement in placements]

    def estimate_quantity(self, garden: Garden, plant: Plant, plant_count: int, spacing_inches: int | None = None, row_spacing_inches: int | None = None) -> tuple[int, list[str]]:
        spacing_inches = spacing_inches or plant.spacing_inches
        row_spacing_inches = row_spacing_inches or plant.row_spacing_inches
        footprint_sq_ft = max(spacing_inches * row_spacing_inches / 144, 1)
        raw_quantity = max(1, int((garden.area_sq_ft / footprint_sq_ft) // max(plant_count, 1)))
        quantity = min(raw_quantity, MAX_PLANT_QUANTITY)
        warnings = []
        if raw_quantity > MAX_PLANT_QUANTITY:
            warnings.append(f"{plant.common_name.title()} quantity was capped at {MAX_PLANT_QUANTITY} for a manageable v1 layout.")
        if _is_large_woody(plant) and garden.area_sq_ft < 100:
            warnings.append(f"{plant.common_name.title()} may be too large for a small garden; consider a larger site or compact cultivar.")
            quantity = 1
        return quantity, warnings

    def _preferred_cells(self, plant: Plant, grid: GardenGrid, available: list) -> list:
        if _is_tall(plant):
            return sorted(available, key=lambda cell: (cell.row, cell.col))
        if _is_pollinator(plant):
            return sorted(available, key=lambda cell: (0 if _is_edge(cell, grid) else 1, cell.row, cell.col))
        return sorted(available, key=lambda cell: (cell.row, cell.col))

    def _select_cell(
        self,
        plant: Plant,
        candidates: list,
        placements: list[LayoutPlacementDTO],
        companion_graph: CompanionGraphService | None,
        occupied: set[str],
    ):
        if companion_graph is None or not placements:
            return next((cell for cell in candidates if cell.cell_id not in occupied), None)
        plant_slug = _plant_slug(plant)
        scored = []
        for cell in candidates:
            if cell.cell_id in occupied:
                continue
            score = 0.0
            for placed in placements:
                distance = abs((placed.row or 0) - cell.row) + abs((placed.col or 0) - cell.col)
                relationship = companion_graph.get_relationship(plant_slug, placed.plant_slug) or companion_graph.get_relationship(placed.plant_slug, plant_slug)
                if relationship is None:
                    continue
                if relationship.relationship_type in POSITIVE_TYPES:
                    score += max(0, 4 - distance) * max(relationship.score, 1)
                if relationship.relationship_type in NEGATIVE_TYPES:
                    score += min(0, relationship.score) * max(0, 4 - distance)
            scored.append((score, cell.row, cell.col, cell))
        scored.sort(key=lambda item: (-item[0], item[1], item[2]))
        return scored[0][3] if scored else None

    def _bring_beneficial_neighbors_together(self, plants: list[Plant], companion_graph: CompanionGraphService) -> list[Plant]:
        ordered = list(plants)
        for idx, plant in enumerate(list(ordered)):
            plant_slug = _plant_slug(plant)
            for jdx, other in enumerate(ordered):
                if idx <= jdx:
                    continue
                relationship = companion_graph.get_relationship(plant_slug, _plant_slug(other))
                if relationship and relationship.relationship_type in POSITIVE_TYPES:
                    ordered.insert(jdx + 1, ordered.pop(idx))
                    break
        return ordered

    def _separate_strong_negatives(self, plants: list[Plant], companion_graph: CompanionGraphService) -> tuple[list[Plant], list[str]]:
        ordered = list(plants)
        warnings: list[str] = []
        for idx in range(len(ordered) - 1):
            current = ordered[idx]
            nxt = ordered[idx + 1]
            relationship = companion_graph.get_relationship(_plant_slug(current), _plant_slug(nxt))
            if relationship and relationship.relationship_type in STRONG_NEGATIVE_TYPES and relationship.score < 0:
                negative_plant = ordered.pop(idx + 1)
                ordered.append(negative_plant)
                warnings.append(f"Separated {current.common_name.title()} and {nxt.common_name.title()} due to {relationship.relationship_type}.")
        return ordered, warnings


def spacing_for(plant: Plant, cultivar: PlantCultivar | None = None) -> tuple[int, int]:
    spacing = getattr(cultivar, "spacing_inches_override", None) if cultivar else None
    row_spacing = getattr(cultivar, "row_spacing_inches_override", None) if cultivar else None
    if spacing and row_spacing:
        return spacing, row_spacing
    if getattr(plant, "spacing_inches", None) and getattr(plant, "row_spacing_inches", None):
        return spacing or plant.spacing_inches, row_spacing or plant.row_spacing_inches
    default = SPACING_DEFAULTS[_spacing_category(plant)]
    return spacing or default[0], row_spacing or default[1]


def _spacing_category(plant: Plant) -> str:
    slug = _plant_slug(plant)
    plant_type = (getattr(plant, "plant_type", "") or "").lower()
    if _is_large_woody(plant):
        return "tree" if _is_tall(plant) else "shrub"
    if slug in {"tomato", "pepper", "eggplant", "potato"}:
        return "nightshade"
    if slug in {"cucumber", "zucchini", "squash", "pumpkin", "melon"}:
        return "cucurbit"
    if slug in {"beans", "peas", "bean", "pea"}:
        return "legume"
    if slug in {"corn"}:
        return "corn"
    if "herb" in plant_type or slug in {"basil", "cilantro", "dill", "mint", "lavender", "thyme", "sage", "rosemary"}:
        return "herb"
    if getattr(plant, "flower", False) or getattr(plant, "ornamental", False):
        return "flower"
    if slug in {"lettuce", "spinach", "kale"}:
        return "leafy_greens"
    return "default"


def _is_tall(plant: Plant) -> bool:
    return bool(getattr(plant, "tree", False) or getattr(plant, "is_tree", False) or (getattr(plant, "typical_height_inches", None) or 0) >= 72)


def _is_large_woody(plant: Plant) -> bool:
    return bool(_is_tall(plant) or getattr(plant, "is_shrub", False))


def _is_pollinator(plant: Plant) -> bool:
    return bool(getattr(plant, "flower", False) or (getattr(plant, "pollinator_value_score", None) or 0) >= 7)


def _is_edge(cell, grid: GardenGrid) -> bool:
    return cell.row in {0, grid.rows - 1} or cell.col in {0, grid.cols - 1}


def _placement_role(plant: Plant, companion_graph: CompanionGraphService | None = None):
    if _is_tall(plant):
        return "tree" if getattr(plant, "tree", False) or getattr(plant, "is_tree", False) else "support"
    if getattr(plant, "is_shrub", False):
        return "shrub"
    if _is_pollinator(plant):
        return "pollinator"
    if (getattr(plant, "plant_type", "") or "").lower() in {"herb", "flower"}:
        return "companion"
    return "crop"


def _plant_slug(plant: Plant) -> str:
    return getattr(plant, "slug", None) or plant.common_name.lower().replace(" ", "-")
