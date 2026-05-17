import type { GeneratedPlan, LayoutResult, PlantRead } from "@/types/api";

export function titleCase(value: string | null | undefined): string {
  return (value ?? "")
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

export function plantDisplayName(plant: PlantRead): string {
  const species = titleCase(plant.common_name);
  return plant.result_type === "cultivar" && plant.cultivar_name ? `${species} — ${plant.cultivar_name}` : species;
}

export function areaCategory(areaSqFt: number): string {
  if (areaSqFt < 25) return "Tiny";
  if (areaSqFt < 100) return "Small";
  if (areaSqFt < 500) return "Medium";
  if (areaSqFt < 2000) return "Large";
  if (areaSqFt < 10000) return "Very Large";
  return "Probably Accidental";
}

export function areaWarning(areaSqFt: number): string | null {
  if (areaSqFt > 10000) return "This garden area is unusually large and may have been drawn at the wrong zoom level.";
  if (areaSqFt > 2000) return "This is a very large garden area for a home garden. Confirm the boundary is correct.";
  return null;
}

export function recommendationFitLabel(score: number): string {
  if (score >= 85) return "Excellent Fit";
  if (score >= 70) return "Good Fit";
  if (score >= 50) return "Possible Fit";
  if (score >= 30) return "Poor Fit";
  return "Not Recommended";
}

export function recommendationTypeLabel(type: string, reasonCodes: string[] = []): string {
  const reasons = new Set(reasonCodes);
  if (["avoid", "disease_risk", "pest_risk", "allelopathy"].some((token) => type.includes(token) || reasons.has(token.toUpperCase()))) return "Not Recommended Nearby";
  if (type === "warning_only") return "Use With Caution";
  if (type.includes("pollinator") || reasons.has("POLLINATOR_SUPPORT") || reasons.has("POLLINATOR_GOAL_MATCH")) return "Pollinator Support";
  if (type.includes("companion") || reasons.has("COMPANION_WITH_SELECTED_PLANT")) return "Good Companion";
  if (type.includes("goal") || type.includes("climate")) return "Recommended";
  return "Possible Fit";
}

export function layoutQualityLabel(score: number): string {
  if (score >= 85) return "Excellent Layout";
  if (score >= 70) return "Good Layout";
  if (score >= 50) return "Acceptable Layout";
  if (score >= 30) return "Needs Review";
  return "Poor Layout";
}

export function subscoreLabel(score: number): string {
  if (score >= 80) return "Good";
  if (score >= 50) return "Acceptable";
  return "Needs Review";
}

export function conciseReasons(explanation: string, reasonCodes: string[], warnings: string[] = []): string[] {
  const reasons: string[] = [];
  const codes = new Set(reasonCodes);
  if (codes.has("SUNLIGHT_MATCH")) reasons.push("Fits your garden sunlight.");
  if (codes.has("FOOD_GOAL_MATCH")) reasons.push("Matches your food garden goal.");
  if (codes.has("FLOWER_GOAL_MATCH")) reasons.push("Matches your flower garden goal.");
  if (codes.has("POLLINATOR_GOAL_MATCH") || codes.has("POLLINATOR_SUPPORT")) reasons.push("Supports pollinators.");
  if (codes.has("COMPANION_WITH_SELECTED_PLANT")) reasons.push("Good companion for a selected plant.");
  if (codes.has("GUILD_WITH_SELECTED_PLANT")) reasons.push("Fits a companion guild with selected plants.");
  if (codes.has("LOW_MAINTENANCE_MATCH")) reasons.push("Fits your maintenance preference.");
  if (codes.has("SPACE_FIT")) reasons.push("Fits the available garden space.");
  if (codes.has("DISEASE_RISK") || codes.has("PEST_RISK")) reasons.push("Use caution: may share pest or disease pressure.");
  if (!reasons.length && explanation) reasons.push(explanation);
  return [...reasons.slice(0, 3), ...warnings.slice(0, 1)];
}

export function layoutToGeneratedPlan(layout: LayoutResult, goals: GeneratedPlan["goals"]): GeneratedPlan {
  return {
    garden_id: layout.garden_id ?? 0,
    summary: layout.summary,
    layout_grid: {
      rows: layout.grid.rows,
      cols: layout.grid.cols,
      cell_size_ft: layout.grid.cell_size_ft,
      orientation: layout.grid.orientation,
      cells: layout.grid.cells,
      access_paths: layout.grid.access_paths
    },
    items: layout.placements.map((placement) => ({
      plant_id: placement.plant_id ?? 0,
      label: plantDisplayLabel(placement.plant_common_name, placement.cultivar_name),
      row: placement.row ?? 0,
      col: placement.col ?? 0,
      width: placement.width ?? 1,
      height: placement.height ?? 1,
      quantity: placement.quantity,
      x_pct: placement.x_pct ?? 0,
      y_pct: placement.y_pct ?? 0,
      notes: placement.location_notes
    })),
    companion_notes: [...layout.explanations, ...layout.warnings],
    goals
  };
}

export function plantDisplayLabel(commonName: string, cultivarName?: string | null): string {
  const species = titleCase(commonName);
  return cultivarName ? `${species} — ${cultivarName}` : species;
}
