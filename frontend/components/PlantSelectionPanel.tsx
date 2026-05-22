"use client";

import React from "react";
import { Sprout, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { GardenGoals, GardenRecommendationResult, LayoutResult, PlantSearchResult } from "@/types/api";
import {
  dedupePlantResults,
  displayPlantResultName,
  recommendationSelectionKey,
  recommendationTarget,
  selectionKeyForPlantResult
} from "@/lib/plantSelection";
import { fitLabel, recommendationLabel, recommendationReasonLabel } from "@/lib/product";

type SelectedPlantItem = PlantSearchResult & { selection_key: string };

type Props = {
  plantResults: PlantSearchResult[];
  plantQuery: string;
  setPlantQuery: (query: string) => void;
  selectedPlants: SelectedPlantItem[];
  onToggleSelection: (plant: PlantSearchResult) => void;
  recommendations: GardenRecommendationResult | null;
  goals: GardenGoals;
  onGenerateRecommendations: () => Promise<void>;
  onGenerateLayout: () => Promise<LayoutResult | void>;
  loadingRecommendations?: boolean;
  showIncompatiblePlants?: boolean;
  setShowIncompatiblePlants?: (value: boolean) => void;
};

export function PlantSelectionPanel({
  plantResults,
  plantQuery,
  setPlantQuery,
  selectedPlants,
  onToggleSelection,
  recommendations,
  goals,
  onGenerateRecommendations,
  onGenerateLayout,
  loadingRecommendations = false,
  showIncompatiblePlants = false,
  setShowIncompatiblePlants
}: Props) {
  const selectedKeys = new Set(selectedPlants.map((item) => item.selection_key));
  const species = dedupePlantResults(plantResults.filter((item) => item.result_type === "species"));
  const cultivars = dedupePlantResults(plantResults.filter((item) => item.result_type === "cultivar"));
  const recommendationCards = recommendations?.recommendations.slice(0, 8) ?? [];

  return (
    <div className="space-y-5">
      <SelectedPlantsSummary selectedPlants={selectedPlants} onGenerateLayout={onGenerateLayout} />
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-5">
        <Card>
          <h2 className="mb-2 text-lg font-semibold">Search plants</h2>
          <p className="mb-3 text-sm text-foreground/70">Pick plants you definitely want to include. JakeGPT will recommend good supplemental plant choices.</p>
          <p className="mb-4 text-sm text-foreground/70">Search species and cultivars. Cultivar names appear under their parent species.</p>
          <div className="flex gap-2">
            <Input value={plantQuery} onChange={(event) => setPlantQuery(event.target.value)} placeholder="Search tomato, basil, Sungold..." />
            <Button className="shrink-0" type="button" onClick={onGenerateRecommendations} disabled={loadingRecommendations}>
              <Sprout className="mr-2 h-4 w-4" />
              {loadingRecommendations ? "Generating..." : "Generate Recommendations"}
            </Button>
          </div>
          {setShowIncompatiblePlants ? (
            <label className="mt-3 flex items-center gap-2 text-sm text-foreground/70">
              <input type="checkbox" checked={showIncompatiblePlants} onChange={(event) => setShowIncompatiblePlants(event.target.checked)} />
              Show plants not recommended for my zone
            </label>
          ) : null}
        </Card>

        {recommendations ? (
          <Card>
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
              <h3 className="text-lg font-semibold">Recommendations</h3>
              <Button type="button" disabled={selectedPlants.length === 0} onClick={onGenerateLayout}>
                Generate Layout
              </Button>
            </div>
            <p className="mb-4 text-sm text-foreground/70">{recommendations.summary}</p>
            {recommendations.warnings.length ? (
              <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                {recommendations.warnings.map((warning) => (
                  <div key={`${warning.warning_type}-${warning.plant_slugs.join("-")}`}>{gardenerWarning(warning.message)}</div>
                ))}
              </div>
            ) : null}
            <div className="grid gap-3 lg:grid-cols-2">
              {recommendationCards.map((item) => {
                const selectionKey = recommendationSelectionKey(item.plant_slug, item.cultivar_recommendations[0]?.cultivar_slug ?? null);
                const selected = selectedKeys.has(selectionKey);
                const targetPlant = recommendationTarget(item, plantResults);
                return (
                  <div key={`${item.plant_slug}-${item.cultivar_recommendations[0]?.cultivar_slug ?? "species"}`} className="rounded-md border border-border bg-white p-3 text-sm">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="font-semibold">{item.plant_common_name}{item.cultivar_recommendations[0]?.cultivar_name ? ` — ${item.cultivar_recommendations[0].cultivar_name}` : ""}</div>
                        <div className="mt-1 flex flex-wrap gap-2 text-xs text-foreground/60">
                          <span className="rounded-full border border-border bg-muted/40 px-2 py-0.5">{recommendationLabel(item.recommendation_type)}</span>
                          <span className="rounded-full border border-border bg-muted/40 px-2 py-0.5">{fitLabel(item.score)}</span>
                        </div>
                      </div>
                      <Button
                        className={selected ? "h-8 bg-emerald-600 px-3 text-xs text-white" : "h-8 px-3 text-xs"}
                        type="button"
                        aria-label={`${selected ? "Remove" : "Add"} ${item.plant_common_name}${item.cultivar_recommendations[0]?.cultivar_name ? ` — ${item.cultivar_recommendations[0].cultivar_name}` : ""}`}
                        onClick={() => targetPlant ? onToggleSelection(targetPlant) : undefined}
                      >
                        {selected ? "Added ✓" : "Add"}
                      </Button>
                    </div>
                    <div className="mt-2 space-y-1 text-foreground/70">
                      <div>{item.explanation}</div>
                      <ul className="list-inside list-disc text-xs">
                        {item.reason_codes.slice(0, 3).map((code) => <li key={code}>{recommendationReasonLabel(code)}</li>)}
                      </ul>
                    </div>
                    {item.warnings.length ? <div className="mt-2 rounded border border-amber-200 bg-amber-50 p-2 text-xs text-amber-900">{item.warnings.map(gardenerWarning).join(" ")}</div> : null}
                  </div>
                );
              })}
            </div>
            <div className="mt-4 flex justify-end">
              <Button type="button" disabled={selectedPlants.length === 0} onClick={onGenerateLayout}>
                Generate Layout
              </Button>
            </div>
          </Card>
        ) : null}

        <Card>
          <h3 className="mb-3 text-lg font-semibold">Species</h3>
          <div className="max-h-[540px] overflow-y-auto pr-2">
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {species.map((plant) => (
              <PlantCard key={selectionKeyForPlantResult(plant)} plant={plant} selected={selectedKeys.has(selectionKeyForPlantResult(plant))} onToggle={onToggleSelection} />
            ))}
            </div>
          </div>
        </Card>

        {cultivars.length ? (
          <Card>
            <h3 className="mb-3 text-lg font-semibold">Cultivars</h3>
            <div className="max-h-[420px] overflow-y-auto pr-2">
              <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
              {cultivars.map((plant) => (
                <PlantCard key={selectionKeyForPlantResult(plant)} plant={plant} selected={selectedKeys.has(selectionKeyForPlantResult(plant))} onToggle={onToggleSelection} />
              ))}
              </div>
            </div>
          </Card>
        ) : null}
      </div>

        <div className="space-y-4">
          <Card>
            <h3 className="mb-3 text-lg font-semibold">Next steps</h3>
            <div className="space-y-2 text-sm text-foreground/70">
              <div>Selected plants: {selectedPlants.length}</div>
              <div>Goal: {goals.goal}</div>
              <div>Planting style: {goals.planting_style ?? "rows"}</div>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button className="w-full" disabled={selectedPlants.length === 0} onClick={onGenerateLayout}>Generate Layout</Button>
            </div>
          </Card>
          <SelectedPlantsTray selectedPlants={selectedPlants} onToggleSelection={onToggleSelection} />
        </div>
      </div>
    </div>
  );
}

function gardenerWarning(message: string) {
  const internalNightshade = "Nightshade crops can share disease and pest pressure; close clustering should be flagged as a risk rather than a beneficial pairing.";
  if (message.includes(internalNightshade)) {
    return message.replace(
      internalNightshade,
      "Tomatoes, peppers, eggplants, and potatoes are all nightshades. Try not to cluster them too closely because they can share pest and disease pressure."
    );
  }
  return message
    .replace("flagged as a risk rather than a beneficial pairing", "treated as something to separate in the garden")
    .replace("beneficial pairing", "helpful pairing");
}

function SelectedPlantsSummary({
  selectedPlants,
  onGenerateLayout
}: {
  selectedPlants: SelectedPlantItem[];
  onGenerateLayout: () => Promise<LayoutResult | void>;
}) {
  return (
    <div className="rounded-md border border-border bg-white px-4 py-3 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-semibold">Selected plants: {selectedPlants.length}</div>
          <div className="mt-1 flex max-h-16 flex-wrap gap-2 overflow-y-auto pr-2 text-xs text-foreground/70">
            {selectedPlants.length ? selectedPlants.map((item) => (
              <span key={item.selection_key} className="rounded-full border border-border bg-muted/40 px-2 py-1">
                {displayPlantResultName(item)}
              </span>
            )) : <span>No plants selected yet.</span>}
          </div>
        </div>
        <Button type="button" disabled={selectedPlants.length === 0} onClick={onGenerateLayout}>
          Generate Layout
        </Button>
      </div>
    </div>
  );
}

function SelectedPlantsTray({
  selectedPlants,
  onToggleSelection
}: {
  selectedPlants: SelectedPlantItem[];
  onToggleSelection: (plant: PlantSearchResult) => void;
}) {
  return (
    <Card>
      <h3 className="mb-2 text-lg font-semibold">Selected for your garden</h3>
      <div className="mb-3 text-sm text-foreground/70">{selectedPlants.length} selected</div>
      <div className="max-h-[420px] space-y-1.5 overflow-y-auto pr-2">
        {selectedPlants.length ? selectedPlants.map((item) => (
          <div key={item.selection_key} className="flex min-h-9 items-center justify-between gap-2 rounded-md border border-border bg-muted/30 py-1.5 pl-2.5 pr-1.5 text-sm">
            <div className="min-w-0 truncate font-medium">{displayPlantResultName(item)}</div>
            <Button
              className="h-7 w-7 shrink-0 bg-transparent p-0 text-foreground/60 hover:bg-muted hover:text-foreground"
              type="button"
              aria-label={`Remove ${displayPlantResultName(item)}`}
              onClick={() => onToggleSelection(item)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        )) : <div className="text-sm text-foreground/60">Nothing selected yet.</div>}
      </div>
    </Card>
  );
}

function PlantCard({ plant, selected, onToggle }: { plant: PlantSearchResult; selected: boolean; onToggle: (plant: PlantSearchResult) => void }) {
  return (
    <button
      type="button"
      aria-label={`${selected ? "Remove" : "Add"} ${displayPlantResultName(plant)}`}
      onClick={() => onToggle(plant)}
      className={`rounded-md border p-3 text-left text-sm transition-colors ${selected ? "border-emerald-500 bg-emerald-50" : "border-border bg-white hover:border-primary/50"}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-semibold">{displayPlantResultName(plant)}</div>
          <div className="mt-1 text-xs text-foreground/60">{plant.result_type === "cultivar" ? "Cultivar" : "Species"}</div>
        </div>
        <span className="rounded-full border border-border bg-muted/40 px-2 py-0.5 text-xs">{selected ? "Added ✓" : "Add"}</span>
      </div>
      <div className="mt-2 text-foreground/60">{plant.sunlight_requirement} · zone {plant.min_zone}-{plant.max_zone}</div>
      {plant.hardiness_warning ? <div className="mt-2 rounded border border-amber-200 bg-amber-50 p-2 text-xs text-amber-900">{plant.hardiness_warning}</div> : null}
    </button>
  );
}
