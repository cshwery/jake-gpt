"use client";

import React from "react";
import type { GeneratedPlan, LayoutResult } from "@/types/api";
import { areaCategory as areaCategoryLabel, layoutQualityLabel, subscoreLabel, titleCase } from "@/lib/product";

type Props = {
  layout?: LayoutResult | null;
  generatedPlan?: GeneratedPlan | null;
  title?: string;
  showLegend?: boolean;
  className?: string;
};

type NormalizedCell = {
  cell_id: string;
  row: number;
  col: number;
  available: boolean;
  is_path: boolean;
  plant_slug?: string | null;
  cultivar_slug?: string | null;
  label?: string | null;
  notes: string[];
  placement_role?: string | null;
  group_id?: string | null;
  group_label?: string | null;
};

export function GardenLayoutGrid({ layout, generatedPlan, title = "Layout", showLegend = true, className = "" }: Props) {
  const normalized = layout ? normalizeLayout(layout) : normalizePlan(generatedPlan);
  if (normalized == null) {
    return <div className={`rounded-md border border-border bg-white p-4 text-sm text-foreground/70 ${className}`}>No layout available yet.</div>;
  }

  const totalScore = normalized.score_breakdown?.total_score ?? null;
  const qualityLabel = totalScore == null ? "Layout preview" : layoutQualityLabel(totalScore);

  return (
    <div className={`rounded-md border border-border bg-white p-4 ${className}`}>
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">{title}</h2>
          <div className="mt-1 text-sm text-foreground/70">{normalized.summary}</div>
        </div>
        <div className="flex flex-col items-end gap-1 text-right text-sm">
          <div className="font-semibold">{qualityLabel}</div>
          {totalScore == null ? null : <div className="text-foreground/60">Overall score hidden in UI</div>}
        </div>
      </div>

      <div className="mb-3 flex flex-wrap gap-2 text-xs text-foreground/70">
        <InfoChip label={layoutStyleLabel(normalized.grid.layout_style)} />
        <InfoChip label="North ↑" />
        <InfoChip label={normalized.grid.layout_style === "rows" ? "Rows run west to east." : `Each cell = ${normalized.grid.cell_size_ft.toFixed(0)} ft × ${normalized.grid.cell_size_ft.toFixed(0)} ft`} />
        <InfoChip label={normalized.grid.layout_style === "raised_beds" ? "Beds are separated by paths." : `Top of grid represents north.`} />
        {normalized.area_sq_ft != null ? <InfoChip label={`${normalized.area_sq_ft.toFixed(0)} sq ft`} /> : null}
        {normalized.area_category ? <InfoChip label={normalized.area_category} /> : normalized.area_sq_ft != null ? <InfoChip label={areaCategoryLabel(normalized.area_sq_ft)} /> : null}
        {normalized.approximate_dimensions_ft ? (
          <InfoChip label={`Approx. ${normalized.approximate_dimensions_ft.width.toFixed(0)} ft × ${normalized.approximate_dimensions_ft.height.toFixed(0)} ft`} />
        ) : null}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_280px]">
        <div>
          <div className="mb-2 text-xs font-medium uppercase text-foreground/50">North ↑</div>
          {normalized.grid.layout_style === "rows" ? (
            <RowLayoutView cells={normalized.grid.cells} placements={normalized.placements} />
          ) : normalized.grid.layout_style === "raised_beds" ? (
            <RaisedBedsView cells={normalized.grid.cells} placements={normalized.placements} cols={normalized.grid.cols} />
          ) : (
            <GridLayoutView cells={normalized.grid.cells} placements={normalized.placements} cols={normalized.grid.cols} />
          )}
        </div>

        <div className="space-y-3 text-sm">
          {normalized.score_breakdown ? (
            <div className="rounded-md border border-border bg-muted/30 p-3">
              <div className="mb-2 font-semibold">Layout quality</div>
              <div className="space-y-1 text-foreground/70">
                <ScoreLine label="Spacing" value={normalized.score_breakdown.spacing_score} />
                <ScoreLine label="Companion placement" value={normalized.score_breakdown.companion_score} />
                <ScoreLine label="Conflict" value={normalized.score_breakdown.conflict_score} />
                <ScoreLine label="Access" value={normalized.score_breakdown.access_score} />
                <ScoreLine label="Sunlight" value={normalized.score_breakdown.sunlight_score} />
                <ScoreLine label="Size fit" value={normalized.score_breakdown.size_fit_score} />
                <ScoreLine label="Diversity" value={normalized.score_breakdown.diversity_score} />
              </div>
            </div>
          ) : null}

          {normalized.placements.length ? (
            <div className="rounded-md border border-border bg-muted/30 p-3">
              <div className="mb-2 font-semibold">Placements</div>
              <div className="space-y-2 text-foreground/70">
                {normalized.placements.map((placement) => (
                  <div key={`${placement.plant_slug}-${placement.grid_cells.join("-")}`}>
                    <div className="font-medium text-foreground">{displayPlacementName(placement)}</div>
                    <div className="text-xs">
                      {placement.placement_role ? `${roleLabel(placement.placement_role)} · ` : ""}
                      Cells {placement.grid_cells.join(", ")}
                    </div>
                    {placement.location_notes ? <div className="text-xs">{placement.location_notes}</div> : null}
                    {placement.warnings.length ? <div className="text-xs text-amber-700">{placement.warnings.join(" ")}</div> : null}
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {normalized.warnings.length ? <MessageBlock title="Warnings" items={normalized.warnings} tone="warning" /> : null}
          {normalized.explanations.length ? <MessageBlock title="Why this layout" items={normalized.explanations} /> : null}
          {normalized.assumptions.length ? <MessageBlock title="Assumptions" items={normalized.assumptions} /> : null}
          {showLegend ? (
            <div className="rounded-md border border-border bg-muted/30 p-3">
              <div className="mb-2 font-semibold">Legend</div>
              <div className="flex flex-wrap gap-2 text-xs text-foreground/70">
                <InfoChip label="Crop" />
                <InfoChip label="Companion" />
                <InfoChip label="Pollinator/border" />
                <InfoChip label="Path" />
                {normalized.grid.layout_style === "raised_beds" ? <InfoChip label="Raised bed" /> : null}
                {normalized.grid.layout_style === "rows" ? <InfoChip label="Planting row" /> : null}
                <InfoChip label="Warning" />
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function normalizeLayout(layout: LayoutResult) {
  return {
    grid: { ...layout.grid, layout_style: layout.grid.layout_style ?? "grid" },
    placements: layout.placements,
    score_breakdown: layout.score_breakdown,
    warnings: layout.warnings ?? [],
    explanations: layout.explanations ?? [],
    assumptions: layout.assumptions ?? [],
    summary: layout.summary,
    area_sq_ft: layout.area_sq_ft ?? null,
    area_category: layout.area_category ?? null,
    approximate_dimensions_ft: layout.approximate_dimensions_ft ?? null
  };
}

function normalizePlan(plan?: GeneratedPlan | null) {
  if (!plan) return null;
  const cells: NormalizedCell[] = [];
  for (let row = 0; row < plan.layout_grid.rows; row += 1) {
    for (let col = 0; col < plan.layout_grid.cols; col += 1) {
      const cell_id = `${columnLabel(col)}${row + 1}`;
      const item = plan.items.find((entry) => entry.row === row && entry.col === col);
      cells.push({
        cell_id,
        row,
        col,
        available: true,
        is_path: plan.layout_grid.access_paths?.length ? col === Math.floor(plan.layout_grid.cols / 2) : false,
        plant_slug: item ? item.label.toLowerCase().replace(/\s+/g, "-") : null,
        label: item?.label ?? null,
        notes: item?.notes ? [item.notes] : [],
      });
    }
  }
  return {
    grid: {
      rows: plan.layout_grid.rows,
      cols: plan.layout_grid.cols,
      cell_size_ft: 2,
      orientation: "north_up",
      layout_style: "grid",
      cells,
      access_paths: plan.layout_grid.access_paths ?? []
    },
    placements: plan.items.map((item) => ({
      plant_slug: item.label.toLowerCase().replace(/\s+/g, "-"),
      plant_common_name: item.label,
      quantity: item.quantity,
      grid_cells: [`${columnLabel(item.col)}${item.row + 1}`],
      row: item.row,
      col: item.col,
      width: item.width,
      height: item.height,
      x_pct: item.x_pct,
      y_pct: item.y_pct,
      location_notes: item.notes ?? null,
      warnings: [],
      placement_role: "crop"
    })),
    score_breakdown: null,
    warnings: [],
    explanations: [],
    assumptions: [],
    summary: plan.summary,
    area_sq_ft: null,
    area_category: null,
    approximate_dimensions_ft: null
  };
}

function displayPlacementName(placement: { plant_common_name: string; cultivar_name?: string | null }) {
  if (placement.cultivar_name) {
    return `${titleCase(placement.plant_common_name)} — ${placement.cultivar_name}`;
  }
  return titleCase(placement.plant_common_name);
}

function roleLabel(role: string) {
  const labels: Record<string, string> = {
    crop: "Crop",
    companion: "Companion",
    pollinator: "Pollinator",
    border: "Border",
    path: "Path",
    support: "Support",
    tree: "Tree",
    shrub: "Shrub"
  };
  return labels[role] ?? titleCase(role);
}

function roleStyles(role: string | null | undefined, hasPlant: boolean) {
  const base = hasPlant ? "border-primary/40 bg-primary/10 text-foreground" : "border-border bg-muted/30 text-foreground/70";
  switch (role) {
    case "companion":
      return `${base} border-emerald-300 bg-emerald-50`;
    case "pollinator":
    case "border":
      return `${base} border-amber-300 bg-amber-50`;
    case "tree":
    case "shrub":
      return `${base} border-stone-400 bg-stone-100`;
    default:
      return base;
  }
}

function inferRole(cell: NormalizedCell, placements: LayoutResult["placements"]) {
  const placement = placements.find((entry) => entry.grid_cells.includes(cell.cell_id));
  return placement?.placement_role ?? null;
}

function GridLayoutView({ cells, placements, cols }: { cells: NormalizedCell[]; placements: LayoutResult["placements"]; cols: number }) {
  return (
    <div className="grid gap-1" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}>
      {cells.map((cell) => <LayoutCell key={cell.cell_id} cell={cell} role={cell.placement_role ?? inferRole(cell, placements)} />)}
    </div>
  );
}

function RowLayoutView({ cells, placements }: { cells: NormalizedCell[]; placements: LayoutResult["placements"] }) {
  const rows = Array.from(new Set(cells.map((cell) => cell.row))).sort((a, b) => a - b);
  return (
    <div className="space-y-2">
      {rows.map((row) => {
        const rowCells = cells.filter((cell) => cell.row === row).sort((a, b) => a.col - b.col);
        const placement = placements.find((item) => item.row === row || item.grid_cells.some((cellId) => rowCells.some((cell) => cell.cell_id === cellId)));
        return (
          <div key={row} className="rounded-md border border-border bg-muted/20 p-2">
            <div className="mb-1 flex items-center justify-between gap-2 text-xs">
              <span className="font-semibold">{rowCells[0]?.group_label ?? `Row ${row + 1}`}</span>
              {placement ? <span className="text-foreground/60">{displayPlacementName(placement)} · {placement.quantity} plantings</span> : null}
            </div>
            <div className="grid gap-1" style={{ gridTemplateColumns: `repeat(${rowCells.length}, minmax(0, 1fr))` }}>
              {rowCells.map((cell) => <LayoutCell key={cell.cell_id} cell={cell} role={cell.placement_role ?? inferRole(cell, placements)} compact />)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function RaisedBedsView({ cells, placements, cols }: { cells: NormalizedCell[]; placements: LayoutResult["placements"]; cols: number }) {
  const groups = Array.from(new Set(cells.map((cell) => cell.group_id ?? "ungrouped"))).filter((group) => group !== "path" && group !== "ungrouped");
  if (!groups.length) return <GridLayoutView cells={cells} placements={placements} cols={cols} />;
  return (
    <div className="space-y-3">
      {groups.map((group) => {
        const bedCells = cells.filter((cell) => cell.group_id === group).sort((a, b) => a.row - b.row || a.col - b.col);
        const bedRows = Array.from(new Set(bedCells.map((cell) => cell.row))).sort((a, b) => a - b);
        return (
          <div key={group} className="rounded-md border border-emerald-200 bg-emerald-50/40 p-3">
            <div className="mb-2 text-sm font-semibold">{bedCells[0]?.group_label ?? titleCase(group)}</div>
            <div className="grid gap-1" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}>
              {bedRows.flatMap((row) =>
                bedCells
                  .filter((cell) => cell.row === row)
                  .sort((a, b) => a.col - b.col)
                  .map((cell) => <LayoutCell key={cell.cell_id} cell={cell} role={cell.placement_role ?? inferRole(cell, placements)} compact />)
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function LayoutCell({ cell, role, compact = false }: { cell: NormalizedCell; role: string | null | undefined; compact?: boolean }) {
  return (
    <div
      className={`flex flex-col justify-between rounded-sm border p-2 text-xs ${
        compact ? "min-h-10" : "min-h-16"
      } ${cell.is_path ? "border-stone-300 bg-stone-100 text-stone-600" : cell.label ? roleStyles(role, true) : "border-border bg-muted/30 text-foreground/70"}`}
    >
      <span className="font-semibold">{cell.cell_id}</span>
      <span className={compact ? "truncate" : ""}>{cell.is_path ? "Path" : cell.label ? titleCase(cell.label) : "Open"}</span>
    </div>
  );
}

function layoutStyleLabel(style?: string | null) {
  if (style === "raised_beds") return "Raised beds";
  if (style === "rows") return "Rows";
  return "Grid";
}

function columnLabel(col: number) {
  return String.fromCharCode(65 + col);
}

function InfoChip({ label }: { label: string }) {
  return <span className="rounded-full border border-border bg-muted/40 px-2 py-1">{label}</span>;
}

function ScoreLine({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span>{label}</span>
      <span className="font-medium">{subscoreLabel(value)}</span>
    </div>
  );
}

function MessageBlock({ title, items, tone = "default" }: { title: string; items: string[]; tone?: "default" | "warning" }) {
  return (
    <div className={`rounded-md border p-3 ${tone === "warning" ? "border-amber-200 bg-amber-50 text-amber-900" : "border-border bg-muted/30"}`}>
      <div className="mb-2 font-semibold">{title}</div>
      <ul className="space-y-1 text-sm">
        {items.map((item) => (
          <li key={item}>• {item}</li>
        ))}
      </ul>
    </div>
  );
}
