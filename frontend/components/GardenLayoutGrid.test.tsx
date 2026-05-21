import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { GardenLayoutGrid } from "./GardenLayoutGrid";

afterEach(cleanup);

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
    expect(screen.getAllByText("A1").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Tomato").length).toBeGreaterThan(0);
  });

  it("renders row layouts as planting rows", () => {
    render(
      <GardenLayoutGrid
        layout={{
          layout_id: 2,
          garden_id: 7,
          summary: "Row layout test",
          grid: {
            rows: 1,
            cols: 3,
            cell_size_ft: 1,
            orientation: "north_up",
            layout_style: "rows",
            access_paths: ["rows run west to east"],
            cells: [
              { cell_id: "R1-1", row: 0, col: 0, available: true, is_path: false, plant_slug: "tomato", label: "Tomato", notes: [], group_id: "row-1", group_label: "Row 1" },
              { cell_id: "R1-2", row: 0, col: 1, available: true, is_path: false, plant_slug: "tomato", label: "Tomato", notes: [], group_id: "row-1", group_label: "Row 1" },
              { cell_id: "R1-3", row: 0, col: 2, available: true, is_path: false, plant_slug: "tomato", label: "Tomato", notes: [], group_id: "row-1", group_label: "Row 1" }
            ]
          },
          placements: [
            { plant_slug: "tomato", plant_common_name: "Tomato", quantity: 3, grid_cells: ["R1-1", "R1-2", "R1-3"], row: 0, col: 0, width: 3, height: 1, warnings: [], placement_role: "crop" }
          ],
          paths: [],
          score_breakdown: { total_score: 75 },
          warnings: [],
          explanations: [],
          assumptions: []
        }}
      />
    );

    expect(screen.getAllByText("Rows").length).toBeGreaterThan(0);
    expect(screen.getByText("Rows run west to east.")).toBeTruthy();
    expect(screen.getByText("Row 1 — Tomato")).toBeTruthy();
    expect(screen.getByText(/start at north edge/)).toBeTruthy();
    expect(screen.getAllByText("North ↑").length).toBeGreaterThan(0);
  });

  it("renders raised bed layouts grouped by bed", () => {
    render(
      <GardenLayoutGrid
        layout={{
          layout_id: 3,
          garden_id: 7,
          summary: "Raised bed test",
          grid: {
            rows: 1,
            cols: 2,
            cell_size_ft: 1,
            orientation: "north_up",
            layout_style: "raised_beds",
            access_paths: ["2 raised beds"],
            cells: [
              { cell_id: "B1-A1", row: 0, col: 0, available: true, is_path: false, plant_slug: "basil", label: "Basil", notes: [], group_id: "bed-1", group_label: "Bed 1" },
              { cell_id: "B1-B1", row: 0, col: 1, available: true, is_path: false, plant_slug: "tomato", label: "Tomato", notes: [], group_id: "bed-1", group_label: "Bed 1" }
            ]
          },
          placements: [
            { plant_slug: "basil", plant_common_name: "Basil", quantity: 2, grid_cells: ["B1-A1"], row: 0, col: 0, warnings: [], placement_role: "companion" },
            { plant_slug: "tomato", plant_common_name: "Tomato", quantity: 1, grid_cells: ["B1-B1"], row: 0, col: 1, warnings: [], placement_role: "crop" }
          ],
          paths: [],
          score_breakdown: { total_score: 75 },
          warnings: [],
          explanations: [],
          assumptions: []
        }}
      />
    );

    expect(screen.getByText("Raised beds")).toBeTruthy();
    expect(screen.getByText("Beds are separated by paths.")).toBeTruthy();
    expect(screen.getAllByText("Bed 1").length).toBeGreaterThan(0);
    expect(screen.getAllByText("4 ft × 8 ft").length).toBeGreaterThan(0);
    expect(screen.getAllByText("B").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Basil").length).toBeGreaterThan(0);
    expect(screen.getAllByText("T").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Tomato").length).toBeGreaterThan(0);
    expect(screen.getByRole("img", { name: /Raised bed/i })).toBeTruthy();
  });

  it("shows trees and bushes separately for row layouts", () => {
    render(
      <GardenLayoutGrid
        layout={{
          layout_id: 4,
          garden_id: 7,
          summary: "Rows with trees",
          grid: {
            rows: 2,
            cols: 3,
            cell_size_ft: 1,
            orientation: "north_up",
            layout_style: "rows",
            access_paths: ["rows run west to east"],
            cells: [
              { cell_id: "R1-1", row: 0, col: 0, available: true, is_path: false, plant_slug: "tomato", label: "Tomato", notes: [], group_id: "row-1", group_label: "Row 1" },
              { cell_id: "R1-2", row: 0, col: 1, available: true, is_path: false, plant_slug: "tomato", label: "Tomato", notes: [], group_id: "row-1", group_label: "Row 1" },
              { cell_id: "R2-1", row: 1, col: 0, available: true, is_path: false, plant_slug: "lettuce", label: "Lettuce", notes: [], group_id: "row-2", group_label: "Row 2" },
              { cell_id: "R2-2", row: 1, col: 1, available: true, is_path: false, plant_slug: "lettuce", label: "Lettuce", notes: [], group_id: "row-2", group_label: "Row 2" }
            ]
          },
          placements: [
            { plant_slug: "apple", plant_common_name: "Honeycrisp Apple", quantity: 1, grid_cells: [], row: null, col: null, warnings: [], placement_role: "tree" },
            { plant_slug: "blueberry", plant_common_name: "Blueberry", quantity: 1, grid_cells: [], row: null, col: null, warnings: [], placement_role: "shrub" },
            { plant_slug: "tomato", plant_common_name: "Tomato", quantity: 3, grid_cells: ["R1-1", "R1-2"], row: 0, col: 0, width: 2, height: 1, spacing_inches: 24, row_spacing_inches: 36, warnings: [], placement_role: "crop" },
            { plant_slug: "lettuce", plant_common_name: "Lettuce", quantity: 6, grid_cells: ["R2-1", "R2-2"], row: 1, col: 0, width: 2, height: 1, spacing_inches: 8, row_spacing_inches: 12, warnings: [], placement_role: "crop" }
          ],
          paths: [],
          score_breakdown: { total_score: 75 },
          warnings: [],
          explanations: [],
          assumptions: []
        }}
      />
    );

    expect(screen.getByText("Trees & Bushes")).toBeTruthy();
    expect(screen.getAllByText("A1").length).toBeGreaterThan(0);
    expect(screen.getByText("Honeycrisp Apple")).toBeTruthy();
    expect(screen.getAllByText("B1").length).toBeGreaterThan(0);
    expect(screen.getByText("Blueberry")).toBeTruthy();
    expect(screen.getByText(/Row 2 — Lettuce/)).toBeTruthy();
    expect(screen.getByText(/12 in from prior row/)).toBeTruthy();
  });
});
