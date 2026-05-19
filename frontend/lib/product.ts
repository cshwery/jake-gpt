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

export function fitLabel(score: number): string {
  if (score >= 85) return "Excellent Fit";
  if (score >= 70) return "Good Fit";
  if (score >= 50) return "Possible Fit";
  if (score >= 30) return "Poor Fit";
  return "Not Recommended";
}

export function recommendationLabel(type: string): string {
  const labels: Record<string, string> = {
    selected: "Selected",
    suggested_companion: "Good Companion",
    climate_fit: "Recommended",
    goal_fit: "Recommended",
    pollinator_support: "Pollinator Support",
    cultivar_suggestion: "Variety Suggestion",
    warning_only: "Review Before Planting",
    not_recommended: "Not Recommended Nearby"
  };
  return labels[type] ?? type.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

export function recommendationReasonLabel(code: string): string {
  const labels: Record<string, string> = {
    HARDINESS_MATCH: "Fits your hardiness zone.",
    HARDINESS_MISMATCH: "May be marginal for your climate.",
    SUNLIGHT_MATCH: "Fits your sun conditions.",
    SUNLIGHT_MISMATCH: "Sun needs may not match your garden.",
    WATER_MATCH: "Water needs look aligned.",
    WATER_WARNING: "Water needs may need extra attention.",
    FOOD_GOAL_MATCH: "Supports your food goal.",
    FLOWER_GOAL_MATCH: "Supports your flowers goal.",
    POLLINATOR_GOAL_MATCH: "Supports pollinators.",
    SHADE_GOAL_MATCH: "Supports a shade goal.",
    LOW_MAINTENANCE_MATCH: "Matches your maintenance preference.",
    COMPANION_WITH_SELECTED_PLANT: "Pairs well with something you selected.",
    GUILD_WITH_SELECTED_PLANT: "Fits a companion planting guild.",
    PEST_DETERRENT_COMPANION: "May help with pest deterrence.",
    POLLINATOR_SUPPORT: "Can support pollinators.",
    NUTRIENT_SUPPORT: "Can support neighboring plants.",
    AVOID_RELATIONSHIP: "Should be kept away from a selected plant.",
    DISEASE_RISK: "May increase disease pressure.",
    PEST_RISK: "May increase pest pressure.",
    ALLELOPATHY_RISK: "May suppress nearby plants.",
    SAME_FAMILY_WARNING: "Shares family risk with another plant.",
    SPACE_FIT: "Fits your garden size.",
    SPACE_WARNING: "Space may be tight.",
    BEGINNER_FRIENDLY: "Good choice for a beginner.",
    CULTIVAR_DAYS_TO_MATURITY_FIT: "Matures in time for your season.",
    CULTIVAR_DISEASE_RESISTANCE: "Cultivar has useful resistance.",
    FALLBACK_TO_SPECIES_DEFAULTS: "Used species-level information where cultivar data was missing."
  };
  return labels[code] ?? code.replaceAll("_", " ").toLowerCase();
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

export function displayPlantName(commonName: string): string {
  return titleCase(commonName);
}

export function displayCultivarName(commonName: string, cultivarName: string): string {
  return `${titleCase(commonName)} — ${cultivarName}`;
}

export function titleCase(value: string): string {
  return value
    .split(/[\s_-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
