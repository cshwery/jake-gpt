import { describe, expect, it } from "vitest";
import { cn } from "./utils";
import { areaCategory, layoutQualityLabel, plantDisplayName, recommendationFitLabel, recommendationTypeLabel, subscoreLabel } from "./product";

describe("cn", () => {
  it("merges class names", () => {
    expect(cn("px-2", false && "hidden", "px-4")).toContain("px-4");
  });

  it("labels garden areas by home-garden scale", () => {
    expect(areaCategory(24)).toBe("Tiny");
    expect(areaCategory(250)).toBe("Medium");
    expect(areaCategory(12000)).toBe("Probably Accidental");
  });

  it("displays species and cultivars distinctly", () => {
    expect(plantDisplayName({ id: 1, common_name: "tomato", plant_type: "vegetable", edible: true, flower: false, tree: false, perennial: false, min_zone: 2, max_zone: 11, sunlight_requirement: "full_sun", water_requirement: "medium", spacing_inches: 24, row_spacing_inches: 36, maintenance_level: "moderate", planting_notes: "Stake." })).toBe("Tomato");
    expect(plantDisplayName({ id: 1, common_name: "tomato", plant_type: "vegetable", edible: true, flower: false, tree: false, perennial: false, min_zone: 2, max_zone: 11, sunlight_requirement: "full_sun", water_requirement: "medium", spacing_inches: 24, row_spacing_inches: 36, maintenance_level: "moderate", planting_notes: "Stake.", result_type: "cultivar", cultivar_name: "Sungold", cultivar_slug: "tomato_sungold" })).toBe("Tomato — Sungold");
  });

  it("maps internal recommendation and layout scores to product labels", () => {
    expect(recommendationFitLabel(86)).toBe("Excellent Fit");
    expect(recommendationTypeLabel("warning_only")).toBe("Use With Caution");
    expect(recommendationTypeLabel("suggested_companion", ["COMPANION_WITH_SELECTED_PLANT"])).toBe("Good Companion");
    expect(layoutQualityLabel(71)).toBe("Good Layout");
    expect(subscoreLabel(49)).toBe("Needs Review");
  });
});
