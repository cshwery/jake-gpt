from types import SimpleNamespace

from app.agents.planner import RuleBasedGardenPlanner
from app.schemas.plan import GardenGoals, PlanItemRead
from app.services.companions import CompanionGraphService
from app.services.layout import LayoutEngine
from app.services.layout.layout_schemas import LayoutResult


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


def _garden(area: float = 240):
    return SimpleNamespace(id=7, area_sq_ft=area)


def _plant(id: int, slug: str, spacing: int = 12, row_spacing: int = 18, tree: bool = False):
    return SimpleNamespace(
        id=id,
        slug=slug,
        common_name=slug.replace("_", " "),
        tree=tree,
        is_tree=tree,
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
