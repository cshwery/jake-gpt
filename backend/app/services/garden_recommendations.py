from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Plant, PlantCompanionRelationship, PlantCultivar, PlantFamily
from app.schemas.garden import GardenContextDTO
from app.services.companions import CompanionGraphService, NEGATIVE_RELATIONSHIP_TYPES, STRONG_NEGATIVE_RELATIONSHIP_TYPES

GoalValue = Literal["food", "flowers", "shade", "pollinators", "low_maintenance", "kid_friendly", "herbs", "fruit", "trees", "native_plants", "combination"]
MaintenanceValue = Literal["low", "moderate", "high"]
ExperienceLevel = Literal["beginner", "intermediate", "advanced"]


class GardenGoalInput(BaseModel):
    goals: list[GoalValue] = Field(default_factory=list)
    primary_goal: GoalValue | None = None
    maintenance_preference: MaintenanceValue = "moderate"
    experience_level: ExperienceLevel = "beginner"
    planting_style: Literal["rows", "intensive_grid", "raised_beds", "mixed", "chaos"] = "rows"
    using_raised_beds: bool | None = None
    raised_beds: dict[str, Any] | None = None
    start_preference: Literal["germinate_myself", "buy_from_nursery", "no_preference"] | None = None
    can_start_seeds_indoors: bool | None = None
    prefers_buying_starts: bool | None = None
    direct_sow_preference: Literal["direct_sow_when_reasonable", "prefer_transplants", "no_preference"] | None = None
    desired_plant_slugs: list[str] = Field(default_factory=list)
    desired_cultivar_slugs: list[str] = Field(default_factory=list)
    excluded_plant_slugs: list[str] = Field(default_factory=list)
    notes: str | None = None


GardenGoalInput.model_rebuild()


class ScoreBreakdown(BaseModel):
    hardiness_score: float = 0
    sunlight_score: float = 0
    water_score: float = 0
    goal_score: float = 0
    maintenance_score: float = 0
    space_score: float = 0
    companion_score: float = 0
    family_risk_score: float = 0
    cultivar_score: float = 0
    beginner_score: float = 0
    chaos_score: float = 0
    diversity_score: float = 0
    total_score: float = 0


class CultivarRecommendation(BaseModel):
    cultivar_slug: str
    cultivar_name: str
    score: float
    reason_codes: list[str]


class PlantRecommendation(BaseModel):
    plant_slug: str
    plant_common_name: str
    cultivar_recommendations: list[CultivarRecommendation] = Field(default_factory=list)
    recommendation_type: str
    score: float
    score_breakdown: ScoreBreakdown
    reason_codes: list[str]
    warnings: list[str]
    explanation: str


class RecommendationWarning(BaseModel):
    warning_type: str
    plant_slugs: list[str]
    severity: str
    message: str


class ExcludedCandidate(BaseModel):
    plant_slug: str
    reason_codes: list[str]
    message: str


class GardenRecommendationResult(BaseModel):
    garden_id: int
    summary: str
    selected: list[str]
    recommendations: list[PlantRecommendation]
    warnings: list[RecommendationWarning]
    excluded: list[ExcludedCandidate] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class GardenRecommendationRequest(BaseModel):
    goals: list[GoalValue] = Field(default_factory=list)
    primary_goal: GoalValue | None = None
    maintenance_preference: MaintenanceValue = "moderate"
    experience_level: ExperienceLevel = "beginner"
    selected_plant_slugs: list[str] = Field(default_factory=list)
    selected_cultivar_slugs: list[str] = Field(default_factory=list)
    excluded_plant_slugs: list[str] = Field(default_factory=list)
    limit: int = 25
    include_excluded: bool = False
    notes: str | None = None
    start_preference: Literal["germinate_myself", "buy_from_nursery", "no_preference"] | None = None
    planting_style: Literal["rows", "intensive_grid", "raised_beds", "mixed", "chaos"] = "rows"
    using_raised_beds: bool | None = None
    raised_beds: dict[str, Any] | None = None
    can_start_seeds_indoors: bool | None = None
    prefers_buying_starts: bool | None = None
    direct_sow_preference: Literal["direct_sow_when_reasonable", "prefer_transplants", "no_preference"] | None = None


@dataclass(frozen=True)
class RecommendationData:
    plants: list[Plant]
    cultivars: list[PlantCultivar]
    relationships: list[PlantCompanionRelationship]
    families: list[PlantFamily]


class PlantFamilyService:
    def __init__(self, plants: list[Plant], families: list[PlantFamily]) -> None:
        self._plants_by_slug = {plant.slug: plant for plant in plants if plant.slug}
        self._families_by_id = {family.id: family for family in families}

    def get_family_for_plant(self, plant_slug: str) -> PlantFamily | None:
        plant = self._plants_by_slug.get(plant_slug)
        if plant is None or plant.plant_family_id is None:
            return None
        return self._families_by_id.get(plant.plant_family_id)

    def plants_share_family(self, plant_slug_a: str, plant_slug_b: str) -> bool:
        family_a = self.get_family_for_plant(plant_slug_a)
        family_b = self.get_family_for_plant(plant_slug_b)
        return family_a is not None and family_b is not None and family_a.id == family_b.id

    def get_family_conflict_warning(self, plant_slug_a: str, plant_slug_b: str) -> str | None:
        if not self.plants_share_family(plant_slug_a, plant_slug_b):
            return None
        family = self.get_family_for_plant(plant_slug_a)
        family_name = family.common_name if family and family.common_name else family.name if family else "same plant family"
        return f"{plant_slug_a.replace('_', ' ').title()} and {plant_slug_b.replace('_', ' ').title()} are both in the {family_name} and may share disease or pest pressure."


class GardenRecommendationService:
    def __init__(self, db: Session | None = None, data: RecommendationData | None = None, companion_graph: CompanionGraphService | None = None) -> None:
        if data is None and db is not None:
            data = RecommendationData(
                plants=list(db.scalars(select(Plant)).all()),
                cultivars=list(db.scalars(select(PlantCultivar)).all()),
                relationships=list(db.scalars(select(PlantCompanionRelationship)).all()),
                families=list(db.scalars(select(PlantFamily)).all()),
            )
        self.data = data or RecommendationData([], [], [], [])
        self.plants_by_slug = {plant.slug: plant for plant in self.data.plants if plant.slug}
        self.cultivars_by_plant: dict[int, list[PlantCultivar]] = {}
        for cultivar in self.data.cultivars:
            self.cultivars_by_plant.setdefault(cultivar.plant_id, []).append(cultivar)
        self.graph = companion_graph or CompanionGraphService(relationships=self.data.relationships, plants=self.data.plants, cultivars=self.data.cultivars)
        self.family_service = PlantFamilyService(self.data.plants, self.data.families)

    def recommend_for_garden(
        self,
        garden_context: GardenContextDTO,
        user_goals: GardenGoalInput,
        selected_plant_slugs: list[str],
        selected_cultivar_slugs: list[str],
        limit: int = 25,
        include_excluded: bool = False,
    ) -> GardenRecommendationResult:
        selected = _unique([*selected_plant_slugs, *user_goals.desired_plant_slugs])
        excluded_slugs = set(user_goals.excluded_plant_slugs)
        recommendations: list[PlantRecommendation] = []
        excluded: list[ExcludedCandidate] = []
        warnings = self._selected_warnings(selected)
        assumptions = list(garden_context.assumptions)
        if garden_context.sunlight.category == "unknown":
            assumptions.append("Sunlight category is unknown, so sunlight fit was not scored.")

        for plant in self.data.plants:
            if not plant.slug or plant.slug in selected:
                continue
            if plant.slug in excluded_slugs:
                excluded.append(ExcludedCandidate(plant_slug=plant.slug, reason_codes=["USER_EXCLUDED"], message="User excluded this plant."))
                continue
            recommendation = self._score_plant(plant, garden_context, user_goals, selected)
            if recommendation.score < -40:
                excluded.append(ExcludedCandidate(plant_slug=plant.slug, reason_codes=recommendation.reason_codes, message=recommendation.explanation))
                if include_excluded:
                    recommendations.append(recommendation)
                continue
            if recommendation.score > 0 or recommendation.warnings:
                recommendations.append(recommendation)

        recommendations = self._apply_diversity(recommendations, user_goals)
        recommendations = sorted(recommendations, key=lambda item: (-item.score, item.plant_common_name))[:limit]
        return GardenRecommendationResult(
            garden_id=garden_context.garden_id,
            summary=_summary(garden_context, user_goals),
            selected=selected,
            recommendations=recommendations,
            warnings=warnings,
            excluded=excluded if include_excluded else excluded[:10],
            assumptions=_unique(assumptions + ["Companion planting is advisory and confidence-weighted."]),
        )

    def _score_plant(self, plant: Plant, context: GardenContextDTO, goals: GardenGoalInput, selected: list[str]) -> PlantRecommendation:
        breakdown = ScoreBreakdown()
        reason_codes: list[str] = []
        warnings: list[str] = []

        breakdown.hardiness_score, codes, warn = _hardiness_score(plant, context)
        reason_codes.extend(codes)
        warnings.extend(warn)
        breakdown.sunlight_score, codes, warn = _sunlight_score(plant, context)
        reason_codes.extend(codes)
        warnings.extend(warn)
        breakdown.water_score, codes, warn = _water_score(plant, context)
        reason_codes.extend(codes)
        warnings.extend(warn)
        breakdown.goal_score, codes = _goal_score(plant, goals)
        reason_codes.extend(codes)
        breakdown.maintenance_score, codes = _maintenance_score(plant, goals.maintenance_preference)
        reason_codes.extend(codes)
        breakdown.space_score, codes, warn = _space_score(plant, context, goals)
        reason_codes.extend(codes)
        warnings.extend(warn)
        breakdown.companion_score, codes, warn = self._companion_score(plant.slug or "", selected)
        reason_codes.extend(codes)
        warnings.extend(warn)
        breakdown.family_risk_score, codes, warn = self._family_score(plant.slug or "", selected)
        reason_codes.extend(codes)
        warnings.extend(warn)
        breakdown.beginner_score, codes = _beginner_score(plant, goals.experience_level)
        reason_codes.extend(codes)
        breakdown.chaos_score, codes, warn = _chaos_score(plant, context, goals)
        reason_codes.extend(codes)
        warnings.extend(warn)
        cultivar_recommendations = self._rank_cultivars(plant, context, goals)
        if cultivar_recommendations:
            breakdown.cultivar_score = min(max(cultivar_recommendations[0].score / 10, 0), 8)
        breakdown.total_score = round(sum(value for key, value in breakdown.model_dump().items() if key != "total_score"), 2)
        recommendation_type = _recommendation_type(reason_codes)
        return PlantRecommendation(
            plant_slug=plant.slug or plant.common_name.lower().replace(" ", "_"),
            plant_common_name=plant.common_name,
            cultivar_recommendations=cultivar_recommendations,
            recommendation_type=recommendation_type,
            score=breakdown.total_score,
            score_breakdown=breakdown,
            reason_codes=_unique(reason_codes),
            warnings=_unique(warnings),
            explanation=_explanation(plant, recommendation_type, reason_codes, warnings),
        )

    def _companion_score(self, plant_slug: str, selected: list[str]) -> tuple[float, list[str], list[str]]:
        score = 0.0
        codes: list[str] = []
        warnings: list[str] = []
        for selected_slug in selected:
            pair_score = self.graph.score_pair(plant_slug, selected_slug) + self.graph.score_pair(selected_slug, plant_slug)
            score += pair_score
            edges = self.graph.get_neighbors(plant_slug) + self.graph.get_neighbors(selected_slug)
            for edge in edges:
                if {edge.source_plant_slug, edge.target_plant_slug} != {plant_slug, selected_slug}:
                    continue
                if edge.relationship_type == "beneficial":
                    codes.append("COMPANION_WITH_SELECTED_PLANT")
                elif edge.relationship_type == "guild":
                    codes.append("GUILD_WITH_SELECTED_PLANT")
                elif edge.relationship_type == "pest_deterrent":
                    codes.append("PEST_DETERRENT_COMPANION")
                elif edge.relationship_type == "pollinator_support":
                    codes.append("POLLINATOR_SUPPORT")
                elif edge.relationship_type == "nutrient_support":
                    codes.append("NUTRIENT_SUPPORT")
                elif edge.relationship_type == "avoid":
                    codes.append("AVOID_RELATIONSHIP")
                    warnings.append(_gardener_warning(edge.rationale))
                elif edge.relationship_type == "disease_risk":
                    codes.append("DISEASE_RISK")
                    warnings.append(_gardener_warning(edge.rationale))
                elif edge.relationship_type == "pest_risk":
                    codes.append("PEST_RISK")
                    warnings.append(_gardener_warning(edge.rationale))
                elif edge.relationship_type == "allelopathy":
                    codes.append("ALLELOPATHY_RISK")
                    warnings.append(_gardener_warning(edge.rationale))
                if edge.relationship_type in STRONG_NEGATIVE_RELATIONSHIP_TYPES and edge.score <= -20:
                    score -= 25
        return round(score, 2), codes, warnings

    def _family_score(self, plant_slug: str, selected: list[str]) -> tuple[float, list[str], list[str]]:
        score = 0.0
        codes: list[str] = []
        warnings: list[str] = []
        for selected_slug in selected:
            warning = self.family_service.get_family_conflict_warning(plant_slug, selected_slug)
            if warning:
                score -= 5
                codes.append("SAME_FAMILY_WARNING")
                warnings.append(warning)
        return score, codes, warnings

    def _rank_cultivars(self, plant: Plant, context: GardenContextDTO, goals: GardenGoalInput) -> list[CultivarRecommendation]:
        ranked: list[CultivarRecommendation] = []
        season = context.frost.growing_season_days
        for cultivar in self.cultivars_by_plant.get(plant.id, []):
            score = 0.0
            codes: list[str] = []
            maturity = cultivar.days_to_maturity_max or cultivar.days_to_maturity_min or plant.days_to_maturity or plant.typical_days_to_maturity_max
            if season and maturity and maturity <= season:
                score += 20
                codes.append("CULTIVAR_DAYS_TO_MATURITY_FIT")
            if cultivar.disease_resistance:
                score += 10
                codes.append("CULTIVAR_DISEASE_RESISTANCE")
            if context.geometry.area_sq_ft < 100 and (cultivar.compact_variety or cultivar.container_friendly):
                score += 8
                codes.append("SPACE_FIT")
            if not codes:
                codes.append("FALLBACK_TO_SPECIES_DEFAULTS")
            ranked.append(CultivarRecommendation(cultivar_slug=cultivar.slug, cultivar_name=cultivar.cultivar_name, score=round(score, 2), reason_codes=codes))
        return sorted(ranked, key=lambda item: (-item.score, item.cultivar_name))[:3]

    def _selected_warnings(self, selected: list[str]) -> list[RecommendationWarning]:
        warnings: list[RecommendationWarning] = []
        for conflict in self.graph.find_conflicts(selected):
            warnings.append(
                RecommendationWarning(
                    warning_type=conflict.relationship_type,
                    plant_slugs=[conflict.source_plant_slug, conflict.target_plant_slug],
                    severity="high" if conflict.score <= -20 else "medium",
                    message=f"{_gardener_warning(conflict.rationale)} {conflict.suggested_action}",
                )
            )
        for index, plant_slug in enumerate(selected):
            for other_slug in selected[index + 1 :]:
                warning = self.family_service.get_family_conflict_warning(plant_slug, other_slug)
                if warning:
                    warnings.append(RecommendationWarning(warning_type="same_family", plant_slugs=[plant_slug, other_slug], severity="low", message=warning))
        return warnings

    def _apply_diversity(self, recommendations: list[PlantRecommendation], goals: GardenGoalInput) -> list[PlantRecommendation]:
        if "combination" not in goals.goals:
            return recommendations
        seen_types: set[str] = set()
        for recommendation in sorted(recommendations, key=lambda item: -item.score):
            plant = self.plants_by_slug.get(recommendation.plant_slug)
            family_type = "herb" if plant and _is_herb(plant) else "flower" if plant and plant.flower else "food" if plant and plant.edible else plant.plant_type if plant else "other"
            if family_type not in seen_types:
                recommendation.score_breakdown.diversity_score += 5
                recommendation.score_breakdown.total_score += 5
                recommendation.score += 5
                recommendation.reason_codes = _unique([*recommendation.reason_codes, "DIVERSITY_MATCH"])
                seen_types.add(family_type)
        return recommendations


def _hardiness_score(plant: Plant, context: GardenContextDTO) -> tuple[float, list[str], list[str]]:
    zone = _zone_number(context.hardiness.zone)
    if zone is None:
        return 0, [], ["Hardiness zone is unknown; hardiness fit was not scored."]
    min_zone = plant.min_hardiness_zone or plant.min_zone
    max_zone = plant.max_hardiness_zone or plant.max_zone
    if min_zone <= zone <= max_zone:
        return 25, ["HARDINESS_MATCH"], []
    if plant.perennial or plant.tree or plant.is_tree or plant.is_shrub:
        return -100, ["HARDINESS_MISMATCH"], [f"{plant.common_name} may not overwinter in zone {context.hardiness.zone}."]
    return -10, ["HARDINESS_MISMATCH"], [f"{plant.common_name} is outside its listed hardiness range, but annual crops may still work if the season is long enough."]


def _sunlight_score(plant: Plant, context: GardenContextDTO) -> tuple[float, list[str], list[str]]:
    garden_sun = context.sunlight.category or "unknown"
    plant_sun = _normalize_sunlight(plant.sunlight_requirement)
    if garden_sun == "unknown":
        return 0, [], ["Sunlight category is unknown."]
    if garden_sun == plant_sun:
        return 25, ["SUNLIGHT_MATCH"], []
    if plant_sun in {"full_sun", "part_sun"} and garden_sun in {"full_sun", "part_sun"}:
        return 12, ["SUNLIGHT_MATCH"], []
    if plant_sun == "full_sun" and garden_sun == "shade":
        return -40, ["SUNLIGHT_MISMATCH"], [f"{plant.common_name} usually needs full sun."]
    return -25, ["SUNLIGHT_MISMATCH"], [f"{plant.common_name} sunlight needs may not match this garden."]


def _water_score(plant: Plant, context: GardenContextDTO) -> tuple[float, list[str], list[str]]:
    precip = context.precipitation.category
    water = plant.water_requirement.lower()
    if not precip:
        return 0, [], []
    if ("low" in water and precip == "low") or ("medium" in water and precip == "medium") or ("high" in water and precip == "high"):
        return 10, ["WATER_MATCH"], []
    if "high" in water and precip == "low":
        return -10, ["WATER_WARNING"], [f"{plant.common_name} may need irrigation in a low-precipitation garden."]
    if "low" in water and precip == "high":
        return -5, ["WATER_WARNING"], [f"{plant.common_name} may need well-drained soil in a wetter garden."]
    return 0, [], []


def _goal_score(plant: Plant, goals: GardenGoalInput) -> tuple[float, list[str]]:
    score = 0.0
    codes: list[str] = []
    goal_values = set(goals.goals)
    if goals.primary_goal:
        goal_values.add(goals.primary_goal)
    if "food" in goal_values and plant.edible:
        score += 20
        codes.append("FOOD_GOAL_MATCH")
    if "flowers" in goal_values and (plant.flower or plant.ornamental):
        score += 18
        codes.append("FLOWER_GOAL_MATCH")
    if "pollinators" in goal_values and (plant.pollinator_value_score or 0) >= 7:
        score += 18
        codes.append("POLLINATOR_GOAL_MATCH")
    if ("shade" in goal_values or "trees" in goal_values) and (plant.tree or plant.is_tree or plant.is_shrub or (plant.typical_height_inches or 0) >= 72):
        score += 18
        codes.append("SHADE_GOAL_MATCH")
    if "low_maintenance" in goal_values and plant.maintenance_level.lower() == "low":
        score += 15
        codes.append("LOW_MAINTENANCE_MATCH")
    if "herbs" in goal_values and _is_herb(plant):
        score += 15
        codes.append("FOOD_GOAL_MATCH")
    if "fruit" in goal_values and (plant.plant_category or "").lower() in {"fruit", "berry", "tree fruit"}:
        score += 18
        codes.append("FOOD_GOAL_MATCH")
    if "native_plants" in goal_values and plant.is_native_option:
        score += 15
        codes.append("NATIVE_PLANT_MATCH")
    return score, codes


def _maintenance_score(plant: Plant, preference: str) -> tuple[float, list[str]]:
    level = plant.maintenance_level.lower()
    if preference == "low":
        if level == "low":
            return 15, ["LOW_MAINTENANCE_MATCH"]
        if level == "high" or level == "intensive":
            return -20, ["MAINTENANCE_WARNING"]
    if preference == "moderate":
        if level == "low":
            return 5, ["LOW_MAINTENANCE_MATCH"]
        if level == "moderate":
            return 10, ["LOW_MAINTENANCE_MATCH"]
        return -5, ["MAINTENANCE_WARNING"]
    return 0, []


def _space_score(plant: Plant, context: GardenContextDTO, goals: GardenGoalInput) -> tuple[float, list[str], list[str]]:
    area = context.geometry.area_sq_ft
    spread = plant.typical_spread_inches or plant.typical_spacing_inches or plant.spacing_inches or 12
    footprint = max((spread * spread) / 144, 1)
    if area < 100 and (plant.tree or plant.is_tree or plant.is_shrub) and "shade" not in goals.goals and "trees" not in goals.goals:
        return -25, ["SPACE_WARNING"], [f"{plant.common_name} may be too large for a small garden."]
    if footprint <= area * 0.25:
        return 8, ["SPACE_FIT"], []
    return -10, ["SPACE_WARNING"], [f"{plant.common_name} may need more space than this garden can comfortably provide."]


def _beginner_score(plant: Plant, experience: str) -> tuple[float, list[str]]:
    if experience != "beginner":
        return 0, []
    beginner_score = plant.beginner_friendliness_score
    if beginner_score is not None and beginner_score >= 7:
        return 8, ["BEGINNER_FRIENDLY"]
    if plant.maintenance_level.lower() in {"high", "intensive"}:
        return -8, ["MAINTENANCE_WARNING"]
    return 0, []


def _chaos_score(plant: Plant, context: GardenContextDTO, goals: GardenGoalInput) -> tuple[float, list[str], list[str]]:
    if goals.planting_style != "chaos":
        return 0, [], []
    slug = plant.slug or plant.common_name.lower().replace(" ", "_")
    codes: list[str] = []
    warnings: list[str] = []
    score = 0.0
    maintenance = (plant.maintenance_level or "").lower()
    if maintenance == "low":
        score += 12
        codes.append("CHAOS_LOW_MAINTENANCE")
    elif maintenance in {"high", "intensive"}:
        score -= 18
        codes.append("MAINTENANCE_WARNING")
    if getattr(plant, "direct_sow_allowed", False):
        score += 12
        codes.append("CHAOS_DIRECT_SOW")
    if getattr(plant, "transplant_recommended", False) and not getattr(plant, "direct_sow_allowed", False):
        score -= 8
        codes.append("CHAOS_SPACE_WARNING")
    if slug in {"bean", "beans", "pea", "peas", "lettuce", "kale", "calendula", "marigold", "nasturtium", "zinnia", "sunflower", "dill", "cilantro"}:
        score += 14
        codes.append("CHAOS_EASY_CROP")
    if plant.flower or plant.ornamental or (plant.pollinator_value_score or 0) >= 7:
        score += 10
        codes.append("CHAOS_POLLINATOR")
    if _is_herb(plant):
        score += 6
        codes.append("CHAOS_EASY_CROP")
    spacing = plant.row_spacing_inches or plant.spacing_inches or plant.typical_spread_inches or 12
    if spacing >= 48 and slug not in {"sunflower"}:
        score -= 8
        codes.append("CHAOS_SPACE_WARNING")
    if slug in {"squash", "pumpkin", "melon", "zucchini"} and context.geometry.area_sq_ft < 150:
        score -= 12
        warnings.append(f"{plant.common_name} can sprawl; use it in chaos mode only if you have enough open space.")
    if plant.tree or plant.is_tree or plant.is_shrub:
        if "trees" not in goals.goals and "fruit" not in goals.goals and goals.primary_goal not in {"trees", "fruit"}:
            score -= 30
            codes.append("CHAOS_TREE_WARNING")
            warnings.append(f"{plant.common_name} is better handled as a separate tree or bush placement, not scattered through a chaos garden.")
    return score, codes, warnings


def _zone_number(zone: str | None) -> int | None:
    if not zone:
        return None
    digits = "".join(ch for ch in zone if ch.isdigit())
    return int(digits) if digits else None


def _normalize_sunlight(value: str) -> str:
    return value.lower().replace(" ", "_").replace("-", "_")


def _is_herb(plant: Plant) -> bool:
    return "herb" in plant.plant_type.lower() or (plant.plant_category or "").lower() == "herb"


def _recommendation_type(codes: list[str]) -> str:
    if "AVOID_RELATIONSHIP" in codes or "ALLELOPATHY_RISK" in codes or "DISEASE_RISK" in codes:
        return "warning_only"
    if "COMPANION_WITH_SELECTED_PLANT" in codes or "GUILD_WITH_SELECTED_PLANT" in codes:
        return "suggested_companion"
    if any(code.endswith("_GOAL_MATCH") for code in codes):
        return "goal_fit"
    return "climate_fit"


def _gardener_warning(message: str) -> str:
    internal_nightshade = "Nightshade crops can share disease and pest pressure; close clustering should be flagged as a risk rather than a beneficial pairing."
    if message == internal_nightshade:
        return "Tomatoes, peppers, eggplants, and potatoes are all nightshades. Try not to cluster them too closely because they can share pest and disease pressure."
    return (
        message.replace("flagged as a risk rather than a beneficial pairing", "treated as something to separate in the garden")
        .replace("beneficial pairing", "helpful pairing")
    )


def _explanation(plant: Plant, recommendation_type: str, codes: list[str], warnings: list[str]) -> str:
    if recommendation_type == "warning_only":
        return f"{plant.common_name} has a warning with selected plants: {warnings[0] if warnings else 'review placement before adding.'}"
    reasons = []
    if "SUNLIGHT_MATCH" in codes:
        reasons.append("fits the garden sunlight")
    if "FOOD_GOAL_MATCH" in codes:
        reasons.append("supports food or herb goals")
    if "FLOWER_GOAL_MATCH" in codes or "POLLINATOR_GOAL_MATCH" in codes:
        reasons.append("supports flowers or pollinators")
    if "COMPANION_WITH_SELECTED_PLANT" in codes:
        reasons.append("pairs well with a selected plant")
    if "BEGINNER_FRIENDLY" in codes:
        reasons.append("is beginner-friendly")
    return f"{plant.common_name} is recommended because it " + ", ".join(reasons or ["fits the current scoring model"]) + "."


def _summary(context: GardenContextDTO, goals: GardenGoalInput) -> str:
    sun = context.sunlight.category or "unknown sunlight"
    zone = context.hardiness.zone or "unknown zone"
    goal_text = ", ".join(goals.goals or ([goals.primary_goal] if goals.primary_goal else ["general garden"]))
    return f"Based on your {sun.replace('_', ' ')} garden, zone {zone} estimate, and {goal_text} goals, JakeGPT recommends plants using climate fit, space, family risk, and companion graph evidence."


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
