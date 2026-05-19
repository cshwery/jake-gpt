import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { GardenLayoutGrid } from "./GardenLayoutGrid";

describe("GardenLayoutGrid", () => {
  it("renders layout metadata and canonical grid labels", () => {
    render(
      <GardenLayoutGrid
        layout={{
          layout_id: 1,
          garden_id: 7,
          summary: "Test layout",
          area_sq_ft: 120,
          area_category: "Medium",
          approximate_dimensions_ft: { width: 12, height: 10, grid_area_sq_ft: 120 },
          grid: {
            rows: 2,
            cols: 2,
            cell_size_ft: 2,
            orientation: "north_up",
            access_paths: ["center path"],
            cells: [
              { cell_id: "A1", row: 0, col: 0, available: true, is_path: false, plant_slug: "tomato", label: "Tomato", notes: [], cultivar_slug: null },
              { cell_id: "B1", row: 0, col: 1, available: true, is_path: true, plant_slug: null, label: null, notes: [] },
              { cell_id: "A2", row: 1, col: 0, available: true, is_path: false, plant_slug: "basil", label: "Basil", notes: [], cultivar_slug: null },
              { cell_id: "B2", row: 1, col: 1, available: true, is_path: false, plant_slug: null, label: null, notes: [] }
            ]
          },
          placements: [
            { plant_slug: "tomato", plant_common_name: "Tomato", quantity: 2, grid_cells: ["A1"], row: 0, col: 0, width: 1, height: 1, x_pct: 25, y_pct: 25, warnings: [], placement_role: "crop" },
            { plant_slug: "basil", plant_common_name: "Basil", quantity: 2, grid_cells: ["A2"], row: 1, col: 0, width: 1, height: 1, x_pct: 25, y_pct: 75, warnings: [], placement_role: "companion" }
          ],
          paths: [],
          score_breakdown: {
            spacing_score: 10,
            companion_score: 20,
            conflict_score: -5,
            access_score: 15,
            sunlight_score: 10,
            size_fit_score: 10,
            diversity_score: 5,
            total_score: 75
          },
          warnings: ["Example warning"],
          explanations: ["Example explanation"],
          assumptions: ["Example assumption"]
        }}
      />
    );

    expect(screen.getAllByText("North ↑").length).toBeGreaterThan(0);
    expect(screen.getByText("Each cell = 2 ft × 2 ft")).toBeTruthy();
    expect(screen.getByText("Test layout")).toBeTruthy();
    expect(screen.getByText("Good Layout")).toBeTruthy();
    expect(screen.getByText("A1")).toBeTruthy();
    expect(screen.getAllByText("Tomato").length).toBeGreaterThan(0);
  });
});
