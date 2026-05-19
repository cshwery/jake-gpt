import { describe, expect, it } from "vitest";
import { cn } from "./utils";
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
    expect(subscoreLabel(20)).toBe("Needs Review");
  });
});
