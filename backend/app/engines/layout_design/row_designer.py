from app.models import Plant

from app.engines.layout_design.schemas import DesignedRow, PlantSymbol, RowBlueprint
from app.engines.planting_design.schemas import PlantingDesignPlan


class RowLayoutDesigner:
    def design(self, design_plan: PlantingDesignPlan, plants: list[Plant], symbols: list[PlantSymbol]) -> RowBlueprint:
        roles = _roles_by_slug(design_plan)
        symbol_by_slug = {symbol.plant_slug: symbol for symbol in symbols}
        plant_by_slug = {_slug(plant): plant for plant in plants}
        woody = {slug for slug, slug_roles in roles.items() if slug_roles & {"tree", "shrub"}}
        used: set[str] = set()
        rows: list[DesignedRow] = []

        for cluster in design_plan.companion_clusters:
            anchor = cluster.anchor_plant_slug
            if anchor in woody or anchor in used or anchor not in symbol_by_slug:
                continue
            companion = [slug for slug in cluster.companion_plant_slugs if slug in symbol_by_slug and slug not in woody]
            border = [slug for slug in cluster.border_plant_slugs if slug in symbol_by_slug and slug not in woody]
            filler = [slug for slug in cluster.filler_plant_slugs if slug in symbol_by_slug and slug not in woody and slug not in companion]
            rows.append(
                DesignedRow(
                    row_number=len(rows) + 1,
                    row_label=f"{_display(anchor, symbol_by_slug)} + nearby support",
                    primary_plants=[anchor],
                    companion_plants=companion + filler,
                    border_plants=border,
                    spacing_from_prior_row_inches=None if not rows else _row_spacing(plant_by_slug.get(anchor)),
                    in_row_spacing_inches=_in_row_spacing(plant_by_slug.get(anchor)),
                    row_role="trellis" if "trellised_crop" in roles.get(anchor, set()) else "primary_crop",
                    notes=[
                        cluster.placement_guidance,
                        *(
                            ["Tall or trellised crop placed toward the north edge."]
                            if roles.get(anchor, set()) & {"tall_crop", "trellised_crop"}
                            else []
                        ),
                        "Use border flowers at row ends instead of making one large flower block.",
                    ],
                )
            )
            used.update([anchor, *companion, *border, *filler])

        for slug in sorted(_north_rows(roles) - woody - used):
            rows.append(_row(len(rows) + 1, slug, symbol_by_slug, plant_by_slug, roles, used, note="Tall or trellised crop placed toward the north edge."))

        for slug in sorted(_sprawling_rows(roles) - woody - used):
            rows.append(_row(len(rows) + 1, slug, symbol_by_slug, plant_by_slug, roles, used, role="sprawling_edge", note="Sprawling crop assigned to an edge row."))

        for slug in sorted(_primary_rows(roles) - woody - used):
            rows.append(_row(len(rows) + 1, slug, symbol_by_slug, plant_by_slug, roles, used))

        for slug in sorted(_companion_rows(roles) - woody - used):
            rows.append(_row(len(rows) + 1, slug, symbol_by_slug, plant_by_slug, roles, used, role="companion", note="Companion crop can be interplanted near nearby primary rows."))

        for slug in sorted(_border_rows(roles) - woody - used):
            rows.append(_row(len(rows) + 1, slug, symbol_by_slug, plant_by_slug, roles, used, role="pollinator_border", note="Use at row ends and garden borders."))

        for slug in sorted(set(symbol_by_slug) - woody - used):
            rows.append(_row(len(rows) + 1, slug, symbol_by_slug, plant_by_slug, roles, used, role="filler"))

        return RowBlueprint(
            rows=rows,
            row_spacing_notes=[rule.rationale for rule in design_plan.separation_rules],
            diagram_label_frequency=_label_frequency(len(rows)),
            tree_shrub_symbols=[symbol_by_slug[slug].symbol for slug in sorted(woody) if slug in symbol_by_slug],
        )


def _row(
    row_number: int,
    slug: str,
    symbol_by_slug: dict[str, PlantSymbol],
    plant_by_slug: dict[str, Plant],
    roles: dict[str, set[str]],
    used: set[str],
    *,
    role: str | None = None,
    note: str | None = None,
) -> DesignedRow:
    used.add(slug)
    row_role = role or _row_role(roles.get(slug, set()))
    return DesignedRow(
        row_number=row_number,
        row_label=_display(slug, symbol_by_slug),
        primary_plants=[slug],
        spacing_from_prior_row_inches=None if row_number == 1 else _row_spacing(plant_by_slug.get(slug)),
        in_row_spacing_inches=_in_row_spacing(plant_by_slug.get(slug)),
        row_role=row_role,
        notes=[note] if note else [],
    )


def _roles_by_slug(design_plan: PlantingDesignPlan) -> dict[str, set[str]]:
    roles: dict[str, set[str]] = {}
    for role in design_plan.plant_roles:
        roles.setdefault(role.plant_slug, set()).add(role.role)
    return roles


def _north_rows(roles: dict[str, set[str]]) -> set[str]:
    return {slug for slug, values in roles.items() if values & {"tall_crop", "trellised_crop"}}


def _sprawling_rows(roles: dict[str, set[str]]) -> set[str]:
    return {slug for slug, values in roles.items() if "sprawling_crop" in values}


def _primary_rows(roles: dict[str, set[str]]) -> set[str]:
    return {slug for slug, values in roles.items() if "primary_crop" in values}


def _companion_rows(roles: dict[str, set[str]]) -> set[str]:
    return {slug for slug, values in roles.items() if values & {"companion_herb", "leafy_green", "root_crop"}}


def _border_rows(roles: dict[str, set[str]]) -> set[str]:
    return {slug for slug, values in roles.items() if values & {"pollinator_flower", "border_plant"}}


def _row_role(roles: set[str]) -> str:
    if "sprawling_crop" in roles:
        return "sprawling_edge"
    if roles & {"tall_crop", "trellised_crop"}:
        return "trellis"
    if roles & {"pollinator_flower", "border_plant"}:
        return "pollinator_border"
    if roles & {"companion_herb", "leafy_green", "root_crop"}:
        return "companion"
    return "primary_crop"


def _display(slug: str, symbol_by_slug: dict[str, PlantSymbol]) -> str:
    symbol = symbol_by_slug.get(slug)
    return f"{symbol.display_name} ({symbol.symbol})" if symbol else slug.replace("_", " ").title()


def _slug(plant: Plant) -> str:
    return getattr(plant, "slug", None) or plant.common_name.lower().replace(" ", "_")


def _row_spacing(plant: Plant | None) -> int | None:
    return int(getattr(plant, "row_spacing_inches", None) or getattr(plant, "spacing_inches", None) or 18) if plant else 18


def _in_row_spacing(plant: Plant | None) -> int | None:
    return int(getattr(plant, "spacing_inches", None) or 12) if plant else 12


def _label_frequency(count: int) -> int:
    if count <= 8:
        return 1
    if count <= 20:
        return 2
    if count <= 50:
        return 5
    return 10
