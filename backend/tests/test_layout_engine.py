from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api import layouts as layout_routes
from app.main import app
from app.models import GardenLayout, LayoutPlacement
from app.agents.planner import RuleBasedGardenPlanner
from app.schemas.plan import GardenGoals, PlanItemRead
from app.services.companions import CompanionGraphService
from app.services.layout import LayoutEngine
from app.services.layout.grid_builder import GridBuilder
from app.services.layout.layout_schemas import GardenGrid, GridCell, LayoutOptions, LayoutResult
from app.services.layout.placement_planner import PlacementPlanner


def test_layout_engine_creates_expected_grid_rows_and_columns() -> None:
    result = LayoutEngine().generate_layout(_garden(), [_plant(1, "tomato"), _plant(2, "basil"), _plant(3, "marigold")])

    assert result.layout_grid["cols"] == 4
    assert result.layout_grid["rows"] == 3
    assert result.layout_grid["access_paths"] == ["between every grid row"]


def test_layout_engine_returns_plan_item_compatible_items() -> None:
    result = LayoutEngine().generate_layout(_garden(), [_plant(1, "tomato")])

    assert isinstance(result.items[0], PlanItemRead)
    assert result.items[0].plant_id == 1
    assert result.items[0].x_pct > 0
    assert result.items[0].notes.startswith("12 in spacing")


def test_tree_or_tall_plants_prefer_top_row() -> None:
    result = LayoutEngine().generate_layout(_garden(), [_plant(1, "basil"), _plant(2, "apple", tree=True)])

    apple = next(item for item in result.items if item.label == "Apple")
    assert apple.row == 0


def test_quantity_uses_garden_area_and_spacing_with_cap() -> None:
    result = LayoutEngine().generate_layout(_garden(area=240), [_plant(1, "lettuce", spacing=12, row_spacing=12)])

    assert result.items[0].quantity == 12


def test_beneficial_companions_are_placed_near_when_simple() -> None:
    plants = [_plant(1, "tomato"), _plant(2, "carrot"), _plant(3, "basil")]
    graph = CompanionGraphService(relationships=[_relationship(1, 3, "beneficial")], plants=plants)

    result = LayoutEngine().generate_layout(_garden(), plants, companion_graph=graph)

    positions = {item.label.lower(): (item.row, item.col) for item in result.items}
    assert abs(positions["tomato"][1] - positions["basil"][1]) <= 1


def test_strong_negative_pairs_are_not_adjacent_when_possible() -> None:
    plants = [_plant(1, "tomato"), _plant(2, "potato"), _plant(3, "basil")]
    graph = CompanionGraphService(relationships=[_relationship(1, 2, "avoid", confidence="high")], plants=plants)

    result = LayoutEngine().generate_layout(_garden(), plants, companion_graph=graph)

    positions = {item.label.lower(): (item.row, item.col) for item in result.items}
    assert abs(positions["tomato"][1] - positions["potato"][1]) > 1
    assert result.warnings


def test_rule_based_planner_delegates_to_layout_engine() -> None:
    fake_engine = FakeLayoutEngine()
    goals = GardenGoals(goal="Food", maintenance_preference="Moderate", sunlight="Full Sun")

    result = RuleBasedGardenPlanner(layout_engine=fake_engine).generate(_garden(), [_plant(1, "tomato")], [], goals)

    assert fake_engine.called
    assert result.layout_grid["cols"] == 9
    assert result.items[0].label == "Delegated"


def test_persisted_layout_models_define_expected_tables() -> None:
    assert GardenLayout.__tablename__ == "garden_layouts"
    assert LayoutPlacement.__tablename__ == "layout_placements"
    assert "score_breakdown" in GardenLayout.__table__.columns
    assert "grid_cells" in LayoutPlacement.__table__.columns


def test_grid_builder_v1_labels_cells_and_adds_paths_for_medium_garden() -> None:
    grid = GridBuilder().build_grid(
        5,
        garden=_garden(area=240),
        garden_context=SimpleNamespace(area_sq_ft=240),
        options=LayoutOptions(cell_size_ft=4, include_paths=True),
    )

    assert grid.orientation == "north_up"
    assert grid.cells[0].cell_id == "A1"
    assert any(cell.is_path for cell in grid.cells)
    assert grid.access_paths


def test_placement_uses_cultivar_spacing_then_species_fallback() -> None:
    tomato = _plant(1, "tomato", spacing=24, row_spacing=36)
    basil = _plant(2, "basil", spacing=12, row_spacing=12)
    cultivar = SimpleNamespace(id=10, plant_id=1, slug="tomato_sungold", cultivar_name="Sungold", spacing_inches_override=18, row_spacing_inches_override=24)
    grid = GardenGrid(rows=3, cols=4, cells=[GridCell(cell_id=f"{chr(ord('A') + col)}{row + 1}", row=row, col=col) for row in range(3) for col in range(4)])

    placements, warnings = PlacementPlanner().plan_placements(_garden(area=120), [tomato, basil], grid, cultivars=[cultivar])

    assert warnings
    tomato_placement = next(placement for placement in placements if placement.plant_slug == "tomato")
    basil_placement = next(placement for placement in placements if placement.plant_slug == "basil")
    assert tomato_placement.spacing_inches == 18
    assert tomato_placement.row_spacing_inches == 24
    assert basil_placement.spacing_inches == 12


def test_layout_engine_v1_scores_and_explains_candidates() -> None:
    plants = [_plant(1, "tomato"), _plant(2, "basil"), _plant(3, "marigold", flower=True)]
    graph = CompanionGraphService(relationships=[_relationship(1, 2, "beneficial"), _relationship(1, 3, "pollinator_support")], plants=plants)

    result = LayoutEngine().generate_layout(
        _garden(area=240),
        plants,
        garden_context=SimpleNamespace(area_sq_ft=240, sunlight_category="full_sun"),
        companion_graph=graph,
        options=LayoutOptions(cell_size_ft=4, include_paths=True),
    )

    assert result.score_breakdown.total_score != 0
    assert result.score_breakdown.companion_score > 0
    assert result.paths
    assert any("rectangular grid" in assumption for assumption in result.assumptions)
    assert any("placed near" in explanation or "companion graph" in explanation for explanation in result.explanations)


def test_layout_result_includes_orientation_and_cell_size() -> None:
    result = LayoutEngine().generate_layout(_garden(area=120), [_plant(1, "tomato")], garden_context=SimpleNamespace(area_sq_ft=120), options=LayoutOptions(cell_size_ft=4))

    assert result.grid.orientation == "north_up"
    assert result.grid.cell_size_ft == 4


def test_pollinator_flowers_prefer_border_cells() -> None:
    result = LayoutEngine().generate_layout(_garden(area=240), [_plant(1, "tomato"), _plant(2, "marigold", flower=True)], garden_context=SimpleNamespace(area_sq_ft=240), options=LayoutOptions(cell_size_ft=4))

    marigold = next(placement for placement in result.placements if placement.plant_slug == "marigold")
    assert any(cell_id.startswith("A") or cell_id.endswith("1") for cell_id in marigold.grid_cells)


def test_companion_visual_cells_are_adjacent_for_tomato_and_basil() -> None:
    plants = [_plant(1, "tomato"), _plant(2, "basil")]
    graph = CompanionGraphService(relationships=[_relationship(1, 2, "beneficial")], plants=plants)

    result = LayoutEngine().generate_layout(_garden(area=240), plants, garden_context=SimpleNamespace(area_sq_ft=240), companion_graph=graph, options=LayoutOptions(cell_size_ft=4))
    tomato_cells = _cells_for(result, "tomato")
    basil_cells = _cells_for(result, "basil")

    assert any(abs(tomato.row - basil.row) + abs(tomato.col - basil.col) <= 1 for tomato in tomato_cells for basil in basil_cells)
    assert any("placed near" in (placement.location_notes or "") for placement in result.placements)


def test_layout_engine_persists_layout_and_placements() -> None:
    db = FakeLayoutSession()
    result = LayoutEngine().generate_layout(_garden(area=120), [_plant(1, "tomato")], garden_context=SimpleNamespace(area_sq_ft=120), options=LayoutOptions(cell_size_ft=4))

    persisted = LayoutEngine().persist_layout(result, db, garden=_garden(area=120), input_payload={"selected_plant_slugs": ["tomato"]})

    assert persisted.id == 1
    assert persisted.score_total == result.score_breakdown.total_score
    assert persisted.result["layout_id"] == 1
    assert len(db.placements) == 1
    assert db.placements[0].grid_cells


def test_layout_api_missing_context_returns_helpful_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(layout_routes, "_authorize_garden", lambda garden_id, db, user: _garden())
    monkeypatch.setattr(layout_routes, "GardenContextService", lambda db: SimpleNamespace(get_context=lambda garden_id: (_ for _ in ()).throw(LookupError("missing"))))
    app.dependency_overrides[deps.get_current_user] = lambda: SimpleNamespace(id=1)
    app.dependency_overrides[layout_routes.get_db] = lambda: object()

    response = TestClient(app).post("/api/gardens/1/layouts/generate", json={"selected_plant_slugs": ["tomato"]}, headers={"Authorization": "Bearer test"})
    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert "Generate garden context" in response.json()["detail"]


def test_layout_api_latest_and_get_enforce_ownership(monkeypatch: pytest.MonkeyPatch) -> None:
    layout_result = LayoutEngine().generate_layout(_garden(area=120), [_plant(1, "tomato")], garden_context=SimpleNamespace(area_sq_ft=120), options=LayoutOptions(cell_size_ft=4))
    persisted = SimpleNamespace(
        id=44,
        garden_id=7,
        garden_plan_id=None,
        recommendation_run_id=None,
        result=layout_result.model_dump(mode="json"),
        garden=SimpleNamespace(property=SimpleNamespace(user_id=1)),
    )
    fake_db = SimpleNamespace(scalar=lambda statement: persisted, get=lambda model, id: persisted)
    monkeypatch.setattr(layout_routes, "_authorize_garden", lambda garden_id, db, user: _garden())
    app.dependency_overrides[deps.get_current_user] = lambda: SimpleNamespace(id=1)
    app.dependency_overrides[layout_routes.get_db] = lambda: fake_db

    client = TestClient(app)
    latest = client.get("/api/gardens/7/layouts/latest", headers={"Authorization": "Bearer test"})
    existing = client.get("/api/layouts/44", headers={"Authorization": "Bearer test"})

    app.dependency_overrides.clear()

    assert latest.status_code == 200
    assert existing.status_code == 200
    assert latest.json()["layout_id"] == 44
    assert existing.json()["layout_id"] == 44


def _garden(area: float = 240):
    return SimpleNamespace(id=7, area_sq_ft=area)


def _plant(id: int, slug: str, spacing: int = 12, row_spacing: int = 18, tree: bool = False, flower: bool = False):
    return SimpleNamespace(
        id=id,
        slug=slug,
        common_name=slug.replace("_", " "),
        tree=tree,
        is_tree=tree,
        is_shrub=False,
        flower=flower,
        ornamental=flower,
        edible=not flower,
        plant_type="flower" if flower else "vegetable",
        pollinator_value_score=8 if flower else None,
        sunlight_requirement="full_sun",
        typical_height_inches=96 if tree else None,
        spacing_inches=spacing,
        row_spacing_inches=row_spacing,
        planting_notes="Test notes.",
    )


def _relationship(source: int, target: int, relationship_type: str, confidence: str = "medium"):
    return SimpleNamespace(
        id=source * 10 + target,
        source_plant_id=source,
        target_plant_id=target,
        source_cultivar_id=None,
        target_cultivar_id=None,
        relationship_type=relationship_type,
        confidence=confidence,
        evidence_type="extension_service",
        rationale="Test relationship.",
        relationship_direction="symmetric",
        min_distance_inches=None,
        max_distance_inches=None,
        source_notes=None,
    )


class FakeLayoutEngine:
    def __init__(self) -> None:
        self.called = False

    def generate_layout(self, garden, plants, companion_graph=None) -> LayoutResult:
        self.called = True
        return LayoutResult(
            layout_grid={"rows": 1, "cols": 9, "access_paths": []},
            items=[
                PlanItemRead(
                    plant_id=1,
                    label="Delegated",
                    row=0,
                    col=0,
                    x_pct=50,
                    y_pct=50,
                )
            ],
        )


class FakeLayoutSession:
    def __init__(self) -> None:
        self.layouts: list[GardenLayout] = []
        self.placements: list[LayoutPlacement] = []

    def add(self, instance) -> None:
        if isinstance(instance, GardenLayout):
            self.layouts.append(instance)
        elif isinstance(instance, LayoutPlacement):
            self.placements.append(instance)

    def flush(self) -> None:
        for idx, layout in enumerate(self.layouts, start=1):
            layout.id = layout.id or idx
        for idx, placement in enumerate(self.placements, start=1):
            placement.id = placement.id or idx


def _cells_for(result: LayoutResult, plant_slug: str):
    return [cell for cell in result.grid.cells if cell.plant_slug == plant_slug]
