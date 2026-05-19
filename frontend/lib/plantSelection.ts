import type { GardenRecommendationResult, PlantSearchResult } from "@/types/api";
import { displayCultivarName, displayPlantName, titleCase } from "@/lib/product";

export function selectionKeyForPlantResult(item: PlantSearchResult): string {
  if (item.result_type === "cultivar") {
    return `cultivar:${normalizedIdentity(item.cultivar_slug ?? item.cultivar_name ?? item.display_name ?? null) ?? item.cultivar_id ?? normalizedIdentity(item.slug ?? item.common_name) ?? item.plant_id ?? item.id}`;
  }
  return `species:${normalizedIdentity(item.slug ?? item.common_name) ?? item.plant_id ?? item.id}`;
}

export function displayPlantResultName(item: PlantSearchResult): string {
  if (item.display_name) {
    return item.display_name;
  }
  return item.result_type === "cultivar"
    ? displayCultivarName(item.common_name, item.cultivar_name ?? titleCase(item.common_name))
    : displayPlantName(item.common_name);
}

export function dedupePlantResults(results: PlantSearchResult[]): PlantSearchResult[] {
  const seen = new Set<string>();
  const deduped: PlantSearchResult[] = [];
  for (const result of results) {
    const key = selectionKeyForPlantResult(result);
    if (seen.has(key)) continue;
    seen.add(key);
    deduped.push(result);
  }
  return deduped;
}

export function uniqueStrings(values: string[]) {
  return Array.from(new Set(values));
}

export function uniqueNumbers(values: number[]) {
  return Array.from(new Set(values));
}

export function recommendationSelectionKey(plantSlug: string, cultivarSlug: string | null) {
  return cultivarSlug ? `cultivar:${cultivarSlug}` : `species:${plantSlug}`;
}

export function selectionKeyForRecommendationTarget(item: GardenRecommendationResult["recommendations"][number]) {
  return recommendationSelectionKey(item.plant_slug, item.cultivar_recommendations[0]?.cultivar_slug ?? null);
}

export function recommendationTarget(
  item: GardenRecommendationResult["recommendations"][number],
  results: PlantSearchResult[]
): PlantSearchResult | null {
  const cultivarSlug = item.cultivar_recommendations[0]?.cultivar_slug;
  if (cultivarSlug) {
    return (
      results.find((result) => result.result_type === "cultivar" && result.cultivar_slug === cultivarSlug) ??
      results.find((result) => result.result_type === "species" && result.slug === item.plant_slug) ??
      syntheticRecommendationResult(item, true)
    );
  }
  return (
    results.find((result) => result.result_type === "species" && result.slug === item.plant_slug) ??
    syntheticRecommendationResult(item, false)
  );
}

export function syntheticRecommendationResult(
  item: GardenRecommendationResult["recommendations"][number],
  isCultivar: boolean
): PlantSearchResult {
  const cultivar = item.cultivar_recommendations[0];
  return {
    id: cultivar?.cultivar_slug ? Math.abs(hashString(cultivar.cultivar_slug)) : Math.abs(hashString(item.plant_slug)),
    slug: item.plant_slug,
    common_name: item.plant_common_name,
    scientific_name: null,
    plant_type: "vegetable",
    edible: true,
    flower: false,
    tree: false,
    perennial: false,
    min_zone: 0,
    max_zone: 99,
    sunlight_requirement: "unknown",
    water_requirement: "unknown",
    spacing_inches: 0,
    row_spacing_inches: 0,
    days_to_maturity: null,
    maintenance_level: "unknown",
    planting_notes: item.explanation,
    result_type: isCultivar ? "cultivar" : "species",
    plant_id: undefined,
    cultivar_id: cultivar?.cultivar_slug ? Math.abs(hashString(cultivar.cultivar_slug)) : undefined,
    cultivar_slug: cultivar?.cultivar_slug ?? null,
    cultivar_name: cultivar?.cultivar_name ?? null,
    display_name: isCultivar ? `${displayPlantName(item.plant_common_name)} — ${cultivar?.cultivar_name ?? ""}`.trim() : displayPlantName(item.plant_common_name),
    cultivar_notes: null
  };
}

function hashString(value: string) {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash << 5) - hash + value.charCodeAt(index);
    hash |= 0;
  }
  return hash || 1;
}

function normalizedIdentity(value: string | null | undefined) {
  const normalized = value?.trim().toLowerCase().replace(/\s+/g, "-");
  return normalized || null;
}
