import { describe, expect, it } from "vitest";
import { cn } from "./utils";
import { applyGardenOrganization } from "./gardenOrganization";
import { areaCategory, areaWarning, fitLabel, layoutQualityLabel, recommendationLabel, recommendationReasonLabel, subscoreLabel } from "./product";

describe("cn", () => {
  it("merges class names", () => {
    expect(cn("px-2", false && "hidden", "px-4")).toContain("px-4");
  });

  it("labels garden area scale", () => {
    expect(areaCategory(24)).toBe("Tiny");
    expect(areaCategory(250)).toBe("Medium");
    expect(areaCategory(12000)).toBe("Probably Accidental");
  });

  it("returns area warnings for very large and tiny gardens", () => {
    expect(areaWarning(24)).toContain("tiny garden");
    expect(areaWarning(2001)).toContain("very large");
    expect(areaWarning(10001)).toContain("wrong zoom level");
  });

  it("maps recommendation and layout scores to product labels", () => {
    expect(fitLabel(90)).toBe("Excellent Fit");
    expect(fitLabel(40)).toBe("Poor Fit");
    expect(recommendationLabel("warning_only")).toBe("Review Before Planting");
    expect(recommendationReasonLabel("POLLINATOR_SUPPORT")).toContain("pollinators");
    expect(layoutQualityLabel(90)).toBe("Excellent Layout");
    expect(layoutQualityLabel(undefined)).toBe("Not evaluated");
    expect(layoutQualityLabel(75)).toBe("Good Layout");
    expect(layoutQualityLabel(60)).toBe("Acceptable Layout");
    expect(layoutQualityLabel(35)).toBe("Needs Review");
    expect(layoutQualityLabel(20)).toBe("Poor Layout");
    expect(subscoreLabel(undefined)).toBe("Not evaluated");
    expect(subscoreLabel(85)).toBe("Good");
    expect(subscoreLabel(65)).toBe("Acceptable");
    expect(subscoreLabel(20)).toBe("Needs Review");
  });

  it("maps the garden organization question into legacy setup fields", () => {
    const goals = {
      goal: "Food",
      goals: ["food"],
      maintenance_preference: "Moderate",
      sunlight: "Full Sun",
      planting_style: "rows" as const,
      using_raised_beds: false,
      raised_beds: { number_of_beds: 2 }
    };

    expect(applyGardenOrganization(goals, "chaos")).toMatchObject({ planting_style: "chaos", using_raised_beds: false, raised_beds: null });
    expect(applyGardenOrganization(goals, "raised_beds")).toMatchObject({ planting_style: "raised_beds", using_raised_beds: true });
    expect(applyGardenOrganization(goals, "rows")).toMatchObject({ planting_style: "rows", using_raised_beds: false, raised_beds: null });
  });
});
