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
          design_plan: {
            organization_style: "rows",
            summary: "Planting design uses rows organization. 1 companion cluster identified.",
            plant_roles: [],
            plant_groups: [],
            companion_clusters: [
              {
                cluster_id: "cluster-tomato",
                anchor_plant_slug: "tomato",
                companion_plant_slugs: ["basil"],
                border_plant_slugs: ["marigold"],
                filler_plant_slugs: [],
                rationale: "Tomato has nearby support plants.",
                placement_guidance: "Keep companion herbs in adjacent rows or interplanted notes near Tomato; use flowers at row ends."
              }
            ],
            pollinator_border: ["marigold"],
            separation_rules: [
              {
                plant_slugs: ["tomato", "potato"],
                relationship_type: "same_family",
                severity: "medium",
                placement_guidance: "do_not_cluster",
                rationale: "Tomatoes and potatoes may share disease pressure. Do not cluster them together."
              }
            ],
            placement_guidance: {
              rows_guidance: ["Tall crops are placed toward the north.", "Flowers are used at row ends and borders."],
              raised_beds_guidance: [],
              chaos_guidance: [],
              north_south_guidance: ["Place tall crops toward the north edge so they shade smaller crops less."],
              border_guidance: ["Use flowers as repeated border/support plants instead of one isolated block."],
              spacing_guidance: []
            },
            warnings: [],
            assumptions: []
          },
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
    expect(screen.getByText("Planting design")).toBeTruthy();
    expect(screen.getByText(/Keep companion herbs/)).toBeTruthy();
    expect(screen.getByText(/Do not cluster them together/)).toBeTruthy();
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
    const rowsHeading = screen.getAllByText("Rows")[1];
    const diagramHeading = screen.getByText("Row diagram");
    expect(rowsHeading.compareDocumentPosition(diagramHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
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

  it("repeats raised bed symbols according to quantity", () => {
    render(
      <GardenLayoutGrid
        layout={{
          layout_id: 33,
          garden_id: 7,
          summary: "Quantity bed test",
          grid: {
            rows: 1,
            cols: 1,
            cell_size_ft: 1,
            orientation: "north_up",
            layout_style: "raised_beds",
            access_paths: ["1 raised bed"],
            cells: [{ cell_id: "B1-A1", row: 0, col: 0, available: true, is_path: false, plant_slug: "bee_balm", label: "Bee Balm", notes: [], group_id: "bed-1", group_label: "Bed 1" }]
          },
          placements: [{ plant_slug: "bee_balm", plant_common_name: "Bee Balm", quantity: 18, grid_cells: ["B1-A1"], row: 0, col: 0, warnings: [], placement_role: "pollinator" }],
          paths: [],
          score_breakdown: { total_score: 75 },
          warnings: [],
          explanations: [],
          assumptions: []
        }}
      />
    );

    expect(screen.getAllByText("BB").length).toBeGreaterThanOrEqual(18);
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

  it("reduces row diagram label density for larger row counts", () => {
    const placements = Array.from({ length: 12 }, (_, index) => ({
      plant_slug: `crop-${index + 1}`,
      plant_common_name: `Crop ${index + 1}`,
      quantity: 1,
      grid_cells: [`R${index + 1}-1`],
      row: index,
      col: 0,
      width: 1,
      height: 1,
      spacing_inches: 12,
      row_spacing_inches: 18,
      warnings: [],
      placement_role: "crop"
    }));
    render(
      <GardenLayoutGrid
        layout={{
          layout_id: 5,
          garden_id: 7,
          summary: "Many rows",
          grid: {
            rows: 12,
            cols: 1,
            cell_size_ft: 1,
            orientation: "north_up",
            layout_style: "rows",
            access_paths: [],
            cells: placements.map((placement) => ({ cell_id: placement.grid_cells[0], row: placement.row, col: 0, available: true, is_path: false, plant_slug: placement.plant_slug, label: placement.plant_common_name, notes: [] }))
          },
          placements,
          paths: [],
          score_breakdown: { total_score: 75 },
          warnings: [],
          explanations: [],
          assumptions: []
        }}
      />
    );

    expect(screen.getByText(/Row 1: Crop 1/)).toBeTruthy();
    expect(screen.queryByText(/Row 2: Crop 2/)).toBeNull();
    expect(screen.getAllByText("North ↑").length).toBeGreaterThan(0);
  });

  it("renders chaos guidance instead of rows or raised beds", () => {
    render(
      <GardenLayoutGrid
        layout={{
          layout_id: 6,
          garden_id: 7,
          summary: "Chaos layout",
          grid: {
            rows: 1,
            cols: 1,
            cell_size_ft: 1,
            orientation: "north_up",
            layout_style: "chaos",
            layout_metadata: {
              suggested_plant_count_range: "6-12",
              guidance: ["Scatter seed in small clusters."],
              plant_groups: {
                easy_direct_sow_crops: ["Lettuce"],
                pollinator_support_flowers: ["Marigold"],
                herbs: ["Dill"],
                larger_sprawling_crops: [],
                avoid_or_separate: ["Apple"]
              }
            },
            access_paths: [],
            cells: []
          },
          placements: [
            { plant_slug: "lettuce", plant_common_name: "Lettuce", quantity: 6, grid_cells: [], warnings: [], placement_role: "crop" },
            { plant_slug: "marigold", plant_common_name: "Marigold", quantity: 6, grid_cells: [], warnings: [], placement_role: "pollinator" }
          ],
          paths: [],
          score_breakdown: { total_score: 75 },
          warnings: ["Keep apples separate from loose seeded crops."],
          explanations: [],
          assumptions: []
        }}
      />
    );

    expect(screen.getByText("Chaos Garden Guidance")).toBeTruthy();
    expect(screen.getByText("Easy direct-sow crops")).toBeTruthy();
    expect(screen.getByText("Keep apart notes")).toBeTruthy();
    expect(screen.queryByText("Row diagram")).toBeNull();
    expect(screen.queryByRole("img", { name: /Raised bed/i })).toBeNull();
  });

  it("renders row layout from LayoutBlueprint design instructions", () => {
    render(
      <GardenLayoutGrid
        layout={{
          layout_id: 7,
          garden_id: 7,
          summary: "Blueprint rows",
          grid: { rows: 1, cols: 1, cell_size_ft: 1, orientation: "north_up", layout_style: "rows", access_paths: [], cells: [] },
          placements: [],
          paths: [],
          layout_blueprint: {
            layout_style: "rows",
            summary: "Blueprint",
            plant_symbols: [
              { symbol: "T", plant_slug: "tomato", cultivar_slug: null, display_name: "Tomato", role: "primary_crop" },
              { symbol: "B", plant_slug: "basil", cultivar_slug: null, display_name: "Basil", role: "companion_herb" },
              { symbol: "M", plant_slug: "marigold", cultivar_slug: null, display_name: "Marigold", role: "border_plant" }
            ],
            row_blueprint: {
              rows: [
                {
                  row_number: 1,
                  row_label: "Tomato (T) + nearby support",
                  primary_plants: ["tomato"],
                  companion_plants: ["basil"],
                  border_plants: ["marigold"],
                  spacing_from_prior_row_inches: null,
                  in_row_spacing_inches: 24,
                  row_role: "trellis",
                  notes: ["Basil is interplanted near tomatoes; marigolds go at row ends."]
                }
              ],
              row_spacing_notes: ["Keep potatoes away from tomatoes."],
              diagram_label_frequency: 1,
              north_orientation: "North ↑; row 1 is the northern row",
              tree_shrub_symbols: []
            },
            raised_bed_blueprint: null,
            chaos_blueprint: null,
            tree_shrub_section: null,
            placement_rules: [],
            warnings: [],
            assumptions: []
          },
          score_breakdown: { total_score: 75 },
          warnings: [],
          explanations: [],
          assumptions: []
        }}
      />
    );

    expect(screen.getByText("Row 1 — Tomato (T) + nearby support")).toBeTruthy();
    expect(screen.getByText(/Companions: Basil \(B\)/)).toBeTruthy();
    expect(screen.getByText(/Borders: Marigold \(M\)/)).toBeTruthy();
    expect(screen.getByText("Keep apart notes")).toBeTruthy();
  });

  it("renders raised bed SVG symbols from LayoutBlueprint quantities", () => {
    render(
      <GardenLayoutGrid
        layout={{
          layout_id: 8,
          garden_id: 7,
          summary: "Blueprint bed",
          grid: { rows: 1, cols: 1, cell_size_ft: 1, orientation: "north_up", layout_style: "raised_beds", access_paths: [], cells: [] },
          placements: [],
          paths: [],
          layout_blueprint: {
            layout_style: "raised_beds",
            summary: "Blueprint",
            plant_symbols: [{ symbol: "BB", plant_slug: "bee_balm", cultivar_slug: null, display_name: "Bee Balm", role: "pollinator_flower" }],
            row_blueprint: null,
            raised_bed_blueprint: {
              beds: [
                {
                  bed_id: "bed-1",
                  bed_name: "Bed 1",
                  length_ft: 8,
                  width_ft: 4,
                  symbol_legend: [{ symbol: "BB", plant_slug: "bee_balm", cultivar_slug: null, display_name: "Bee Balm", role: "pollinator_flower" }],
                  plantings: [],
                  border_plantings: [{ plant_slug: "bee_balm", cultivar_slug: null, symbol: "BB", quantity: 18, role: "pollinator_flower", approximate_zone: "border", near_plant_slugs: [], keep_away_from_slugs: [], rationale: "Border pollinator support." }],
                  companion_clusters: [],
                  notes: ["Border flowers are repeated around bed edges."],
                  warnings: []
                }
              ],
              unplaced_plants: [],
              tree_shrub_symbols: []
            },
            chaos_blueprint: null,
            tree_shrub_section: null,
            placement_rules: [],
            warnings: [],
            assumptions: []
          },
          score_breakdown: { total_score: 75 },
          warnings: [],
          explanations: [],
          assumptions: []
        }}
      />
    );

    expect(screen.getByText("Why plants are grouped")).toBeTruthy();
    expect(screen.getAllByText("BB").length).toBeGreaterThanOrEqual(18);
  });
});
