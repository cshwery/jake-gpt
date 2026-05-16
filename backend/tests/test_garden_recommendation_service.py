from datetime import date
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.api import gardens as garden_routes
from app.api import plants as plant_routes
from app.main import app
from app.models import Plant, PlantCompanionRelationship, PlantCultivar, PlantFamily
from app.schemas.garden import GardenContextDTO
from app.services.garden_recommendations import GardenGoalInput, GardenRecommendationResult, GardenRecommendationService, RecommendationData


def test_hardiness_scoring_perennial_mismatch_is_severe_but_annual_is_not() -> None:
    service = _service([_plant(1, "apple", tree=True, perennial=True, min_zone=8, max_zone=10), _plant(2, "tomato", min_zone=8, max_zone=10)])

    result = service.recommend_for_garden(_context(zone="5b"), _goals(["food"]), [], [], limit=10, include_excluded=True)

    apple = _rec(result, "apple")
    tomato = _rec(result, "tomato")
    assert apple.score_breakdown.hardiness_score == -100
    assert "HARDINESS_MISMATCH" in apple.reason_codes
    assert tomato.score_breakdown.hardiness_score == -10


def test_sunlight_scoring_full_sun_match_and_shade_penalty() -> None:
    service = _service([_plant(1, "tomato", sunlight="Full Sun"), _plant(2, "lettuce", sunlight="Part Shade")])

    sunny = service.recommend_for_garden(_context(sunlight="full_sun"), _goals(["food"]), [], [])
    shady = service.recommend_for_garden(_context(sunlight="shade"), _goals(["food"]), [], [], include_excluded=True)

    assert _rec(sunny, "tomato").score_breakdown.sunlight_score == 25
    assert _rec(shady, "tomato").score_breakdown.sunlight_score == -40


def test_unknown_sunlight_adds_assumption_without_crashing() -> None:
    service = _service([_plant(1, "tomato")])

    result = service.recommend_for_garden(_context(sunlight="unknown"), _goals(["food"]), [], [])

    assert any("Sunlight category is unknown" in assumption for assumption in result.assumptions)


def test_goal_and_maintenance_scoring() -> None:
    service = _service(
        [
            _plant(1, "tomato", edible=True, maintenance="Moderate"),
            _plant(2, "marigold", edible=False, flower=True, pollinator=9, maintenance="Low"),
            _plant(3, "fussy", edible=True, maintenance="High"),
        ]
    )

    food = service.recommend_for_garden(_context(), _goals(["food"], maintenance="low"), [], [], include_excluded=True)
    pollinators = service.recommend_for_garden(_context(), _goals(["pollinators", "flowers"], maintenance="low"), [], [])

    assert "FOOD_GOAL_MATCH" in _rec(food, "tomato").reason_codes
    assert "POLLINATOR_GOAL_MATCH" in _rec(pollinators, "marigold").reason_codes
    assert _rec(food, "fussy").score_breakdown.maintenance_score == -20


def test_companion_graph_boosts_basil_and_avoid_overrides_weak_positive() -> None:
    plants = [_plant(1, "tomato"), _plant(2, "basil"), _plant(3, "potato")]
    relationships = [
        _relationship(1, 2, 1, "beneficial", confidence="medium", evidence_type="extension_service"),
        _relationship(2, 3, 1, "beneficial", confidence="low", evidence_type="generated_inference"),
        _relationship(3, 3, 1, "avoid", confidence="high", evidence_type="extension_service"),
    ]
    service = _service(plants, relationships=relationships)

    result = service.recommend_for_garden(_context(), _goals(["food"]), ["tomato"], [], include_excluded=True)

    basil = _rec(result, "basil")
    potato = _rec(result, "potato")
    assert basil.score_breakdown.companion_score > 0
    assert "COMPANION_WITH_SELECTED_PLANT" in basil.reason_codes
    assert potato.score_breakdown.companion_score < -30
    assert "AVOID_RELATIONSHIP" in potato.reason_codes


def test_generated_inference_has_lower_impact_than_extension_relationship() -> None:
    plants = [_plant(1, "tomato"), _plant(2, "basil"), _plant(3, "dill")]
    relationships = [
        _relationship(1, 2, 1, "beneficial", confidence="medium", evidence_type="extension_service"),
        _relationship(2, 3, 1, "beneficial", confidence="low", evidence_type="generated_inference"),
    ]
    service = _service(plants, relationships=relationships)

    result = service.recommend_for_garden(_context(), _goals(["food"]), ["tomato"], [])

    assert _rec(result, "basil").score_breakdown.companion_score > _rec(result, "dill").score_breakdown.companion_score


def test_family_risk_warns_but_does_not_automatically_exclude() -> None:
    solanaceae = PlantFamily(id=1, slug="solanaceae", name="Solanaceae", common_name="nightshade family")
    service = _service([_plant(1, "tomato", family_id=1), _plant(2, "potato", family_id=1)], families=[solanaceae])

    result = service.recommend_for_garden(_context(), _goals(["food"]), ["tomato"], [], include_excluded=True)
    potato = _rec(result, "potato")

    assert potato.score_breakdown.family_risk_score == -5
    assert "SAME_FAMILY_WARNING" in potato.reason_codes
    assert potato.score > -40


def test_cultivar_scoring_uses_maturity_overrides_and_fallbacks() -> None:
    tomato = _plant(1, "tomato")
    cultivars = [
        _cultivar(1, 1, "tomato_sungold", "Sungold", days=65, disease_resistance="good"),
        _cultivar(2, 1, "tomato_unknown", "Unknown"),
    ]
    service = _service([tomato], cultivars=cultivars)

    result = service.recommend_for_garden(_context(season_days=90), _goals(["food"]), [], [])
    rec = _rec(result, "tomato")

    assert rec.cultivar_recommendations[0].cultivar_slug == "tomato_sungold"
    assert "CULTIVAR_DAYS_TO_MATURITY_FIT" in rec.cultivar_recommendations[0].reason_codes
    assert "CULTIVAR_DISEASE_RESISTANCE" in rec.cultivar_recommendations[0].reason_codes
    assert "FALLBACK_TO_SPECIES_DEFAULTS" in rec.cultivar_recommendations[-1].reason_codes


def test_space_scoring_penalizes_large_tree_in_small_garden_unless_shade_goal() -> None:
    service = _service([_plant(1, "apple", tree=True, perennial=True, spread=240)])

    food = service.recommend_for_garden(_context(area_sq_ft=80), _goals(["food"]), [], [], include_excluded=True)
    shade = service.recommend_for_garden(_context(area_sq_ft=80), _goals(["shade"]), [], [], include_excluded=True)

    assert _rec(food, "apple").score_breakdown.space_score == -25
    assert _rec(shade, "apple").score_breakdown.space_score >= -10


def test_recommendation_result_contains_breakdown_reasons_explanation_warnings_and_assumptions() -> None:
    service = _service([_plant(1, "tomato")])

    result = service.recommend_for_garden(_context(assumptions=["Hardiness is mocked."]), _goals(["food"]), [], [])
    rec = _rec(result, "tomato")

    assert rec.score_breakdown.total_score == rec.score
    assert rec.reason_codes
    assert rec.explanation
    assert result.assumptions
    assert isinstance(result.warnings, list)


def test_recommendation_api_generate_latest_and_missing_context(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_context = SimpleNamespace(get_context=lambda garden_id: _context())
    fake_service = SimpleNamespace(recommend_for_garden=lambda *args, **kwargs: _fake_result())
    fake_db = FakeRecommendationSession()
    monkeypatch.setattr(garden_routes, "GardenContextService", lambda db: fake_context)
    monkeypatch.setattr(garden_routes, "GardenRecommendationService", lambda db: fake_service)
    monkeypatch.setattr(garden_routes, "_authorize_garden", lambda garden_id, db, user: SimpleNamespace(id=garden_id))
    app.dependency_overrides[deps.get_current_user] = lambda: SimpleNamespace(id=1)
    app.dependency_overrides[garden_routes.get_db] = lambda: fake_db

    client = TestClient(app)
    body = {"goals": ["food"], "primary_goal": "food", "selected_plant_slugs": ["tomato"]}
    generated = client.post("/api/gardens/1/recommendations/generate", json=body, headers={"Authorization": "Bearer test"})
    latest = client.get("/api/gardens/1/recommendations/latest", headers={"Authorization": "Bearer test"})

    fake_context_missing = SimpleNamespace(get_context=lambda garden_id: (_ for _ in ()).throw(LookupError("missing")))
    monkeypatch.setattr(garden_routes, "GardenContextService", lambda db: fake_context_missing)
    missing = client.post("/api/gardens/2/recommendations/generate", json=body, headers={"Authorization": "Bearer test"})
    app.dependency_overrides.clear()

    assert generated.status_code == 200
    assert latest.status_code == 200
    assert missing.status_code == 400
    assert "Generate garden context" in missing.json()["detail"]


def test_legacy_plants_suggest_uses_new_recommendation_service(monkeypatch: pytest.MonkeyPatch) -> None:
    basil = _plant(2, "basil")
    fake_db = FakePlantSuggestSession([basil])

    class FakeRecommendationService:
        def __init__(self, db) -> None:
            pass

        def recommend_for_garden(self, *args, **kwargs) -> GardenRecommendationResult:
            return GardenRecommendationResult(
                garden_id=1,
                summary="Test",
                selected=["tomato"],
                recommendations=[
                    {
                        "plant_slug": "basil",
                        "plant_common_name": "Basil",
                        "cultivar_recommendations": [],
                        "recommendation_type": "suggested_companion",
                        "score": 82.0,
                        "score_breakdown": {"total_score": 82.0},
                        "reason_codes": ["COMPANION_WITH_SELECTED_PLANT"],
                        "warnings": [],
                        "explanation": "Basil pairs well with tomato.",
                    }
                ],
                warnings=[],
                excluded=[],
                assumptions=[],
            )

    monkeypatch.setattr(plant_routes, "GardenRecommendationService", FakeRecommendationService)
    app.dependency_overrides[deps.get_current_user] = lambda: SimpleNamespace(id=1)
    app.dependency_overrides[plant_routes.get_db] = lambda: fake_db

    response = TestClient(app).post(
        "/api/plants/suggest",
        json={"garden_id": 1, "goal": "Food", "maintenance_preference": "Moderate", "sunlight": "Full Sun", "selected_plant_ids": []},
        headers={"Authorization": "Bearer test"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()[0]["plant"]["slug"] == "basil"
    assert response.json()[0]["score"] == 82
    assert "Basil pairs well with tomato." in response.json()[0]["reasons"]


def _service(
    plants: list[Plant],
    *,
    cultivars: list[PlantCultivar] | None = None,
    relationships: list[PlantCompanionRelationship] | None = None,
    families: list[PlantFamily] | None = None,
) -> GardenRecommendationService:
    return GardenRecommendationService(data=RecommendationData(plants=plants, cultivars=cultivars or [], relationships=relationships or [], families=families or []))


def _context(zone: str = "6b", sunlight: str = "full_sun", area_sq_ft: float = 400, season_days: int = 150, assumptions: list[str] | None = None) -> GardenContextDTO:
    return GardenContextDTO.model_validate(
        {
            "garden_id": 1,
            "geometry": {
                "centroid": {"lat": 42.0, "lon": -83.0},
                "bbox": {"min_lat": 42.0, "min_lon": -83.0, "max_lat": 42.001, "max_lon": -82.999},
                "area_sq_m": area_sq_ft / 10.7639,
                "area_sq_ft": area_sq_ft,
            },
            "hardiness": {"zone": zone, "source": "mock", "confidence": "low"},
            "frost": {
                "estimated_last_frost_date": date(2026, 5, 5),
                "estimated_first_frost_date": date(2026, 10, 12),
                "growing_season_days": season_days,
                "source": "mock",
                "confidence": "low",
            },
            "precipitation": {
                "expected_annual_precipitation_mm": 820,
                "expected_growing_season_precipitation_mm": 480,
                "category": "medium",
                "source": "mock",
                "confidence": "low",
            },
            "sunlight": {"category": sunlight, "method": "user_reported", "confidence": "medium", "user_override": sunlight},
            "assumptions": assumptions or [],
            "warnings": [],
            "raw_context": {},
        }
    )


def _goals(goals: list[str], maintenance: str = "moderate", experience: str = "beginner") -> GardenGoalInput:
    return GardenGoalInput(goals=goals, primary_goal=goals[0] if goals else None, maintenance_preference=maintenance, experience_level=experience)


def _plant(
    id: int,
    slug: str,
    *,
    edible: bool = True,
    flower: bool = False,
    tree: bool = False,
    perennial: bool = False,
    min_zone: int = 3,
    max_zone: int = 10,
    sunlight: str = "Full Sun",
    water: str = "medium",
    maintenance: str = "Moderate",
    pollinator: int | None = None,
    spread: int | None = 18,
    family_id: int | None = None,
) -> Plant:
    return Plant(
        id=id,
        slug=slug,
        plant_family_id=family_id,
        common_name=slug.replace("_", " ").title(),
        plant_type="tree" if tree else "herb" if slug in {"basil", "dill"} else "vegetable",
        edible=edible,
        flower=flower,
        ornamental=flower,
        tree=tree,
        is_tree=tree,
        is_shrub=False,
        perennial=perennial,
        min_zone=min_zone,
        max_zone=max_zone,
        sunlight_requirement=sunlight,
        water_requirement=water,
        spacing_inches=12,
        row_spacing_inches=24,
        typical_spread_inches=spread,
        maintenance_level=maintenance,
        pollinator_value_score=pollinator,
        beginner_friendliness_score=8 if maintenance.lower() != "high" else 4,
        planting_notes="Test plant.",
    )


def _cultivar(id: int, plant_id: int, slug: str, name: str, days: int | None = None, disease_resistance: str | None = None) -> PlantCultivar:
    return PlantCultivar(id=id, plant_id=plant_id, slug=slug, cultivar_name=name, normalized_name=name.lower(), days_to_maturity_max=days, disease_resistance=disease_resistance)


def _relationship(id: int, source: int, target: int, relationship_type: str, confidence: str = "medium", evidence_type: str = "extension_service") -> PlantCompanionRelationship:
    return PlantCompanionRelationship(
        id=id,
        source_plant_id=source,
        target_plant_id=target,
        relationship_type=relationship_type,
        confidence=confidence,
        evidence_type=evidence_type,
        rationale=f"{relationship_type} test relationship.",
        source_name="Test",
        relationship_direction="symmetric",
    )


def _rec(result, slug: str):
    for recommendation in result.recommendations:
        if recommendation.plant_slug == slug:
            return recommendation
    for excluded in result.excluded:
        if excluded.plant_slug == slug:
            raise AssertionError(f"{slug} was excluded: {excluded.message}")
    raise AssertionError(f"missing recommendation for {slug}")


def _fake_result() -> GardenRecommendationResult:
    return GardenRecommendationResult(garden_id=1, summary="Test", selected=["tomato"], recommendations=[], warnings=[], excluded=[], assumptions=[])


class FakeRecommendationSession:
    def __init__(self) -> None:
        self.run = None

    def add(self, run) -> None:
        self.run = run
        self.run.id = 1

    def commit(self) -> None:
        return None

    def scalar(self, statement):
        return self.run


class FakePlantSuggestSession:
    def __init__(self, plants: list[Plant]) -> None:
        self.garden = SimpleNamespace(id=1, property=SimpleNamespace(user_id=1))
        self.context = _context()
        self.plants = plants

    def get(self, model, id: int):
        return self.garden

    def scalar(self, statement):
        return self.context

    def scalars(self, statement):
        return SimpleNamespace(all=lambda: self.plants)
