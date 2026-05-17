import math
from typing import Any

from app.models import Garden, GardenContext
from app.services.layout.layout_config import DEFAULT_ACCESS_PATHS, DEFAULT_CELL_SIZE_FT, DEFAULT_GRID_COLUMNS, MIN_GRID_ROWS
from app.services.layout.layout_schemas import GardenGrid, GridCell, LayoutOptions, LayoutPathDTO


class GridBuilder:
    def build_grid(
        self,
        plant_count: int,
        columns: int = DEFAULT_GRID_COLUMNS,
        garden: Garden | None = None,
        garden_context: GardenContext | Any | None = None,
        options: LayoutOptions | None = None,
    ) -> GardenGrid:
        options = options or LayoutOptions()
        area_sq_ft = _area_sq_ft(garden, garden_context)
        cell_size_ft = options.cell_size_ft or DEFAULT_CELL_SIZE_FT
        if garden is None and garden_context is None:
            rows = max(MIN_GRID_ROWS, (plant_count + columns - 1) // columns + 1)
            cols = columns
        else:
            rows, cols = self._dimensions(area_sq_ft, plant_count, cell_size_ft)

        path_cells: set[tuple[int, int]] = set()
        access_paths: list[str] = []
        paths: list[LayoutPathDTO] = []
        if options.include_paths and self._should_include_path(area_sq_ft, rows, cols):
            path_col = max(1, cols // 2)
            for row in range(rows):
                path_cells.add((row, path_col))
            access_paths = [f"vertical path through column {_column_label(path_col)}"]
            paths.append(
                LayoutPathDTO(
                    path_id="main-access",
                    grid_cells=[_cell_id(row, path_col) for row in range(rows)],
                    width_ft=cell_size_ft,
                    notes="Main access path keeps center rows reachable.",
                )
            )
        elif garden is None and garden_context is None:
            access_paths = list(DEFAULT_ACCESS_PATHS)

        cells = [
            GridCell(cell_id=_cell_id(row, col), row=row, col=col, available=(row, col) not in path_cells, is_path=(row, col) in path_cells)
            for row in range(rows)
            for col in range(cols)
        ]
        grid = GardenGrid(rows=rows, cols=cols, cell_size_ft=cell_size_ft, cells=cells, access_paths=access_paths)
        self._last_paths = paths
        return grid

    def paths_for_grid(self, grid: GardenGrid) -> list[LayoutPathDTO]:
        return getattr(self, "_last_paths", [])

    def _dimensions(self, area_sq_ft: float, plant_count: int, cell_size_ft: float) -> tuple[int, int]:
        if area_sq_ft <= 0:
            return max(MIN_GRID_ROWS, (plant_count + DEFAULT_GRID_COLUMNS - 1) // DEFAULT_GRID_COLUMNS + 1), DEFAULT_GRID_COLUMNS
        target_cells = max(plant_count + 2, math.ceil(area_sq_ft / max(cell_size_ft * cell_size_ft, 1)))
        if area_sq_ft < 100:
            target_cells = min(max(target_cells, plant_count + 1), 24)
        elif area_sq_ft <= 500:
            target_cells = min(max(target_cells, plant_count + 4), 80)
        else:
            target_cells = min(max(target_cells, plant_count + 8), 160)
        cols = max(2, min(10, math.ceil(math.sqrt(target_cells * 1.25))))
        rows = max(MIN_GRID_ROWS, math.ceil(target_cells / cols))
        return rows, cols

    def _should_include_path(self, area_sq_ft: float, rows: int, cols: int) -> bool:
        if area_sq_ft < 100:
            return False
        if area_sq_ft > 500:
            return True
        return rows > 3 or cols > 4


def _area_sq_ft(garden: Garden | None, garden_context: Any | None) -> float:
    if garden_context is not None:
        if hasattr(garden_context, "area_sq_ft"):
            return float(garden_context.area_sq_ft or 0)
        geometry = getattr(garden_context, "geometry", None)
        if geometry is not None:
            return float(getattr(geometry, "area_sq_ft", 0) or 0)
        if isinstance(garden_context, dict):
            return float(garden_context.get("geometry", {}).get("area_sq_ft", 0) or garden_context.get("area_sq_ft", 0) or 0)
    return float(getattr(garden, "area_sq_ft", 0) or 0)


def _cell_id(row: int, col: int) -> str:
    return f"{_column_label(col)}{row + 1}"


def _column_label(col: int) -> str:
    return chr(ord("A") + col)
