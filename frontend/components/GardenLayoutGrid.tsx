import type { GeneratedPlan, LayoutResult } from "@/types/api";
import { areaCategory, layoutQualityLabel, subscoreLabel } from "@/lib/product";

type Props = {
  layout?: LayoutResult | null;
  plan?: GeneratedPlan | null;
  areaSqFt?: number | null;
  showDetails?: boolean;
};

export function GardenLayoutGrid({ layout, plan, areaSqFt, showDetails = true }: Props) {
  const normalized = normalizeLayout(layout, plan);
  if (!normalized) return null;
  const totalScore = layout?.score_breakdown.total_score ?? 0;
  const cellSize = normalized.cellSizeFt ?? 2;
  return (
    <div className="rounded-md border border-border bg-white p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Garden Layout</h2>
          <div className="text-xs text-foreground/60">North ↑ · top of grid represents north</div>
        </div>
        <div className="rounded-md border border-border bg-muted/40 px-3 py-2 text-sm font-medium">
          {layout ? layoutQualityLabel(totalScore) : "Canonical Plan Layout"}
        </div>
      </div>
      <div className="mb-3 grid gap-2 text-xs sm:grid-cols-3">
        <div className="rounded border border-border bg-muted/30 px-2 py-1">Each cell = {cellSize} ft × {cellSize} ft</div>
        <div className="rounded border border-border bg-muted/30 px-2 py-1">Grid = {normalized.rows} rows × {normalized.cols} columns</div>
        {areaSqFt ? <div className="rounded border border-border bg-muted/30 px-2 py-1">{areaSqFt.toFixed(0)} sq ft · {areaCategory(areaSqFt)}</div> : null}
      </div>
      <div className="mb-3 flex flex-wrap gap-2 text-xs">
        <LegendSwatch className="border-emerald-300 bg-emerald-100" label="Crop" />
        <LegendSwatch className="border-sky-300 bg-sky-100" label="Companion" />
        <LegendSwatch className="border-fuchsia-300 bg-fuchsia-100" label="Pollinator/border" />
        <LegendSwatch className="border-stone-300 bg-stone-100" label="Path" />
        <LegendSwatch className="border-amber-300 bg-amber-100" label="Warning" />
      </div>
      <div className="grid gap-1" style={{ gridTemplateColumns: `repeat(${normalized.cols}, minmax(0, 1fr))` }}>
        {normalized.cells.map((cell) => (
          <div key={cell.cell_id} className={`flex min-h-16 flex-col justify-between rounded-sm border p-2 text-xs ${cellClass(cell)}`}>
            <span className="font-semibold">{cell.cell_id}</span>
            <span className="leading-tight">{cell.is_path ? "Path" : cell.label ?? ""}</span>
          </div>
        ))}
      </div>
      {showDetails && layout ? (
        <div className="mt-4 grid gap-2 text-xs sm:grid-cols-2">
          {Object.entries(layout.score_breakdown).filter(([key]) => key !== "total_score").map(([key, value]) => (
            <div key={key} className="rounded-md border border-border bg-muted/30 px-2 py-1">
              {scoreLabel(key)}: {subscoreLabel(value)}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function LegendSwatch({ className, label }: { className: string; label: string }) {
  return <div className="flex items-center gap-1"><span className={`h-3 w-3 rounded-sm border ${className}`} />{label}</div>;
}

function normalizeLayout(layout?: LayoutResult | null, plan?: GeneratedPlan | null) {
  if (layout) {
    return {
      rows: layout.grid.rows,
      cols: layout.grid.cols,
      cellSizeFt: layout.grid.cell_size_ft,
      cells: layout.grid.cells
    };
  }
  if (!plan) return null;
  const rows = plan.layout_grid.rows;
  const cols = plan.layout_grid.cols;
  const cells = plan.layout_grid.cells?.length ? plan.layout_grid.cells : Array.from({ length: rows * cols }).map((_, index) => {
    const row = Math.floor(index / cols);
    const col = index % cols;
    const item = plan.items.find((candidate) => candidate.row === row && candidate.col === col);
    return {
      cell_id: `${String.fromCharCode(65 + col)}${row + 1}`,
      row,
      col,
      available: true,
      is_path: false,
      plant_slug: item ? String(item.plant_id) : null,
      cultivar_slug: null,
      label: item?.label ?? null,
      notes: item?.notes ? [item.notes] : []
    };
  });
  return { rows, cols, cellSizeFt: plan.layout_grid.cell_size_ft ?? 2, cells };
}

function cellClass(cell: { is_path: boolean; plant_slug?: string | null; label?: string | null; notes?: string[] }) {
  const notes = (cell.notes ?? []).join(" ").toLowerCase();
  if (cell.is_path) return "border-stone-300 bg-stone-100 text-stone-700";
  if (notes.includes("warning")) return "border-amber-300 bg-amber-100 text-amber-950";
  if (notes.includes("pollinator") || notes.includes("border")) return "border-fuchsia-300 bg-fuchsia-100 text-fuchsia-950";
  if (notes.includes("companion") || notes.includes("near")) return "border-sky-300 bg-sky-100 text-sky-950";
  if (cell.plant_slug || cell.label) return "border-emerald-300 bg-emerald-100 text-emerald-950";
  return "border-border bg-muted/30 text-foreground/60";
}

function scoreLabel(key: string) {
  const labels: Record<string, string> = {
    spacing_score: "Spacing",
    companion_score: "Companion placement",
    conflict_score: "Conflict separation",
    access_score: "Access",
    sunlight_score: "Sunlight",
    size_fit_score: "Size fit",
    diversity_score: "Diversity"
  };
  return labels[key] ?? key.replaceAll("_", " ");
}
