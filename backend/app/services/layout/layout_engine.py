from app.models import Garden, Plant
from app.services.companions import CompanionGraphService
from app.services.layout.grid_builder import GridBuilder
from app.services.layout.layout_explanation_builder import LayoutExplanationBuilder
from app.services.layout.layout_schemas import LayoutResult
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
        companion_graph: CompanionGraphService | None = None,
    ) -> LayoutResult:
        ordered, warnings = self.placement_planner.order_plants(plants, companion_graph)
        layout_grid = self.grid_builder.build_grid(len(ordered))
        items = self.placement_planner.build_items(garden, ordered, layout_grid["rows"], layout_grid["cols"])
        return LayoutResult(
            layout_grid=layout_grid,
            items=items,
            score_breakdown=self.layout_scorer.score(ordered, warnings),
            warnings=warnings,
            explanations=self.explanation_builder.explanations(),
            assumptions=self.explanation_builder.assumptions(),
        )
