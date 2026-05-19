import { describe, expect, it } from "vitest";
import type { PlantSearchResult } from "@/types/api";
import { dedupePlantResults, displayPlantResultName, recommendationTarget, selectionKeyForPlantResult } from "./plantSelection";

function species(overrides: Partial<PlantSearchResult> = {}): PlantSearchResult {
  return {
    id: 1,
    slug: "tomato",
    common_name: "tomato",
    scientific_name: "Solanum lycopersicum",
    plant_type: "vegetable",
    edible: true,
    flower: false,
    tree: false,
    perennial: false,
    min_zone: 3,
    max_zone: 10,
    sunlight_requirement: "Full Sun",
    water_requirement: "Medium",
    spacing_inches: 24,
    row_spacing_inches: 36,
    days_to_maturity: 75,
    maintenance_level: "moderate",
    planting_notes: "notes",
    result_type: "species",
    plant_id: 1,
    cultivar_id: null,
    cultivar_slug: null,
    cultivar_name: null,
    display_name: "Tomato",
    cultivar_notes: null,
    ...overrides
  };
}

function cultivar(overrides: Partial<PlantSearchResult> = {}): PlantSearchResult {
  return {
    ...species({
      result_type: "cultivar",
      cultivar_id: 10,
      cultivar_slug: "tomato_sungold",
      cultivar_name: "Sungold",
      display_name: "Tomato — Sungold"
    }),
    ...overrides
  };
}

describe("plantSelection helpers", () => {
  it("deduplicates identical species rows", () => {
    const results = [species(), species()];
    expect(dedupePlantResults(results)).toHaveLength(1);
  });

  it("deduplicates species rows with different ids but the same slug", () => {
    const results = [species({ id: 1, plant_id: 1 }), species({ id: 2, plant_id: 2 })];
    expect(dedupePlantResults(results)).toHaveLength(1);
  });

  it("keeps cultivar rows distinct from species rows", () => {
    const results = dedupePlantResults([species(), cultivar()]);
    expect(results).toHaveLength(2);
    expect(selectionKeyForPlantResult(results[0])).not.toBe(selectionKeyForPlantResult(results[1]));
  });

  it("prefers the backend display name", () => {
    expect(displayPlantResultName(cultivar())).toBe("Tomato — Sungold");
  });

  it("creates a cultivar target for cultivar recommendations when cultivar rows are not loaded", () => {
    const target = recommendationTarget(
      {
        plant_slug: "tomato",
        plant_common_name: "Tomato",
        cultivar_recommendations: [{ cultivar_slug: "tomato_sungold", cultivar_name: "Sungold", score: 30, reason_codes: [] }],
        recommendation_type: "goal_fit",
        score: 100,
        score_breakdown: {},
        reason_codes: [],
        warnings: [],
        explanation: "Good fit."
      },
      [species()]
    );

    expect(target?.result_type).toBe("cultivar");
    expect(selectionKeyForPlantResult(target!)).toBe("cultivar:tomato_sungold");
  });
});
