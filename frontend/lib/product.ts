export function areaCategory(areaSqFt: number): string {
  if (areaSqFt < 25) return "Tiny";
  if (areaSqFt < 100) return "Small";
  if (areaSqFt < 500) return "Medium";
  if (areaSqFt < 2000) return "Large";
  if (areaSqFt < 10000) return "Very Large";
  return "Probably Accidental";
}

export function areaWarning(areaSqFt: number): string | null {
  if (areaSqFt > 10000) return "This garden area is unusually large and may have been drawn at the wrong zoom level. Zoom in and draw only the actual planting area.";
  if (areaSqFt > 2000) return "This is a very large garden area for a home garden. Confirm the boundary is correct.";
  if (areaSqFt < 25) return "This is a tiny garden area. That can work for containers or herbs, but confirm the boundary is correct.";
  return null;
}

export function formatArea(areaSqFt: number | null | undefined): string {
  return typeof areaSqFt === "number" ? `${areaSqFt.toFixed(0)} sq ft` : "No boundary drawn";
}
