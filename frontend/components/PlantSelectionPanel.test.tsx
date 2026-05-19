import React from "react";
import { useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PlantSelectionPanel } from "./PlantSelectionPanel";
import type { GardenGoals, PlantSearchResult } from "@/types/api";
import { selectionKeyForPlantResult } from "@/lib/plantSelection";

function species(id = 1, slug = "tomato", commonName = "tomato"): PlantSearchResult {
  return {
    id,
    slug,
    common_name: commonName,
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
    plant_id: id,
    cultivar_id: null,
    cultivar_slug: null,
    cultivar_name: null,
    display_name: commonName.charAt(0).toUpperCase() + commonName.slice(1),
    cultivar_notes: null
  };
}

function cultivar(id = 10, slug = "tomato_sungold", cultivarName = "Sungold"): PlantSearchResult {
  return {
    ...species(1, "tomato", "tomato"),
    id,
    result_type: "cultivar",
    cultivar_id: id,
    cultivar_slug: slug,
    cultivar_name: cultivarName,
    display_name: `Tomato — ${cultivarName}`
  };
}

function Harness({ plantResults }: { plantResults: PlantSearchResult[] }) {
  const [selectedPlants, setSelectedPlants] = useState<Array<PlantSearchResult & { selection_key: string }>>([]);
  const goals: GardenGoals = {
    goal: "Food",
    goals: ["food"],
    maintenance_preference: "Moderate",
    experience_level: "beginner",
    sunlight: "Full Sun",
    free_text_preferences: "",
    planting_style: "rows",
    using_raised_beds: false,
    raised_beds: null,
    start_preference: "no_preference",
    can_start_seeds_indoors: null,
    prefers_buying_starts: null,
    direct_sow_preference: "no_preference"
  };

  return (
    <PlantSelectionPanel
      plantResults={plantResults}
      plantQuery=""
      setPlantQuery={() => undefined}
      selectedPlants={selectedPlants}
      onToggleSelection={(plant) => {
        setSelectedPlants((current) => {
          const key = selectionKeyForPlantResult(plant);
          const existing = current.find((item) => item.selection_key === key);
          if (existing) {
            return current.filter((item) => item.selection_key !== key);
          }
          return [...current, { ...plant, selection_key: key }];
        });
      }}
      recommendations={null}
      goals={goals}
      onGenerateRecommendations={vi.fn()}
      onGenerateLayout={vi.fn()}
    />
  );
}

describe("PlantSelectionPanel", () => {
  it("adds only the clicked species", () => {
    render(<Harness plantResults={[species(), species(2, "basil", "basil")]} />);

    fireEvent.click(screen.getByRole("button", { name: "Add Tomato" }));

    expect(screen.getAllByText("Selected plants: 1").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Added ✓")).toHaveLength(1);
    expect(screen.getAllByText("Tomato").length).toBeGreaterThan(0);
  });

  it("keeps species and cultivar selections distinct", () => {
    render(<Harness plantResults={[species(), cultivar()]} />);

    fireEvent.click(screen.getByRole("button", { name: "Add Tomato — Sungold" }));

    expect(screen.getAllByText("Selected plants: 1").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Tomato — Sungold").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Added ✓").length).toBeGreaterThan(0);
  });

  it("shows helper copy for selection", () => {
    render(<Harness plantResults={[species()]} />);

    expect(screen.getAllByText(/Pick plants you definitely want to include/i).length).toBeGreaterThan(0);
  });
});
