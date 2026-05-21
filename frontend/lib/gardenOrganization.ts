import type { GardenGoals } from "@/types/api";

export type GardenOrganizationMode = "raised_beds" | "rows" | "chaos";

export function organizationModeFromGoals(goals: Pick<GardenGoals, "planting_style" | "using_raised_beds">): GardenOrganizationMode {
  if (goals.using_raised_beds === true || goals.planting_style === "raised_beds") return "raised_beds";
  if (goals.planting_style === "chaos") return "chaos";
  return "rows";
}

export function applyGardenOrganization(goals: GardenGoals, mode: GardenOrganizationMode): GardenGoals {
  if (mode === "raised_beds") {
    return { ...goals, planting_style: "raised_beds", using_raised_beds: true };
  }
  if (mode === "chaos") {
    return { ...goals, planting_style: "chaos", using_raised_beds: false, raised_beds: null };
  }
  return { ...goals, planting_style: "rows", using_raised_beds: false, raised_beds: null };
}

export function layoutStyleFromGoals(goals: Pick<GardenGoals, "planting_style" | "using_raised_beds">): "raised_beds" | "rows" | "chaos" | "grid" {
  const mode = organizationModeFromGoals(goals);
  if (mode === "raised_beds") return "raised_beds";
  if (mode === "chaos") return "chaos";
  return "rows";
}
