from dataclasses import dataclass, field
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Plant, PlantCompanionRelationship, PlantCultivar


RELATIONSHIP_WEIGHTS = {
    "beneficial": 20,
    "guild": 30,
    "pollinator_support": 12,
    "pest_deterrent": 10,
    "nutrient_support": 10,
    "shade_support": 8,
    "succession": 5,
    "neutral": 0,
    "competition": -10,
    "pest_risk": -15,
    "disease_risk": -20,
    "avoid": -35,
    "allelopathy": -50,
}

CONFIDENCE_MULTIPLIERS = {
    "high": 1.0,
    "medium": 0.65,
    "low": 0.3,
}

EVIDENCE_MULTIPLIERS = {
    "peer_reviewed": 1.0,
    "extension_service": 1.0,
    "master_gardener": 0.85,
    "seed_catalog": 0.65,
    "manual": 0.6,
    "traditional": 0.5,
    "generated_inference": 0.25,
}

POSITIVE_RELATIONSHIP_TYPES = {
    "beneficial",
    "guild",
    "pollinator_support",
    "pest_deterrent",
    "nutrient_support",
    "shade_support",
    "succession",
}

NEGATIVE_RELATIONSHIP_TYPES = {
    "avoid",
    "disease_risk",
    "pest_risk",
    "allelopathy",
    "competition",
}

STRONG_NEGATIVE_RELATIONSHIP_TYPES = {"avoid", "disease_risk", "pest_risk", "allelopathy"}


@dataclass(frozen=True)
class CompanionGraphEdge:
    source_plant_slug: str
    target_plant_slug: str
    relationship_type: str
    confidence: str
    evidence_type: str
    rationale: str
    relationship_direction: str
    min_distance_inches: int | None = None
    max_distance_inches: int | None = None
    source_notes: str | None = None
    source_cultivar_slug: str | None = None
    target_cultivar_slug: str | None = None
    canonical_relationship_id: int | None = None
    is_reverse: bool = False

    @property
    def score(self) -> float:
        return score_edge(self.relationship_type, self.confidence, self.evidence_type)

    @property
    def explanation(self) -> str:
        return (
            f"{self.source_plant_slug} -> {self.target_plant_slug}: "
            f"{self.relationship_type} ({self.confidence}, {self.evidence_type}); {self.rationale}"
        )


@dataclass(frozen=True)
class CompanionConflict:
    source_plant_slug: str
    target_plant_slug: str
    relationship_type: str
    score: float
    confidence: str
    rationale: str
    suggested_action: str


@dataclass(frozen=True)
class CompanionSuggestion:
    plant_slug: str
    score: float
    explanations: list[str] = field(default_factory=list)


def score_edge(relationship_type: str, confidence: str, evidence_type: str) -> float:
    relationship_weight = RELATIONSHIP_WEIGHTS.get(relationship_type, 0)
    confidence_multiplier = CONFIDENCE_MULTIPLIERS.get(confidence, 0.3)
    evidence_multiplier = EVIDENCE_MULTIPLIERS.get(evidence_type, 0.25)
    return relationship_weight * confidence_multiplier * evidence_multiplier


class CompanionGraphService:
    def __init__(
        self,
        relationships: Iterable[PlantCompanionRelationship] | None = None,
        plants: Iterable[Plant] | None = None,
        cultivars: Iterable[PlantCultivar] | None = None,
        db: Session | None = None,
    ) -> None:
        if db is not None:
            plants = db.scalars(select(Plant)).all()
            cultivars = db.scalars(select(PlantCultivar)).all()
            relationships = db.scalars(select(PlantCompanionRelationship)).all()

        self._plants_by_id = {plant.id: plant for plant in plants or []}
        self._cultivars_by_id = {cultivar.id: cultivar for cultivar in cultivars or []}
        self._edges_by_source: dict[str, list[CompanionGraphEdge]] = {}
        self._edges_by_pair: dict[tuple[str, str], list[CompanionGraphEdge]] = {}

        for relationship in relationships or []:
            edge = self._edge_from_relationship(relationship)
            if edge is None:
                continue
            self._add_edge(edge)
            if edge.relationship_direction == "symmetric":
                self._add_edge(
                    CompanionGraphEdge(
                        source_plant_slug=edge.target_plant_slug,
                        target_plant_slug=edge.source_plant_slug,
                        source_cultivar_slug=edge.target_cultivar_slug,
                        target_cultivar_slug=edge.source_cultivar_slug,
                        relationship_type=edge.relationship_type,
                        confidence=edge.confidence,
                        evidence_type=edge.evidence_type,
                        rationale=edge.rationale,
                        relationship_direction=edge.relationship_direction,
                        min_distance_inches=edge.min_distance_inches,
                        max_distance_inches=edge.max_distance_inches,
                        source_notes=edge.source_notes,
                        canonical_relationship_id=edge.canonical_relationship_id,
                        is_reverse=True,
                    )
                )

    @classmethod
    def from_db(cls, db: Session) -> "CompanionGraphService":
        return cls(db=db)

    def get_neighbors(self, plant_slug: str) -> list[CompanionGraphEdge]:
        return sorted(self._edges_by_source.get(plant_slug, []), key=lambda edge: (edge.target_plant_slug, edge.relationship_type))

    def get_positive_companions(self, plant_slug: str) -> list[CompanionGraphEdge]:
        return [edge for edge in self.get_neighbors(plant_slug) if edge.relationship_type in POSITIVE_RELATIONSHIP_TYPES and edge.score > 0]

    def get_negative_companions(self, plant_slug: str) -> list[CompanionGraphEdge]:
        return [edge for edge in self.get_neighbors(plant_slug) if edge.relationship_type in NEGATIVE_RELATIONSHIP_TYPES and edge.score < 0]

    def get_relationship(self, source_plant_slug: str, target_plant_slug: str) -> CompanionGraphEdge | None:
        edges = self._edges_by_pair.get((source_plant_slug, target_plant_slug), [])
        if not edges:
            return None
        return sorted(edges, key=lambda edge: (edge.score < 0, abs(edge.score)), reverse=True)[0]

    def score_pair(self, source_plant_slug: str, target_plant_slug: str) -> float:
        return round(sum(edge.score for edge in self._edges_by_pair.get((source_plant_slug, target_plant_slug), [])), 3)

    def find_conflicts(self, selected_plant_slugs: list[str]) -> list[CompanionConflict]:
        selected = set(selected_plant_slugs)
        conflicts: list[CompanionConflict] = []
        seen: set[tuple[str, str, str, int | None]] = set()
        for source_slug in selected_plant_slugs:
            for edge in self.get_neighbors(source_slug):
                if edge.target_plant_slug not in selected or edge.relationship_type not in NEGATIVE_RELATIONSHIP_TYPES:
                    continue
                identity = self._conflict_identity(edge)
                if identity in seen:
                    continue
                seen.add(identity)
                conflicts.append(
                    CompanionConflict(
                        source_plant_slug=edge.source_plant_slug,
                        target_plant_slug=edge.target_plant_slug,
                        relationship_type=edge.relationship_type,
                        score=round(edge.score, 3),
                        confidence=edge.confidence,
                        rationale=edge.rationale,
                        suggested_action=_suggested_action(edge),
                    )
                )
        return sorted(conflicts, key=lambda conflict: (conflict.score, conflict.source_plant_slug, conflict.target_plant_slug))

    def suggest_companions(
        self,
        selected_plant_slugs: list[str],
        candidate_plant_slugs: list[str],
        limit: int = 20,
        include_strong_negatives: bool = False,
    ) -> list[CompanionSuggestion]:
        selected = set(selected_plant_slugs)
        suggestions: list[CompanionSuggestion] = []
        for candidate_slug in candidate_plant_slugs:
            if candidate_slug in selected:
                continue
            score = 0.0
            explanations: list[str] = []
            has_strong_negative = False
            for selected_slug in selected_plant_slugs:
                edges = self._edges_by_pair.get((candidate_slug, selected_slug), []) + self._edges_by_pair.get((selected_slug, candidate_slug), [])
                for edge in edges:
                    edge_score = edge.score
                    score += edge_score
                    explanations.append(_suggestion_explanation(edge, selected_slug))
                    if edge.relationship_type in STRONG_NEGATIVE_RELATIONSHIP_TYPES and edge_score <= -5:
                        has_strong_negative = True
            if has_strong_negative and not include_strong_negatives:
                continue
            if score > 0 or include_strong_negatives and explanations:
                suggestions.append(CompanionSuggestion(plant_slug=candidate_slug, score=round(score, 3), explanations=explanations))
        return sorted(suggestions, key=lambda suggestion: (-suggestion.score, suggestion.plant_slug))[:limit]

    def _add_edge(self, edge: CompanionGraphEdge) -> None:
        self._edges_by_source.setdefault(edge.source_plant_slug, []).append(edge)
        self._edges_by_pair.setdefault((edge.source_plant_slug, edge.target_plant_slug), []).append(edge)

    def _edge_from_relationship(self, relationship: PlantCompanionRelationship) -> CompanionGraphEdge | None:
        source_plant = self._plants_by_id.get(relationship.source_plant_id)
        target_plant = self._plants_by_id.get(relationship.target_plant_id)
        if source_plant is None or target_plant is None:
            return None
        source_cultivar = self._cultivars_by_id.get(relationship.source_cultivar_id) if relationship.source_cultivar_id else None
        target_cultivar = self._cultivars_by_id.get(relationship.target_cultivar_id) if relationship.target_cultivar_id else None
        return CompanionGraphEdge(
            source_plant_slug=source_plant.slug or source_plant.common_name.lower().replace(" ", "-"),
            target_plant_slug=target_plant.slug or target_plant.common_name.lower().replace(" ", "-"),
            source_cultivar_slug=source_cultivar.slug if source_cultivar else None,
            target_cultivar_slug=target_cultivar.slug if target_cultivar else None,
            relationship_type=relationship.relationship_type,
            confidence=relationship.confidence,
            evidence_type=relationship.evidence_type,
            rationale=relationship.rationale,
            relationship_direction=relationship.relationship_direction,
            min_distance_inches=relationship.min_distance_inches,
            max_distance_inches=relationship.max_distance_inches,
            source_notes=relationship.source_notes,
            canonical_relationship_id=relationship.id,
        )

    @staticmethod
    def _conflict_identity(edge: CompanionGraphEdge) -> tuple[str, str, str, int | None]:
        if edge.relationship_direction == "symmetric":
            first, second = sorted([edge.source_plant_slug, edge.target_plant_slug])
            return (first, second, edge.relationship_type, edge.canonical_relationship_id)
        return (edge.source_plant_slug, edge.target_plant_slug, edge.relationship_type, edge.canonical_relationship_id)


def companion_notes(plants: list[Plant], relationships: list[PlantCompanionRelationship]) -> list[str]:
    selected = {plant.id: plant for plant in plants}
    notes: list[str] = []
    for rel in relationships:
        if rel.source_plant_id in selected and rel.target_plant_id in selected:
            notes.append(
                f"{selected[rel.source_plant_id].common_name.title()} and "
                f"{selected[rel.target_plant_id].common_name.title()}: "
                f"{rel.relationship_type}. {rel.rationale}"
            )
    return notes


def relationship_lookup(relationships: list[PlantCompanionRelationship]) -> dict[tuple[int, int], str]:
    lookup: dict[tuple[int, int], str] = {}
    for rel in relationships:
        lookup[(rel.source_plant_id, rel.target_plant_id)] = rel.relationship_type
        if rel.relationship_direction == "symmetric":
            lookup[(rel.target_plant_id, rel.source_plant_id)] = rel.relationship_type
    return lookup


def _suggested_action(edge: CompanionGraphEdge) -> str:
    if edge.relationship_type == "allelopathy":
        return "Keep separated; allelopathic relationships may suppress sensitive plants."
    if edge.relationship_type == "avoid":
        return "Keep separate unless a stronger source later narrows the concern."
    if edge.relationship_type in {"disease_risk", "pest_risk"}:
        return "Avoid close clustering and rotate locations where possible."
    if edge.relationship_type == "competition":
        if edge.min_distance_inches or edge.max_distance_inches:
            return "Increase spacing between these plants to reduce competition."
        return "Avoid dense planting together; separate if space allows."
    return "Review before placing these plants together."


def _suggestion_explanation(edge: CompanionGraphEdge, selected_slug: str) -> str:
    direction = "supports" if edge.score > 0 else "conflicts with"
    other_slug = edge.target_plant_slug if edge.source_plant_slug == selected_slug else edge.source_plant_slug
    return (
        f"{edge.relationship_type} {direction} {selected_slug} via {other_slug}; "
        f"score {edge.score:.2f}. {edge.rationale}"
    )
