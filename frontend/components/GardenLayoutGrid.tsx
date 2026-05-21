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

type NormalizedPlacement = LayoutResult["placements"][number];

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
          {totalScore == null ? null : <div className="text-foreground/60">Overall score {totalScore.toFixed(0)}/100</div>}
        </div>
      </div>

      <div className="mb-3 flex flex-wrap gap-2 text-xs text-foreground/70">
        <InfoChip label={layoutStyleLabel(normalized.grid.layout_style)} />
        <InfoChip label="North ↑" />
        <InfoChip label={normalized.grid.layout_style === "rows" ? "Rows run west to east." : normalized.grid.layout_style === "chaos" ? "Loose guidance, not a precise placement map." : `Each cell = ${normalized.grid.cell_size_ft.toFixed(0)} ft × ${normalized.grid.cell_size_ft.toFixed(0)} ft`} />
        <InfoChip label={normalized.grid.layout_style === "raised_beds" ? "Beds are separated by paths." : normalized.grid.layout_style === "chaos" ? "Keep taller plants north when practical." : `Top of grid represents north.`} />
        {normalized.area_sq_ft != null ? <InfoChip label={`${normalized.area_sq_ft.toFixed(0)} sq ft`} /> : null}
        {normalized.area_category ? <InfoChip label={normalized.area_category} /> : normalized.area_sq_ft != null ? <InfoChip label={areaCategoryLabel(normalized.area_sq_ft)} /> : null}
        {normalized.approximate_dimensions_ft ? (
          <InfoChip label={`Approx. ${normalized.approximate_dimensions_ft.width.toFixed(0)} ft × ${normalized.approximate_dimensions_ft.height.toFixed(0)} ft`} />
        ) : null}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_280px]">
        <div>
          <div className="mb-2 text-xs font-medium uppercase text-foreground/50">North ↑</div>
          {normalized.grid.layout_style === "chaos" ? (
            <ChaosLayoutView placements={normalized.placements} metadata={normalized.grid.layout_metadata} warnings={normalized.warnings} />
          ) : normalized.grid.layout_style === "rows" ? (
            <RowLayoutView placements={normalized.placements} />
          ) : normalized.grid.layout_style === "raised_beds" ? (
            <RaisedBedsView cells={normalized.grid.cells} placements={normalized.placements} metadata={normalized.grid.layout_metadata} />
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
    grid: { ...layout.grid, layout_style: layout.grid.layout_style ?? "grid", layout_metadata: layout.grid.layout_metadata ?? {} },
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
      layout_metadata: {},
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

function RowLayoutView({ placements }: { placements: LayoutResult["placements"] }) {
  const rowPlacements = placements.filter((item) => item.placement_role !== "tree" && item.placement_role !== "shrub").sort((a, b) => (a.row ?? 0) - (b.row ?? 0));
  const woodyPlacements = placements.filter((item) => item.placement_role === "tree" || item.placement_role === "shrub");
  const rowSymbols = buildSymbolMap(rowPlacements);
  const woodySymbols = buildTreeBushSymbolMap(woodyPlacements);
  return (
    <div className="space-y-4">
      {woodyPlacements.length ? <TreeBushLegend placements={woodyPlacements} symbols={woodySymbols} /> : null}
      <div className="rounded-md border border-border bg-muted/20 p-3">
        <div className="mb-2 font-semibold">Rows</div>
        <div className="space-y-2 text-sm">
          {rowPlacements.map((placement, index) => (
            <div key={`${placement.plant_slug}-${placement.row}`} className="flex flex-wrap items-center justify-between gap-3 rounded border border-border bg-white px-3 py-2">
              <div className="font-medium">Row {index + 1} — {displayPlacementName(placement)}</div>
              <div className="text-foreground/70">{index === 0 ? "start at north edge" : `${placement.row_spacing_inches ?? 0} in from prior row`} · {placement.spacing_inches ?? 0} in in-row</div>
            </div>
          ))}
        </div>
      </div>
      <div className="rounded-md border border-border bg-white p-3">
        <div className="mb-2 flex items-center justify-between gap-3 text-sm">
          <div className="font-semibold">Row diagram</div>
          <div className="text-xs text-foreground/60">North ↑ · rows run west to east</div>
        </div>
        <RowDiagram rows={rowPlacements} rowSymbols={rowSymbols} woody={woodyPlacements} woodySymbols={woodySymbols} />
      </div>
    </div>
  );
}

function RaisedBedsView({ cells, placements, metadata }: { cells: NormalizedCell[]; placements: LayoutResult["placements"]; metadata?: Record<string, unknown> }) {
  const groups = Array.from(new Set(cells.map((cell) => cell.group_id ?? "ungrouped"))).filter((group) => group !== "path" && group !== "ungrouped");
  if (!groups.length) return <GridLayoutView cells={cells} placements={placements} cols={4} />;
  const symbols = buildSymbolMap(placements);
  const outOfBedWoody = placements.filter((placement) => (placement.placement_role === "tree" || placement.placement_role === "shrub") && placement.grid_cells.length === 0);
  const woodySymbols = buildTreeBushSymbolMap(outOfBedWoody);
  const bedLength = numberMetadata(metadata, "bed_length_ft", 8);
  const bedWidth = numberMetadata(metadata, "bed_width_ft", 4);
  return (
    <div className="space-y-4">
      {outOfBedWoody.length ? <TreeBushLegend placements={outOfBedWoody} symbols={woodySymbols} /> : null}
      <div className="grid gap-4 xl:grid-cols-2">
        {groups.map((group) => {
        const bedCells = cells.filter((cell) => cell.group_id === group).sort((a, b) => a.row - b.row || a.col - b.col);
        const bedPlacements = placements.filter((placement) => placement.grid_cells.some((cellId) => bedCells.some((cell) => cell.cell_id === cellId)));
        const warnings = uniqueStrings(bedPlacements.flatMap((placement) => placement.warnings ?? []));
        return (
          <div key={group} className="rounded-md border border-emerald-200 bg-emerald-50/30 p-4">
            <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
              <div className="text-base font-semibold">{bedCells[0]?.group_label ?? titleCase(group)}</div>
              <div className="text-sm text-foreground/70">{bedWidth} ft × {bedLength} ft</div>
            </div>
            <PlantSymbolLegend placements={bedPlacements} symbols={symbols} />
            <RaisedBedSvg cells={bedCells} placements={bedPlacements} symbols={symbols} widthFt={bedWidth} lengthFt={bedLength} />
            {warnings.length ? (
              <div className="mt-3 space-y-1 text-xs text-foreground/70">
                {warnings.map((warning) => <div key={warning} className="text-amber-800">{warning}</div>)}
              </div>
            ) : null}
          </div>
        );
        })}
      </div>
    </div>
  );
}

function RaisedBedSvg({ cells, placements, symbols, widthFt, lengthFt }: { cells: NormalizedCell[]; placements: NormalizedPlacement[]; symbols: Map<string, string>; widthFt: number; lengthFt: number }) {
  const tokens = placements.flatMap((placement) => {
    const symbol = symbols.get(displayPlacementName(placement)) ?? "?";
    return Array.from({ length: Math.max(1, Math.min(placement.quantity ?? 1, 96)) }, (_, index) => ({ key: `${placement.plant_slug}-${index}`, symbol }));
  });
  const total = tokens.length;
  const columns = Math.max(2, Math.ceil(Math.sqrt(total * Math.max(lengthFt / Math.max(widthFt, 1), 1))));
  const rows = Math.max(1, Math.ceil(total / columns));
  const fontSize = total > 72 ? 5 : total > 40 ? 6 : total > 24 ? 7 : 9;
  return (
    <svg className="mt-3 h-72 w-full rounded border border-emerald-300 bg-white" viewBox="0 0 280 190" role="img" aria-label={`Raised bed ${widthFt} ft by ${lengthFt} ft`}>
      <text x="12" y="18" className="fill-slate-700 text-[10px] font-semibold">North ↑</text>
      <text x="268" y="18" textAnchor="end" className="fill-slate-500 text-[9px]">{widthFt} ft × {lengthFt} ft</text>
      <rect x="18" y="32" width="244" height="132" rx="3" fill="#f7fee7" stroke="#15803d" strokeWidth="2" />
      {tokens.map((token, index) => {
        const colIndex = index % columns;
        const rowIndex = Math.floor(index / columns);
        const x = 30 + (colIndex + 0.5) * (220 / Math.max(columns, 1));
        const y = 46 + (rowIndex + 0.5) * (104 / Math.max(rows, 1));
        return (
          <g key={token.key}>
            <circle cx={x} cy={y} r={fontSize + 4} fill="#dcfce7" stroke="#16a34a" />
            <text x={x} y={y + fontSize / 3} textAnchor="middle" className="fill-slate-900 font-bold" style={{ fontSize }}>{token.symbol}</text>
          </g>
        );
      })}
      {placements.some((placement) => (placement.quantity ?? 1) > 96) ? <text x="140" y="178" textAnchor="middle" className="fill-slate-600 text-[8px]">Some high quantities are summarized after the first 96 plantings.</text> : null}
    </svg>
  );
}

function RowDiagram({ rows, rowSymbols, woody, woodySymbols }: { rows: NormalizedPlacement[]; rowSymbols: Map<string, string>; woody: NormalizedPlacement[]; woodySymbols: Map<string, string> }) {
  const rowGap = 92 / Math.max(rows.length, 1);
  const labelInterval = rowLabelInterval(rows.length);
  return (
    <svg className="h-72 w-full rounded border border-border bg-white" viewBox="0 0 320 210" role="img" aria-label="Row planting diagram">
      <text x="16" y="20" className="fill-slate-700 text-[11px] font-semibold">North ↑</text>
      <rect x="18" y="34" width="284" height="152" rx="3" fill="#f8fafc" stroke="#334155" strokeWidth="1.5" />
      {rows.map((placement, index) => {
        const y = 54 + index * rowGap;
        return (
          <g key={`${placement.plant_slug}-${index}`}>
            <line x1="34" x2="286" y1={y} y2={y} stroke="#15803d" strokeWidth="3" />
            {index % labelInterval === 0 ? <text x="42" y={y - 6} className="fill-slate-900 text-[10px] font-semibold">Row {index + 1}: {displayPlacementName(placement)} ({rowSymbols.get(displayPlacementName(placement))})</text> : null}
          </g>
        );
      })}
      {woody.map((placement, index) => {
        const symbol = woodySymbols.get(displayPlacementName(placement)) ?? "?";
        return (
          <g key={`${placement.plant_slug}-${index}`}>
            <circle cx={52 + index * 38} cy="170" r="13" fill="#e7e5e4" stroke="#78716c" />
            <text x={52 + index * 38} y="174" textAnchor="middle" className="fill-slate-900 text-[9px] font-bold">{symbol}</text>
          </g>
        );
      })}
      <text x="160" y="202" textAnchor="middle" className="fill-slate-500 text-[9px]">Rows run west to east</text>
    </svg>
  );
}

function ChaosLayoutView({ placements, metadata, warnings }: { placements: NormalizedPlacement[]; metadata?: Record<string, unknown>; warnings: string[] }) {
  const groups = chaosGroups(placements, metadata);
  const guidance = stringArrayMetadata(metadata, "guidance");
  const suggestedRange = typeof metadata?.suggested_plant_count_range === "string" ? metadata.suggested_plant_count_range : "6-12";
  return (
    <div className="space-y-4">
      <div className="rounded-md border border-amber-200 bg-amber-50 p-4">
        <div className="text-base font-semibold">Chaos Garden Guidance</div>
        <p className="mt-1 text-sm text-amber-950">Chaos mode gives you a loose planting strategy instead of a precise map. Use clusters, borders, and separation notes rather than rows or beds.</p>
        <div className="mt-3 text-sm font-medium">Suggested plant type range: {suggestedRange}</div>
      </div>
      <div className="grid gap-3 lg:grid-cols-2">
        {Object.entries(groups).map(([label, items]) => (
          <div key={label} className="rounded-md border border-border bg-white p-3">
            <div className="mb-2 font-semibold">{label}</div>
            <div className="space-y-1 text-sm text-foreground/70">
              {items.length ? items.map((item) => <div key={item}>• {item}</div>) : <div>Not enough selected plants for this group.</div>}
            </div>
          </div>
        ))}
      </div>
      <MessageBlock title="Scatter and cluster guidance" items={guidance.length ? guidance : ["Scatter seed in small clusters instead of rows.", "Keep taller plants toward the north edge when practical.", "Use pollinator flowers around borders and between crop clusters."]} />
      {warnings.length ? <MessageBlock title="Keep apart notes" items={warnings} tone="warning" /> : null}
    </div>
  );
}

function PlantSymbolLegend({ placements, symbols }: { placements: NormalizedPlacement[]; symbols: Map<string, string> }) {
  if (!placements.length) return null;
  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
      {placements.map((placement) => {
        const name = displayPlacementName(placement);
        return <div key={`${placement.plant_slug}-${placement.cultivar_slug ?? ""}`}><span className="font-semibold">{symbols.get(name)}</span> — {name}</div>;
      })}
    </div>
  );
}

function TreeBushLegend({ placements, symbols }: { placements: NormalizedPlacement[]; symbols: Map<string, string> }) {
  return (
    <div className="rounded-md border border-stone-300 bg-stone-50 p-3">
      <div className="mb-2 font-semibold">Trees & Bushes</div>
      <div className="grid gap-1 text-sm sm:grid-cols-2">
        {placements.map((placement) => {
          const name = displayPlacementName(placement);
          return <div key={`${placement.plant_slug}-${placement.cultivar_slug ?? ""}`}><span className="font-semibold">{symbols.get(name)}</span> — {name}</div>;
        })}
      </div>
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
  if (style === "chaos") return "Chaos";
  return "Grid";
}

function buildSymbolMap(placements: NormalizedPlacement[]) {
  const symbols = new Map<string, string>();
  const used = new Set<string>();
  placements.forEach((placement) => {
    const name = displayPlacementName(placement);
    symbols.set(name, getPlantSymbol(name, used));
  });
  return symbols;
}

function buildTreeBushSymbolMap(placements: NormalizedPlacement[]) {
  const counters = new Map<string, number>();
  const symbols = new Map<string, string>();
  placements.forEach((placement) => {
    const name = displayPlacementName(placement);
    const prefix = placement.placement_role === "shrub" ? "B" : treePrefix(name);
    const next = (counters.get(prefix) ?? 0) + 1;
    counters.set(prefix, next);
    symbols.set(name, `${prefix}${next}`);
  });
  return symbols;
}

function getPlantSymbol(plantName: string, existingSymbols: Set<string>) {
  const words = plantName.replace(/[^A-Za-z0-9 ]/g, " ").split(/\s+/).filter(Boolean);
  const candidates = [
    words.slice(0, 2).map((word) => word[0]?.toUpperCase()).join(""),
    firstLetter(plantName),
    plantName.slice(0, 2).replace(/[^A-Za-z0-9]/g, "").replace(/^\w/, (value) => value.toUpperCase())
  ].filter(Boolean);
  for (const candidate of candidates) {
    if (!existingSymbols.has(candidate)) {
      existingSymbols.add(candidate);
      return candidate;
    }
  }
  const base = firstLetter(plantName);
  let index = 1;
  while (existingSymbols.has(`${base}${index}`)) index += 1;
  const symbol = `${base}${index}`;
  existingSymbols.add(symbol);
  return symbol;
}

function firstLetter(value: string) {
  return (value.match(/[A-Za-z0-9]/)?.[0] ?? "P").toUpperCase();
}

function treePrefix(value: string) {
  const words = value.replace(/[^A-Za-z0-9 ]/g, " ").split(/\s+/).filter(Boolean);
  const treeWord = words.find((word) => /apple|pear|peach|plum|cherry/i.test(word));
  return firstLetter(treeWord ?? words[words.length - 1] ?? value);
}

function numberMetadata(metadata: Record<string, unknown> | undefined, key: string, fallback: number) {
  const value = metadata?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function stringArrayMetadata(metadata: Record<string, unknown> | undefined, key: string) {
  const value = metadata?.[key];
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function chaosGroups(placements: NormalizedPlacement[], metadata?: Record<string, unknown>) {
  const raw = metadata?.plant_groups;
  if (raw && typeof raw === "object" && !Array.isArray(raw)) {
    const record = raw as Record<string, unknown>;
    return {
      "Easy direct-sow crops": normalizeGroup(record.easy_direct_sow_crops),
      "Pollinator/support flowers": normalizeGroup(record.pollinator_support_flowers),
      Herbs: normalizeGroup(record.herbs),
      "Larger/sprawling crops": normalizeGroup(record.larger_sprawling_crops),
      "Avoid or separate": normalizeGroup(record.avoid_or_separate),
    };
  }
  return {
    "Easy direct-sow crops": placements.filter((item) => !["tree", "shrub", "pollinator"].includes(item.placement_role ?? "")).map(displayPlacementName),
    "Pollinator/support flowers": placements.filter((item) => item.placement_role === "pollinator").map(displayPlacementName),
    Herbs: placements.filter((item) => item.placement_role === "companion").map(displayPlacementName),
    "Larger/sprawling crops": placements.filter((item) => (item.row_spacing_inches ?? item.spacing_inches ?? 0) >= 48).map(displayPlacementName),
    "Avoid or separate": placements.filter((item) => item.placement_role === "tree" || item.placement_role === "shrub" || item.warnings.length).map(displayPlacementName),
  };
}

function normalizeGroup(value: unknown) {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function rowLabelInterval(count: number) {
  if (count <= 8) return 1;
  if (count <= 20) return 2;
  if (count <= 50) return 5;
  return 10;
}

function uniqueStrings(values: string[]) {
  return Array.from(new Set(values.filter(Boolean)));
}

function columnLabel(col: number) {
  return String.fromCharCode(65 + col);
}

function InfoChip({ label }: { label: string }) {
  return <span className="rounded-full border border-border bg-muted/40 px-2 py-1">{label}</span>;
}

function ScoreLine({ label, value }: { label: string; value?: number | null }) {
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
