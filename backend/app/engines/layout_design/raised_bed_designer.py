from typing import Any

from app.models import Plant

from app.engines.layout_design.schemas import DesignedBed, DesignedPlanting, PlantSymbol, RaisedBedBlueprint
from app.engines.planting_design.schemas import PlantingDesignPlan


class RaisedBedLayoutDesigner:
    def design(self, design_plan: PlantingDesignPlan, plants: list[Plant], symbols: list[PlantSymbol], layout_options: Any | None = None) -> RaisedBedBlueprint:
        roles = _roles_by_slug(design_plan)
        symbol_by_slug = {symbol.plant_slug: symbol for symbol in symbols}
        plant_by_slug = {_slug(plant): plant for plant in plants}
        woody = {slug for slug, slug_roles in roles.items() if slug_roles & {"tree", "shrub"}}
        settings = _bed_settings(layout_options)
        bed_count = max(1, settings["count"])
        beds = [
            DesignedBed(
                bed_id=f"bed-{index + 1}",
                bed_name=f"Bed {index + 1}",
                length_ft=settings["length_ft"],
                width_ft=settings["width_ft"],
            )
            for index in range(bed_count)
        ]
        unplaced = sorted(slug for slug in woody if slug in symbol_by_slug)

        assigned: set[str] = set()
        for cluster in design_plan.companion_clusters:
            anchor = cluster.anchor_plant_slug
            if anchor in woody or anchor not in symbol_by_slug or anchor in assigned:
                continue
            bed = beds[len(assigned) % bed_count]
            anchor_planting = _planting(anchor, symbol_by_slug, plant_by_slug, roles, zone="center", rationale=cluster.placement_guidance)
            bed.plantings.append(anchor_planting)
            assigned.add(anchor)
            for slug in cluster.companion_plant_slugs + cluster.filler_plant_slugs:
                if slug in woody or slug in assigned or slug not in symbol_by_slug:
                    continue
                bed.plantings.append(_planting(slug, symbol_by_slug, plant_by_slug, roles, zone="interplanted", near=[anchor], rationale=f"Interplant near {symbol_by_slug[anchor].display_name}."))
                assigned.add(slug)
            for slug in cluster.border_plant_slugs:
                if slug in woody or slug in assigned or slug not in symbol_by_slug:
                    continue
                border = _planting(slug, symbol_by_slug, plant_by_slug, roles, zone="border", near=[anchor], rationale="Repeat as bed-edge pollinator support.")
                bed.border_plantings.append(border)
                assigned.add(slug)
            bed.companion_clusters.append(cluster.cluster_id)
            bed.notes.append(cluster.placement_guidance)

        for slug in sorted(set(symbol_by_slug) - assigned - set(unplaced)):
            bed = _best_bed(beds)
            zone = "border" if roles.get(slug, set()) & {"pollinator_flower", "border_plant"} else "north_edge" if roles.get(slug, set()) & {"tall_crop", "trellised_crop"} else "center"
            planting = _planting(slug, symbol_by_slug, plant_by_slug, roles, zone=zone, rationale=_rationale(slug, roles))
            if zone == "border":
                bed.border_plantings.append(planting)
            else:
                bed.plantings.append(planting)
            assigned.add(slug)

        warnings = [warning for warning in design_plan.warnings if "tree" in warning.lower() or "raised bed" in warning.lower()]
        if unplaced:
            warnings.append("Tree and shrub crops are kept outside raised beds unless using confirmed dwarf or compact varieties.")
        for bed in beds:
            bed.symbol_legend = _legend_for_bed(bed, symbol_by_slug)
            bed.warnings = warnings[:]
            if bed.border_plantings and "Border flowers are repeated around bed edges." not in bed.notes:
                bed.notes.append("Border flowers are repeated around bed edges.")

        return RaisedBedBlueprint(beds=beds, unplaced_plants=unplaced, tree_shrub_symbols=[symbol_by_slug[slug].symbol for slug in unplaced])


def _planting(
    slug: str,
    symbol_by_slug: dict[str, PlantSymbol],
    plant_by_slug: dict[str, Plant],
    roles: dict[str, set[str]],
    *,
    zone: str,
    rationale: str,
    near: list[str] | None = None,
) -> DesignedPlanting:
    plant = plant_by_slug.get(slug)
    return DesignedPlanting(
        plant_slug=slug,
        cultivar_slug=symbol_by_slug[slug].cultivar_slug,
        symbol=symbol_by_slug[slug].symbol,
        quantity=_quantity(plant),
        role=sorted(roles.get(slug, {"filler_crop"}))[0],
        approximate_zone=zone,
        near_plant_slugs=near or [],
        rationale=rationale,
    )


def _bed_settings(layout_options: Any | None) -> dict[str, int | float]:
    raw = getattr(layout_options, "raised_beds", None) if layout_options is not None else None
    raw = raw if isinstance(raw, dict) else {}
    return {
        "count": int(raw.get("count") or raw.get("bed_count") or raw.get("number_of_beds") or 2),
        "length_ft": float(raw.get("length_ft") or raw.get("bed_length_ft") or 8),
        "width_ft": float(raw.get("width_ft") or raw.get("bed_width_ft") or 4),
    }


def _roles_by_slug(design_plan: PlantingDesignPlan) -> dict[str, set[str]]:
    roles: dict[str, set[str]] = {}
    for role in design_plan.plant_roles:
        roles.setdefault(role.plant_slug, set()).add(role.role)
    return roles


def _best_bed(beds: list[DesignedBed]) -> DesignedBed:
    return sorted(beds, key=lambda bed: len(bed.plantings) + len(bed.border_plantings))[0]


def _legend_for_bed(bed: DesignedBed, symbol_by_slug: dict[str, PlantSymbol]) -> list[PlantSymbol]:
    slugs = []
    for planting in [*bed.plantings, *bed.border_plantings]:
        if planting.plant_slug not in slugs:
            slugs.append(planting.plant_slug)
    return [symbol_by_slug[slug] for slug in slugs if slug in symbol_by_slug]


def _quantity(plant: Plant | None) -> int:
    if plant is None:
        return 1
    spacing = max(6, int(getattr(plant, "spacing_inches", None) or 18))
    if getattr(plant, "flower", False) or (getattr(plant, "pollinator_value_score", None) or 0) >= 7:
        return 8
    if spacing <= 8:
        return 12
    if spacing <= 12:
        return 8
    if spacing <= 18:
        return 4
    return 2


def _rationale(slug: str, roles: dict[str, set[str]]) -> str:
    values = roles.get(slug, set())
    if values & {"pollinator_flower", "border_plant"}:
        return "Place around bed edges for pollinator support."
    if values & {"tall_crop", "trellised_crop"}:
        return "Place toward the north edge so it shades smaller crops less."
    if "sprawling_crop" in values:
        return "Use a bed edge where vines can trail without covering smaller crops."
    return "Placed with a mixed-bed pattern instead of an isolated block."


def _slug(plant: Plant) -> str:
    return getattr(plant, "slug", None) or plant.common_name.lower().replace(" ", "_")
