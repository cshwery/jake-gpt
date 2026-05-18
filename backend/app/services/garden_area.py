def area_category(area_sq_ft: float) -> str:
    if area_sq_ft < 25:
        return "Tiny"
    if area_sq_ft < 100:
        return "Small"
    if area_sq_ft < 500:
        return "Medium"
    if area_sq_ft < 2_000:
        return "Large"
    if area_sq_ft < 10_000:
        return "Very Large"
    return "Probably Accidental"


def area_warning(area_sq_ft: float) -> str | None:
    if area_sq_ft > 10_000:
        return "This garden area is unusually large and may have been drawn at the wrong zoom level. Zoom in and draw only the actual planting area."
    if area_sq_ft > 2_000:
        return "This is a very large garden area for a home garden. Confirm the boundary is correct."
    if area_sq_ft < 25:
        return "This is a tiny garden area. That can work for containers or herbs, but confirm the boundary is correct."
    return None
