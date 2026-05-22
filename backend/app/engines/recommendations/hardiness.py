from typing import Any

from app.models import Plant


def zone_number(zone: str | None) -> int | None:
    if not zone:
        return None
    digits = "".join(ch for ch in str(zone) if ch.isdigit())
    return int(digits) if digits else None


def context_zone_number(garden_context: Any | None) -> int | None:
    if garden_context is None:
        return None
    if isinstance(garden_context, dict):
        return zone_number(garden_context.get("hardiness", {}).get("zone") or garden_context.get("hardiness_zone"))
    hardiness = getattr(garden_context, "hardiness", None)
    if hardiness is not None:
        return zone_number(getattr(hardiness, "zone", None))
    return zone_number(getattr(garden_context, "hardiness_zone", None))


def is_perennial_or_woody(plant: Plant) -> bool:
    category = (getattr(plant, "plant_category", "") or "").lower()
    lifecycle = (getattr(plant, "lifecycle", "") or "").lower()
    plant_type = (getattr(plant, "plant_type", "") or "").lower()
    return bool(
        getattr(plant, "perennial", False)
        or getattr(plant, "tree", False)
        or getattr(plant, "is_tree", False)
        or getattr(plant, "is_shrub", False)
        or "perennial" in lifecycle
        or "tree" in plant_type
        or "shrub" in plant_type
        or category in {"berry", "berries", "tree fruit", "fruit tree", "shrub"}
    )


def hardiness_zone_bounds(plant: Plant) -> tuple[int | None, int | None]:
    min_zone = getattr(plant, "min_hardiness_zone", None) or getattr(plant, "min_zone", None)
    max_zone = getattr(plant, "max_hardiness_zone", None) or getattr(plant, "max_zone", None)
    return min_zone, max_zone


def is_hardiness_compatible(plant: Plant, zone: int | None) -> bool:
    if zone is None:
        return True
    min_zone, max_zone = hardiness_zone_bounds(plant)
    if min_zone is None or max_zone is None:
        return True
    return min_zone <= zone <= max_zone


def should_exclude_for_hardiness(plant: Plant, zone: int | None) -> bool:
    return is_perennial_or_woody(plant) and not is_hardiness_compatible(plant, zone)


def hardiness_warning(plant: Plant, zone: int | None) -> str | None:
    if zone is None or not should_exclude_for_hardiness(plant, zone):
        return None
    return f"{plant.common_name.title()} is not recommended for your hardiness zone and may not survive winter."
