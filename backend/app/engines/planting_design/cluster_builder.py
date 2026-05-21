from app.models import Plant
from app.services.companions import CompanionGraphService, POSITIVE_RELATIONSHIP_TYPES, STRONG_NEGATIVE_RELATIONSHIP_TYPES

from app.engines.planting_design.schemas import CompanionCluster, PlantGroup, PlantRole


class CompanionClusterBuilder:
    def build(
        self,
        plants: list[Plant],
        plant_roles: list[PlantRole],
        companion_graph: CompanionGraphService | None = None,
        organization_style: str = "rows",
    ) -> tuple[list[CompanionCluster], list[PlantGroup], list[str]]:
        slugs = [_plant_slug(plant) for plant in plants]
        role_map = _roles_by_slug(plant_roles)
        clusters: list[CompanionCluster] = []
        groups: list[PlantGroup] = []
        pollinator_border: list[str] = []

        primary_slugs = [slug for slug in slugs if "primary_crop" in role_map.get(slug, set())]
        for anchor in primary_slugs:
            companions: list[str] = []
            borders: list[str] = []
            fillers: list[str] = []
            for candidate in slugs:
                if candidate == anchor or _strong_negative_between(anchor, candidate, companion_graph):
                    continue
                candidate_roles = role_map.get(candidate, set())
                if companion_graph is not None:
                    edge = companion_graph.get_relationship(anchor, candidate) or companion_graph.get_relationship(candidate, anchor)
                    if edge is None or edge.relationship_type not in POSITIVE_RELATIONSHIP_TYPES or edge.score <= 0:
                        continue
                if "companion_herb" in candidate_roles:
                    companions.append(candidate)
                elif "pollinator_flower" in candidate_roles or "border_plant" in candidate_roles:
                    borders.append(candidate)
                    pollinator_border.append(candidate)
                elif "filler_crop" in candidate_roles or "leafy_green" in candidate_roles:
                    fillers.append(candidate)
            if companions or borders or fillers:
                clusters.append(
                    CompanionCluster(
                        cluster_id=f"cluster-{anchor}",
                        anchor_plant_slug=anchor,
                        companion_plant_slugs=sorted(set(companions)),
                        border_plant_slugs=sorted(set(borders)),
                        filler_plant_slugs=sorted(set(fillers)),
                        rationale=f"{_name(anchor)} has nearby support plants that make the layout more diverse and useful.",
                        placement_guidance=_cluster_guidance(anchor, organization_style),
                    )
                )

        if pollinator_border:
            groups.append(
                PlantGroup(
                    group_id="pollinator-border",
                    group_type="pollinator_border",
                    primary_plants=[],
                    support_plants=sorted(set(pollinator_border)),
                    placement_strategy="Repeat flowers at row ends, bed edges, and garden borders instead of one isolated block.",
                    notes=["Use flowers as repeated border/support plants instead of one isolated block."],
                )
            )
        for slug in slugs:
            roles = role_map.get(slug, set())
            group = _group_for_roles(slug, roles, organization_style)
            if group:
                groups.append(group)
        if organization_style == "chaos":
            groups.append(
                PlantGroup(
                    group_id="chaos-mix",
                    group_type="chaos_mix",
                    primary_plants=[slug for slug in slugs if "tree" not in role_map.get(slug, set()) and "shrub" not in role_map.get(slug, set())],
                    support_plants=sorted(set(pollinator_border)),
                    placement_strategy="Scatter compatible plants in loose clusters and keep warned pairs apart.",
                    notes=["Chaos mode gives guidance rather than a detailed placement map."],
                )
            )
        return clusters, _unique_groups(groups), sorted(set(pollinator_border))


def _roles_by_slug(plant_roles: list[PlantRole]) -> dict[str, set[str]]:
    roles: dict[str, set[str]] = {}
    for role in plant_roles:
        roles.setdefault(role.plant_slug, set()).add(role.role)
    return roles


def _strong_negative_between(source: str, target: str, companion_graph: CompanionGraphService | None) -> bool:
    if companion_graph is None:
        return False
    edge = companion_graph.get_relationship(source, target) or companion_graph.get_relationship(target, source)
    return bool(edge and edge.relationship_type in STRONG_NEGATIVE_RELATIONSHIP_TYPES and edge.score < 0)


def _group_for_roles(slug: str, roles: set[str], organization_style: str) -> PlantGroup | None:
    if "tree" in roles or "shrub" in roles:
        return PlantGroup(group_id=f"woody-{slug}", group_type="tree_shrub_zone", primary_plants=[slug], placement_strategy="Place in a separate Trees & Bushes zone outside annual rows or raised beds.", notes=["Separate trees and shrubs from annual row crops."])
    if "sprawling_crop" in roles:
        return PlantGroup(group_id=f"edge-{slug}", group_type="sprawling_edge", primary_plants=[slug], placement_strategy="Place on an edge where vines can sprawl without covering smaller crops.", notes=["Keep sprawling crops near an edge."])
    if "trellised_crop" in roles and organization_style == "rows":
        return PlantGroup(group_id=f"trellis-{slug}", group_type="trellis_row", primary_plants=[slug], placement_strategy="Use a north-side or edge row with support.", notes=["Tall or trellised crops should not shade smaller crops."])
    if "leafy_green" in roles:
        return PlantGroup(group_id=f"leafy-{slug}", group_type="leafy_green_patch", primary_plants=[slug], placement_strategy="Use as a patch or filler near larger crops.", notes=["Leafy greens can fill gaps where spacing allows."])
    if "root_crop" in roles:
        return PlantGroup(group_id=f"root-{slug}", group_type="root_crop_row", primary_plants=[slug], placement_strategy="Use a simple row or patch where soil can stay loose.", notes=[])
    return None


def _cluster_guidance(anchor: str, organization_style: str) -> str:
    if organization_style == "raised_beds":
        return f"Place {_name(anchor)} with its herbs nearby and repeat flowers along bed edges."
    if organization_style == "rows":
        return f"Keep companion herbs in adjacent rows or interplanted notes near {_name(anchor)}; use flowers at row ends."
    if organization_style == "chaos":
        return f"Use {_name(anchor)} as a loose cluster anchor and scatter compatible herbs or flowers nearby."
    return f"Keep compatible herbs and flowers near {_name(anchor)} without crowding."


def _unique_groups(groups: list[PlantGroup]) -> list[PlantGroup]:
    seen: set[str] = set()
    result: list[PlantGroup] = []
    for group in groups:
        if group.group_id not in seen:
            seen.add(group.group_id)
            result.append(group)
    return result


def _plant_slug(plant: Plant) -> str:
    return getattr(plant, "slug", None) or plant.common_name.lower().replace(" ", "_")


def _name(slug: str) -> str:
    return slug.replace("_", " ").replace("-", " ").title()

