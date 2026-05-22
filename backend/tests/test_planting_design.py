from types import SimpleNamespace

from app.engines.companion_graph.service import CompanionGraphService as NewCompanionGraphService
from app.engines.garden_context.service import GardenContextService as NewGardenContextService
from app.engines.layout.service import LayoutEngine as NewLayoutEngine
from app.engines.layout_design import LayoutDesignEngine
from app.engines.planting_design import PlantingDesignService
from app.engines.planting_design.schemas import PlantingDesignPlan
from app.engines.recommendations.service import GardenRecommendationService as NewGardenRecommendationService
from app.services.companions import CompanionGraphService
from app.services.garden_context import GardenContextService
from app.services.garden_recommendations import GardenRecommendationService
from app.services.layout import LayoutEngine
from app.services.layout.layout_schemas import LayoutOptions
from app.services.planting_design import PlantingDesignService as OldPlantingDesignService


def test_old_and_new_engine_imports_work() -> None:
    assert NewCompanionGraphService is CompanionGraphService
    assert NewGardenContextService is GardenContextService
    assert NewGardenRecommendationService is GardenRecommendationService
    assert NewLayoutEngine is LayoutEngine
    assert OldPlantingDesignService is PlantingDesignService


def test_planting_design_classifies_roles_and_builds_clusters() -> None:
    plants = [
        _plant(1, "tomato", height=72),
        _plant(2, "basil", plant_type="herb"),
        _plant(3, "marigold", flower=True, pollinator=9),
        _plant(4, "lettuce"),
        _plant(5, "squash", spread=72),
        _plant(6, "apple", tree=True, perennial=True, height=180),
    ]
    graph = CompanionGraphService(
        plants=plants,
        relationships=[
            _relationship(1, 1, 2, "beneficial"),
            _relationship(2, 1, 3, "pollinator_support"),
        ],
    )

    plan = PlantingDesignService().create_design_plan(
        garden_context=_context(),
        plants=plants,
        cultivars=[],
        companion_graph=graph,
        garden_goals=None,
        organization_style="rows",
    )

    roles = {(role.plant_slug, role.role) for role in plan.plant_roles}
    assert ("tomato", "primary_crop") in roles
    assert ("tomato", "trellised_crop") in roles
    assert ("basil", "companion_herb") in roles
    assert ("marigold", "pollinator_flower") in roles
    assert ("marigold", "border_plant") in roles
    assert ("lettuce", "leafy_green") in roles
    assert ("lettuce", "filler_crop") in roles
    assert ("squash", "sprawling_crop") in roles
    assert ("apple", "tree") in roles
    tomato_cluster = next(cluster for cluster in plan.companion_clusters if cluster.anchor_plant_slug == "tomato")
    assert "basil" in tomato_cluster.companion_plant_slugs
    assert "marigold" in tomato_cluster.border_plant_slugs
    assert "marigold" in plan.pollinator_border
    assert any(group.group_type == "tree_shrub_zone" for group in plan.plant_groups)
    assert any("Trees & Bushes" in item for item in plan.placement_guidance.rows_guidance)


def test_planting_design_creates_user_facing_separation_rules_and_isolation_guidance() -> None:
    plants = [_plant(1, "tomato"), _plant(2, "potato"), _plant(3, "mint", plant_type="herb"), _plant(4, "fennel", plant_type="herb")]
    graph = CompanionGraphService(plants=plants, relationships=[_relationship(10, 1, 2, "disease_risk", rationale="Nightshade disease pressure.")])

    plan = PlantingDesignService().create_design_plan(_context(), plants, [], graph, organization_style="rows")

    assert any(rule.plant_slugs == ["tomato", "potato"] and "Do not cluster" in rule.rationale for rule in plan.separation_rules)
    assert any(rule.plant_slugs == ["mint"] and rule.placement_guidance == "containerize" for rule in plan.separation_rules)
    assert any(rule.plant_slugs == ["fennel"] and rule.placement_guidance == "isolate" for rule in plan.separation_rules)
    assert not any("flagged as a risk" in rule.rationale for rule in plan.separation_rules)


def test_style_specific_design_guidance() -> None:
    plants = [_plant(1, "tomato"), _plant(2, "basil", plant_type="herb"), _plant(3, "marigold", flower=True, pollinator=9)]
    graph = CompanionGraphService(plants=plants, relationships=[_relationship(1, 1, 2, "beneficial"), _relationship(2, 1, 3, "pollinator_support")])
    service = PlantingDesignService()

    rows = service.create_design_plan(_context(), plants, [], graph, organization_style="rows")
    beds = service.create_design_plan(_context(), plants, [], graph, organization_style="raised_beds")
    chaos = service.create_design_plan(_context(), plants, [], graph, organization_style="chaos")

    assert rows.placement_guidance.rows_guidance
    assert any("bed-level companion clusters" in item for item in beds.placement_guidance.raised_beds_guidance)
    assert chaos.placement_guidance.chaos_guidance
    assert any(group.group_type == "chaos_mix" for group in chaos.plant_groups)


def test_strong_negative_edge_prevents_positive_cluster() -> None:
    plants = [_plant(1, "tomato"), _plant(2, "basil", plant_type="herb")]
    graph = CompanionGraphService(
        plants=plants,
        relationships=[
            _relationship(1, 1, 2, "beneficial", confidence="low", evidence_type="generated_inference"),
            _relationship(2, 1, 2, "avoid", confidence="high", evidence_type="extension_service"),
        ],
    )

    plan = PlantingDesignService().create_design_plan(_context(), plants, [], graph, organization_style="raised_beds")

    assert not plan.companion_clusters
    assert any(rule.severity == "high" for rule in plan.separation_rules)


def test_layout_engine_accepts_design_plan_and_returns_it() -> None:
    plants = [_plant(1, "tomato"), _plant(2, "basil", plant_type="herb")]
    graph = CompanionGraphService(plants=plants, relationships=[_relationship(1, 1, 2, "beneficial")])
    design_plan = PlantingDesignService().create_design_plan(_context(), plants, [], graph, organization_style="rows")

    result = LayoutEngine().generate_layout(
        _garden(),
        plants,
        garden_context=SimpleNamespace(area_sq_ft=240, sunlight_category="full_sun"),
        companion_graph=graph,
        options=LayoutOptions(layout_style="rows", include_paths=False, cell_size_ft=1),
        design_plan=design_plan,
    )

    assert isinstance(result.design_plan, PlantingDesignPlan)
    assert result.design_plan.summary == design_plan.summary
    assert result.layout_blueprint is not None
    assert result.layout_blueprint.row_blueprint is not None
    assert any("Planting design uses rows organization" in item for item in result.explanations)


def test_layout_design_blueprint_uses_companion_clusters_and_tree_section() -> None:
    plants = [
        _plant(1, "tomato", height=72),
        _plant(2, "basil", plant_type="herb"),
        _plant(3, "marigold", flower=True, pollinator=9),
        _plant(4, "apple", tree=True, perennial=True),
    ]
    graph = CompanionGraphService(plants=plants, relationships=[_relationship(1, 1, 2, "beneficial"), _relationship(2, 1, 3, "pollinator_support")])
    plan = PlantingDesignService().create_design_plan(_context(), plants, [], graph, organization_style="rows")

    blueprint = LayoutDesignEngine().create_blueprint(plan, plants)

    assert blueprint.layout_style == "rows"
    assert blueprint.row_blueprint is not None
    tomato_row = next(row for row in blueprint.row_blueprint.rows if "tomato" in row.primary_plants)
    assert "basil" in tomato_row.companion_plants
    assert "marigold" in tomato_row.border_plants
    assert blueprint.tree_shrub_section is not None
    assert blueprint.tree_shrub_section.items[0].plant_slug == "apple"


def test_layout_design_raised_bed_blueprint_places_border_flowers_and_unplaces_trees() -> None:
    plants = [
        _plant(1, "tomato"),
        _plant(2, "basil", plant_type="herb"),
        _plant(3, "marigold", flower=True, pollinator=9),
        _plant(4, "apple", tree=True, perennial=True),
    ]
    graph = CompanionGraphService(plants=plants, relationships=[_relationship(1, 1, 2, "beneficial"), _relationship(2, 1, 3, "pollinator_support")])
    plan = PlantingDesignService().create_design_plan(_context(), plants, [], graph, organization_style="raised_beds")

    blueprint = LayoutDesignEngine().create_blueprint(plan, plants, layout_options=SimpleNamespace(raised_beds={"number_of_beds": 1, "bed_length_ft": 8, "bed_width_ft": 4}))

    assert blueprint.raised_bed_blueprint is not None
    bed = blueprint.raised_bed_blueprint.beds[0]
    assert any(planting.plant_slug == "basil" and "tomato" in planting.near_plant_slugs for planting in bed.plantings)
    assert any(planting.plant_slug == "marigold" and planting.approximate_zone == "border" for planting in bed.border_plantings)
    assert "apple" in blueprint.raised_bed_blueprint.unplaced_plants


def test_layout_design_chaos_blueprint_is_advisory_only() -> None:
    plants = [_plant(1, "lettuce"), _plant(2, "marigold", flower=True, pollinator=9), _plant(3, "mint", plant_type="herb")]
    plan = PlantingDesignService().create_design_plan(_context(), plants, [], None, organization_style="chaos")

    blueprint = LayoutDesignEngine().create_blueprint(plan, plants)

    assert blueprint.layout_style == "chaos"
    assert blueprint.chaos_blueprint is not None
    assert blueprint.row_blueprint is None
    assert blueprint.raised_bed_blueprint is None
    assert blueprint.chaos_blueprint.scatter_guidance


def _garden(area: float = 240):
    return SimpleNamespace(id=7, area_sq_ft=area)


def _context():
    return SimpleNamespace(area_sq_ft=240)


def _plant(id: int, slug: str, *, plant_type: str = "vegetable", flower: bool = False, pollinator: int | None = None, tree: bool = False, perennial: bool = False, height: int | None = None, spread: int | None = 18):
    return SimpleNamespace(
        id=id,
        slug=slug,
        common_name=slug.replace("_", " "),
        plant_type=plant_type,
        plant_category=plant_type,
        edible=not flower or slug in {"squash"},
        flower=flower,
        ornamental=flower,
        tree=tree,
        is_tree=tree,
        is_shrub=False,
        perennial=perennial,
        pollinator_value_score=pollinator,
        typical_height_inches=height,
        typical_spread_inches=spread,
        spacing_inches=12,
        row_spacing_inches=24,
        sunlight_requirement="full_sun",
        water_requirement="medium",
        maintenance_level="Low",
        planting_notes="Use support if needed." if slug == "tomato" else "Test plant.",
    )


def _relationship(id: int, source: int, target: int, relationship_type: str, *, confidence: str = "medium", evidence_type: str = "extension_service", rationale: str | None = None):
    return SimpleNamespace(
        id=id,
        source_plant_id=source,
        target_plant_id=target,
        source_cultivar_id=None,
        target_cultivar_id=None,
        relationship_type=relationship_type,
        confidence=confidence,
        evidence_type=evidence_type,
        rationale=rationale or f"{relationship_type} relationship.",
        relationship_direction="symmetric",
        min_distance_inches=None,
        max_distance_inches=None,
        source_notes=None,
    )
