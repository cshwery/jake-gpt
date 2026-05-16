from app.services.layout.layout_config import DEFAULT_ACCESS_PATHS, DEFAULT_GRID_COLUMNS, MIN_GRID_ROWS


class GridBuilder:
    def build_grid(self, plant_count: int, columns: int = DEFAULT_GRID_COLUMNS) -> dict:
        rows = max(MIN_GRID_ROWS, (plant_count + columns - 1) // columns + 1)
        return {"rows": rows, "cols": columns, "access_paths": list(DEFAULT_ACCESS_PATHS)}
