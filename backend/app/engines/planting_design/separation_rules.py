from app.models import Plant
from app.services.companions import CompanionGraphService, STRONG_NEGATIVE_RELATIONSHIP_TYPES

from app.engines.planting_design.schemas import SeparationRule


NIGHTSHADES = {"tomato", "pepper", "eggplant", "potato"}
ISOLATE_PLANTS = {"mint", "fennel", "black_walnut", "black-walnut"}


class SeparationRuleBuilder:
    def build(self, plants: list[Plant], companion_graph: CompanionGraphService | None = None) -> list[SeparationRule]:
        slugs = [_plant_slug(plant) for plant in plants]
        rules: list[SeparationRule] = []
        seen: set[tuple[str, str, str]] = set()
        if companion_graph is not None:
            for index, source in enumerate(slugs):
                for target in slugs[index + 1 :]:
                    edge = companion_graph.get_relationship(source, target) or companion_graph.get_relationship(target, source)
                    if edge is None or edge.score >= 0:
                        continue
                    identity = tuple(sorted([source, target]) + [edge.relationship_type])
                    if identity in seen:
                        continue
                    seen.add(identity)
                    rules.append(
                        SeparationRule(
                            plant_slugs=[source, target],
                            relationship_type=edge.relationship_type,
                            severity="high" if edge.relationship_type in STRONG_NEGATIVE_RELATIONSHIP_TYPES or edge.score <= -20 else "medium",
                            placement_guidance="keep_far_apart" if edge.relationship_type in STRONG_NEGATIVE_RELATIONSHIP_TYPES else "do_not_cluster",
                            rationale=_friendly_rationale(source, target, edge.relationship_type, edge.rationale),
                        )
                    )
        for source in slugs:
            if source in ISOLATE_PLANTS:
                rules.append(
                    SeparationRule(
                        plant_slugs=[source],
                        relationship_type="isolation",
                        severity="high" if source in {"mint", "fennel"} else "medium",
                        placement_guidance="containerize" if source == "mint" else "isolate",
                        rationale=_isolation_copy(source),
                    )
                )
        selected_nightshades = sorted(set(slugs) & NIGHTSHADES)
        if len(selected_nightshades) >= 2:
            rules.append(
                SeparationRule(
                    plant_slugs=selected_nightshades,
                    relationship_type="same_family",
                    severity="medium",
                    placement_guidance="do_not_cluster",
                    rationale="Tomatoes, peppers, eggplants, and potatoes are all nightshades. Try not to cluster them too closely because they can share pest and disease pressure.",
                )
            )
        return _unique_rules(rules)


def _friendly_rationale(source: str, target: str, relationship_type: str, fallback: str) -> str:
    if relationship_type == "disease_risk":
        return f"{_name(source)} and {_name(target)} may share disease pressure. Do not cluster them together."
    if relationship_type == "pest_risk":
        return f"{_name(source)} and {_name(target)} may attract or share pest pressure. Keep them separated where practical."
    if relationship_type == "allelopathy":
        return f"{_name(source)} may suppress nearby plants. Isolate it from {_name(target)}."
    if relationship_type == "avoid":
        return f"{_name(source)} and {_name(target)} should not be planted close together."
    if relationship_type == "competition":
        return f"{_name(source)} and {_name(target)} may compete for space, light, or nutrients. Avoid tight clustering."
    return fallback.replace("flagged as a risk rather than a beneficial pairing", "kept separated in the garden").replace("beneficial pairing", "helpful pairing")


def _isolation_copy(slug: str) -> str:
    if slug == "mint":
        return "Mint can spread aggressively. Consider a container or isolated patch."
    if slug == "fennel":
        return "Fennel is best isolated from most vegetables."
    return f"{_name(slug)} is best handled as an isolated planting."


def _plant_slug(plant: Plant) -> str:
    return getattr(plant, "slug", None) or plant.common_name.lower().replace(" ", "_")


def _name(slug: str) -> str:
    return slug.replace("_", " ").replace("-", " ").title()


def _unique_rules(rules: list[SeparationRule]) -> list[SeparationRule]:
    seen: set[tuple[str, ...]] = set()
    result: list[SeparationRule] = []
    for rule in rules:
        identity = tuple([*sorted(rule.plant_slugs), rule.relationship_type, rule.placement_guidance])
        if identity not in seen:
            seen.add(identity)
            result.append(rule)
    return result

