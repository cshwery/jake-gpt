from typing import Any

from app.models import Plant, PlantCultivar
from app.engines.layout_design.chaos_designer import ChaosLayoutDesigner
from app.engines.layout_design.placement_rules import placement_rules_from_design
from app.engines.layout_design.raised_bed_designer import RaisedBedLayoutDesigner
from app.engines.layout_design.row_designer import RowLayoutDesigner
from app.engines.layout_design.schemas import LayoutBlueprint, PlantSymbol, TreeShrubItem, TreeShrubSection
from app.engines.planting_design.schemas import PlantingDesignPlan


class LayoutDesignEngine:
    def __init__(
        self,
        row_designer: RowLayoutDesigner | None = None,
        raised_bed_designer: RaisedBedLayoutDesigner | None = None,
        chaos_designer: ChaosLayoutDesigner | None = None,
    ) -> None:
        self.row_designer = row_designer or RowLayoutDesigner()
        self.raised_bed_designer = raised_bed_designer or RaisedBedLayoutDesigner()
        self.chaos_designer = chaos_designer or ChaosLayoutDesigner()

    def create_blueprint(
        self,
        design_plan: PlantingDesignPlan,
        plants: list[Plant],
        cultivars: list[PlantCultivar] | None = None,
        garden_context: Any | None = None,
        layout_options: Any | None = None,
    ) -> LayoutBlueprint:
        layout_style = _style(design_plan.organization_style)
        symbols = build_symbols(plants, cultivars or [], design_plan)
        rules = placement_rules_from_design(design_plan)
        tree_section = tree_shrub_section(plants, symbols, design_plan)
        row_blueprint = self.row_designer.design(design_plan, plants, symbols) if layout_style == "rows" else None
        raised_blueprint = self.raised_bed_designer.design(design_plan, plants, symbols, layout_options) if layout_style == "raised_beds" else None
        chaos_blueprint = self.chaos_designer.design(design_plan, plants) if layout_style == "chaos" else None
        return LayoutBlueprint(
            layout_style=layout_style,
            summary=f"Layout blueprint converts planting design into concrete {layout_style.replace('_', ' ')} instructions.",
            plant_symbols=symbols,
            row_blueprint=row_blueprint,
            raised_bed_blueprint=raised_blueprint,
            chaos_blueprint=chaos_blueprint,
            tree_shrub_section=tree_section,
            placement_rules=rules,
            warnings=design_plan.warnings,
            assumptions=["LayoutBlueprint is deterministic and derived from PlantingDesignPlan."],
        )


def build_symbols(plants: list[Plant], cultivars: list[PlantCultivar], design_plan: PlantingDesignPlan) -> list[PlantSymbol]:
    cultivar_by_plant = {cultivar.plant_id: cultivar for cultivar in cultivars}
    primary_role_by_slug = {}
    for role in design_plan.plant_roles:
        primary_role_by_slug.setdefault(role.plant_slug, role.role)
    used: set[str] = set()
    symbols: list[PlantSymbol] = []
    for plant in plants:
        slug = _slug(plant)
        cultivar = cultivar_by_plant.get(plant.id)
        display = f"{plant.common_name.title()} — {cultivar.cultivar_name}" if cultivar else plant.common_name.title()
        symbol = _symbol(display, used)
        symbols.append(PlantSymbol(symbol=symbol, plant_slug=slug, cultivar_slug=cultivar.slug if cultivar else None, display_name=display, role=primary_role_by_slug.get(slug, "filler_crop")))
    return symbols


def tree_shrub_section(plants: list[Plant], symbols: list[PlantSymbol], design_plan: PlantingDesignPlan) -> TreeShrubSection | None:
    woody_slugs = {role.plant_slug for role in design_plan.plant_roles if role.role in {"tree", "shrub"}}
    if not woody_slugs:
        return None
    symbol_by_slug = {symbol.plant_slug: symbol for symbol in symbols}
    items = [
        TreeShrubItem(
            symbol=symbol_by_slug[slug].symbol,
            plant_slug=slug,
            cultivar_slug=symbol_by_slug[slug].cultivar_slug,
            display_name=symbol_by_slug[slug].display_name,
            placement_guidance="Place in a separate Trees & Bushes section outside annual rows or raised beds.",
            warning=next((warning for warning in design_plan.warnings if slug in warning.lower()), None),
        )
        for slug in sorted(woody_slugs)
        if slug in symbol_by_slug
    ]
    return TreeShrubSection(items=items) if items else None


def _style(value: str) -> str:
    if value == "raised_beds":
        return "raised_beds"
    if value == "chaos":
        return "chaos"
    if value in {"mixed", "grid", "intensive_grid"}:
        return "mixed" if value == "mixed" else "grid"
    return "rows"


def _slug(plant: Plant) -> str:
    return getattr(plant, "slug", None) or plant.common_name.lower().replace(" ", "_")


def _symbol(name: str, used: set[str]) -> str:
    words = [word for word in name.replace("—", " ").replace("-", " ").split() if word]
    candidates = ["".join(word[0].upper() for word in words[:2]), words[0][0].upper() if words else "P", (words[0][:2].title() if words else "P")]
    for candidate in candidates:
        if candidate and candidate not in used:
            used.add(candidate)
            return candidate
    base = candidates[0] or "P"
    index = 1
    while f"{base}{index}" in used:
        index += 1
    used.add(f"{base}{index}")
    return f"{base}{index}"
