from app.models import Plant, PlantCultivar
from app.services.companions import CompanionGraphService, NEGATIVE_RELATIONSHIP_TYPES, POSITIVE_RELATIONSHIP_TYPES

from app.engines.planting_design.schemas import PlantRole


PRIMARY_CROPS = {"tomato", "pepper", "eggplant", "cucumber", "bean", "beans", "pea", "peas", "corn"}
LEAFY_GREENS = {"lettuce", "spinach", "kale", "arugula"}
ROOT_CROPS = {"carrot", "beet", "radish", "onion", "garlic"}
SPRAWLING = {"squash", "pumpkin", "melon", "zucchini"}
TRELLISED = {"pea", "peas", "bean", "beans", "cucumber", "tomato"}
ISOLATE = {"mint", "fennel", "black_walnut", "black-walnut"}
HERBS = {"basil", "dill", "cilantro", "parsley", "thyme", "sage", "rosemary", "oregano", "mint", "fennel"}


class PlantRoleClassifier:
    def classify(
        self,
        plant: Plant,
        cultivar: PlantCultivar | None = None,
        companion_graph: CompanionGraphService | None = None,
        selected_slugs: list[str] | None = None,
    ) -> list[PlantRole]:
        slug = _plant_slug(plant)
        selected_slugs = selected_slugs or []
        roles: list[PlantRole] = []
        cultivar_slug = getattr(cultivar, "slug", None)

        def add(role: str, rationale: str) -> None:
            if not any(existing.role == role for existing in roles):
                roles.append(PlantRole(plant_slug=slug, cultivar_slug=cultivar_slug, role=role, rationale=rationale))

        if getattr(plant, "tree", False) or getattr(plant, "is_tree", False):
            add("tree", "Tree crops need a permanent zone separate from annual crop rows or most raised beds.")
        if getattr(plant, "is_shrub", False) or "blueberry" in slug or "raspberry" in slug or "blackberry" in slug:
            add("shrub", "Shrubs and berry bushes need a separate woody/perennial zone.")
        if getattr(plant, "perennial", False):
            add("perennial", "Perennials should be placed where they can remain across seasons.")
        if slug in ISOLATE or _has_strong_negative_edges(slug, companion_graph):
            add("avoid_or_isolate", f"{plant.common_name.title()} should be isolated or handled carefully near vegetables.")
        if _is_herb(plant, slug):
            if _has_positive_edge_to_selected(slug, selected_slugs, companion_graph):
                add("companion_herb", f"{plant.common_name.title()} has companion value near selected crops.")
            else:
                add("filler_crop", f"{plant.common_name.title()} can fill small spaces around primary crops.")
        if getattr(plant, "flower", False) or getattr(plant, "ornamental", False) or (getattr(plant, "pollinator_value_score", None) or 0) >= 7:
            add("pollinator_flower", f"{plant.common_name.title()} can support pollinators.")
            add("border_plant", "Pollinator flowers work well repeated along edges and row ends.")
        if slug in PRIMARY_CROPS and not any(role.role in {"tree", "shrub"} for role in roles):
            add("primary_crop", f"{plant.common_name.title()} is a main production crop.")
        if slug in TRELLISED or _support_likely(plant, cultivar):
            add("trellised_crop", f"{plant.common_name.title()} benefits from support or vertical placement.")
        if slug in LEAFY_GREENS:
            add("leafy_green", f"{plant.common_name.title()} works well as a leafy green patch.")
            add("filler_crop", "Leafy greens can fill gaps around larger crops.")
        if slug in ROOT_CROPS:
            add("root_crop", f"{plant.common_name.title()} is best handled as a root-crop row or patch.")
        if slug in SPRAWLING:
            add("sprawling_crop", f"{plant.common_name.title()} can sprawl and should be given an edge or dedicated area.")
        if _height_inches(plant, cultivar) >= 72 and not any(role.role == "tree" for role in roles):
            add("tall_crop", f"{plant.common_name.title()} is tall enough to prefer the north side.")
        if not roles:
            add("filler_crop", f"{plant.common_name.title()} can be used as a flexible crop in the design.")
        return roles


def _plant_slug(plant: Plant) -> str:
    return getattr(plant, "slug", None) or plant.common_name.lower().replace(" ", "_")


def _is_herb(plant: Plant, slug: str) -> bool:
    return slug in HERBS or "herb" in ((getattr(plant, "plant_type", "") or "").lower()) or (getattr(plant, "plant_category", "") or "").lower() == "herb"


def _support_likely(plant: Plant, cultivar: PlantCultivar | None) -> bool:
    notes = " ".join(str(value or "") for value in [getattr(plant, "planting_notes", None), getattr(cultivar, "notes", None) if cultivar else None]).lower()
    return "trellis" in notes or "support" in notes or "stake" in notes


def _height_inches(plant: Plant, cultivar: PlantCultivar | None) -> int:
    override = getattr(cultivar, "height_inches_override", None) if cultivar else None
    return int(override or getattr(plant, "typical_height_inches", None) or 0)


def _has_positive_edge_to_selected(slug: str, selected_slugs: list[str], companion_graph: CompanionGraphService | None) -> bool:
    if companion_graph is None:
        return False
    for selected in selected_slugs:
        edge = companion_graph.get_relationship(slug, selected) or companion_graph.get_relationship(selected, slug)
        if edge and edge.relationship_type in POSITIVE_RELATIONSHIP_TYPES and edge.score > 0:
            return True
    return False


def _has_strong_negative_edges(slug: str, companion_graph: CompanionGraphService | None) -> bool:
    if companion_graph is None:
        return False
    return any(edge.relationship_type in NEGATIVE_RELATIONSHIP_TYPES and edge.score <= -15 for edge in companion_graph.get_neighbors(slug))

