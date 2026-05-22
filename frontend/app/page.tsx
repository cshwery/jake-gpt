"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { MapPin, Save, Sprout } from "lucide-react";
import { ApiClient } from "@/lib/api";
import { GardenMap } from "@/components/GardenMap";
import { GardenLayoutGrid } from "@/components/GardenLayoutGrid";
import { PlantSelectionPanel } from "@/components/PlantSelectionPanel";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { GardenContextRead, GardenGoals, GardenRead, GardenRecommendationResult, GeneratedPlan, GeocodeResult, LayoutResult, PlantSearchResult, PropertyRead } from "@/types/api";
import { areaCategory, areaWarning, displayCultivarName, displayPlantName, fitLabel, layoutQualityLabel, recommendationLabel, recommendationReasonLabel } from "@/lib/product";
import { dedupePlantResults, selectionKeyForPlantResult, uniqueNumbers, uniqueStrings } from "@/lib/plantSelection";
import { applyGardenOrganization, layoutStyleFromGoals, organizationModeFromGoals } from "@/lib/gardenOrganization";

type Step = "login" | "address" | "map" | "context" | "setup" | "plants" | "layout" | "plan";

type SelectedPlantItem = PlantSearchResult & { selection_key: string };

export default function Home() {
  const [step, setStep] = useState<Step>("login");
  const [token, setToken] = useState<string | null>(() => (typeof window === "undefined" ? null : localStorage.getItem("jakegpt_token")));
  const [property, setProperty] = useState<PropertyRead | null>(null);
  const [geocode, setGeocode] = useState<GeocodeResult | null>(null);
  const [addressQuery, setAddressQuery] = useState<string>("");
  const [garden, setGarden] = useState<GardenRead | null>(null);
  const [draftPolygon, setDraftPolygon] = useState<GeoJSON.Polygon | null>(null);
  const [draftAreaSqM, setDraftAreaSqM] = useState<number | null>(null);
  const [context, setContext] = useState<GardenContextRead | null>(null);
  const [plantQuery, setPlantQuery] = useState<string>("");
  const [plantResults, setPlantResults] = useState<PlantSearchResult[]>([]);
  const [recommendations, setRecommendations] = useState<GardenRecommendationResult | null>(null);
  const [selectedPlants, setSelectedPlants] = useState<SelectedPlantItem[]>([]);
  const [loadingRecommendations, setLoadingRecommendations] = useState(false);
  const [showIncompatiblePlants, setShowIncompatiblePlants] = useState(false);
  const [savingGarden, setSavingGarden] = useState(false);
  const [goals, setGoals] = useState<GardenGoals>({
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
  });
  const [layout, setLayout] = useState<LayoutResult | null>(null);
  const [plan, setPlan] = useState<GeneratedPlan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const api = useMemo(() => new ApiClient(token), [token]);
  const selectedPlantIds = useMemo(
    () => uniqueNumbers(selectedPlants.map((item) => item.plant_id).filter((value): value is number => typeof value === "number")),
    [selectedPlants]
  );
  const selectedPlantSlugs = useMemo(
    () => uniqueStrings(selectedPlants.map((item) => item.slug).filter(Boolean) as string[]),
    [selectedPlants]
  );
  const selectedCultivarSlugs = useMemo(() => uniqueStrings(selectedPlants.map((item) => item.cultivar_slug).filter(Boolean) as string[]), [selectedPlants]);

  useEffect(() => {
    if (step !== "plants") return;
    let active = true;
    const timer = window.setTimeout(async () => {
      try {
        const query = plantQuery.trim();
        const params = new URLSearchParams();
        if (query) params.set("q", query);
        if (garden?.id) params.set("garden_id", String(garden.id));
        if (showIncompatiblePlants) params.set("include_incompatible", "true");
        const result = await api.request<PlantSearchResult[]>(`/plants${params.toString() ? `?${params.toString()}` : ""}`);
        if (active) setPlantResults(dedupePlantResults(result));
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Plant load failed");
        }
      }
    }, 250);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [api, plantQuery, step, garden?.id, showIncompatiblePlants]);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const form = new FormData(event.currentTarget);
    try {
      const result = await api.request<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: form.get("email"), password: form.get("password") })
      });
      localStorage.setItem("jakegpt_token", result.access_token);
      setToken(result.access_token);
      setStep("address");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  }

  async function handleAddress(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const form = new FormData(event.currentTarget);
    const address = String(form.get("address") ?? "");
    try {
      const result = await api.request<GeocodeResult>("/properties/geocode", {
        method: "POST",
        body: JSON.stringify({ address })
      });
      setAddressQuery(address);
      setGeocode(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Address lookup failed");
    }
  }

  async function confirmProperty() {
    if (!geocode) return;
    setError(null);
    try {
      const created = await api.request<PropertyRead>("/properties", {
        method: "POST",
        body: JSON.stringify({ address: addressQuery || geocode.query })
      });
      setProperty(created);
      setGarden(null);
      setDraftPolygon(null);
      setDraftAreaSqM(null);
      setStep("map");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Property save failed");
    }
  }

  async function saveGardenBoundary(continueAfterSave = false) {
    const polygon = draftPolygon ?? garden?.polygon_geojson ?? null;
    if (!property || !polygon) return;
    setError(null);
    setSavingGarden(true);
    try {
      const created = await api.request<GardenRead>("/gardens", {
        method: "POST",
        body: JSON.stringify({ property_id: property.id, name: "Primary Garden", polygon_geojson: polygon })
      });
      setGarden(created);
      setDraftAreaSqM(created.area_sq_m);
      if (continueAfterSave) setStep("context");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Garden save failed");
    } finally {
      setSavingGarden(false);
    }
  }

  async function saveContext() {
    if (!garden) return;
    setError(null);
    try {
      const created = await api.request<GardenContextRead>(`/gardens/${garden.id}/context/generate`, {
        method: "POST",
        body: JSON.stringify({ user_sunlight_override: sunlightToApi(goals.sunlight) })
      });
      setContext(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Context save failed");
    }
  }

  async function recalculateContext() {
    if (!garden) return;
    setError(null);
    try {
      const updated = await api.request<GardenContextRead>(`/gardens/${garden.id}/context/recalculate`, {
        method: "POST",
        body: JSON.stringify({ user_sunlight_override: sunlightToApi(goals.sunlight) })
      });
      setContext(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Context recalculation failed");
    }
  }

  async function updateSunlight(value: string) {
    if (!garden) return;
    setGoals({ ...goals, sunlight: apiToGoalSunlight(value) });
    setError(null);
    try {
      const updated = await api.request<GardenContextRead>(`/gardens/${garden.id}/context/sunlight`, {
        method: "PATCH",
        body: JSON.stringify({ user_sunlight_override: value })
      });
      setContext(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sunlight update failed");
    }
  }

  async function continueToSetup() {
    setStep("setup");
  }

  async function continueToPlants() {
    setError(null);
    try {
      const params = new URLSearchParams();
      if (garden?.id) params.set("garden_id", String(garden.id));
      if (showIncompatiblePlants) params.set("include_incompatible", "true");
      const allPlants = await api.request<PlantSearchResult[]>(`/plants${params.toString() ? `?${params.toString()}` : ""}`);
      setPlantResults(dedupePlantResults(allPlants));
      setPlantQuery("");
      setStep("plants");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Plant load failed");
    }
  }

  async function loadSuggestions() {
    if (!garden) {
      setError("Save a garden before generating recommendations.");
      return;
    }
    if (!context) {
      setError("Generate garden context before recommendations.");
      return;
    }
    if (selectedPlants.length === 0) {
      setError("Select at least one plant before generating recommendations.");
      return;
    }
    setLoadingRecommendations(true);
    setError(null);
    setRecommendations(null);
    try {
      const result = await api.request<GardenRecommendationResult>(`/gardens/${garden.id}/recommendations/generate`, {
        method: "POST",
        body: JSON.stringify({
          goals: recommendationGoals(goals),
          primary_goal: goalToApi(goals.goal),
          maintenance_preference: goals.maintenance_preference.toLowerCase(),
          experience_level: experienceToApi(goals.experience_level),
          selected_plant_slugs: selectedPlantSlugs,
          selected_cultivar_slugs: selectedCultivarSlugs,
          excluded_plant_slugs: [],
          limit: 25,
          include_excluded: false,
          notes: goals.free_text_preferences ?? null,
          planting_style: goals.planting_style ?? "rows",
          using_raised_beds: goals.using_raised_beds,
          raised_beds: goals.raised_beds,
          start_preference: goals.start_preference ?? "no_preference",
          can_start_seeds_indoors: goals.can_start_seeds_indoors,
          prefers_buying_starts: goals.prefers_buying_starts,
          direct_sow_preference: goals.direct_sow_preference
        })
      });
      setRecommendations(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Recommendation generation failed");
    } finally {
      setLoadingRecommendations(false);
    }
  }

  async function generatePlan() {
    if (!garden) return;
    setError(null);
    try {
      if (!layout) {
        await generateLayout("plan", false);
      }
      const generated = await api.request<GeneratedPlan>("/plans/generate", {
        method: "POST",
        body: JSON.stringify({ garden_id: garden.id, selected_plant_ids: selectedPlantIds, goals })
      });
      setPlan(generated);
      setStep("plan");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Plan generation failed");
    }
  }

  async function generateLayout(nextStep: Step = "layout", persistSelection = true) {
    if (!garden) return;
    setError(null);
    try {
      const generated = await api.request<LayoutResult>(`/gardens/${garden.id}/layouts/generate`, {
        method: "POST",
        body: JSON.stringify({
          selected_plant_slugs: selectedPlantSlugs,
          selected_cultivar_slugs: selectedCultivarSlugs,
          accepted_recommendation_slugs: selectedPlantSlugs,
          accepted_cultivar_slugs: selectedCultivarSlugs,
          options: {
            cell_size_ft: goals.using_raised_beds ? 1 : goals.planting_style === "rows" || goals.planting_style === "chaos" ? 1 : 2,
            include_paths: goals.using_raised_beds ? false : !["rows", "chaos"].includes(goals.planting_style ?? "rows"),
            layout_style: layoutStyleFromGoals(goals),
            max_candidates: 10,
            persist: true,
            using_raised_beds: goals.using_raised_beds,
            raised_beds: goals.raised_beds
          }
        })
      });
      setLayout(generated);
      setPlan(null);
      if (persistSelection) setStep(nextStep);
      return generated;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Layout generation failed");
      throw err;
    }
  }

  async function savePlan() {
    if (!plan) return;
    const saved = await api.request<GeneratedPlan>("/plans", {
      method: "POST",
      body: JSON.stringify({ generated_plan: plan })
    });
    setPlan(saved);
  }

  function toggleSelection(item: PlantSearchResult) {
    setSelectedPlants((current) => {
      const key = selectionKeyForPlantResult(item);
      const existing = current.find((entry) => entry.selection_key === key);
      if (existing) {
        return current.filter((entry) => entry.selection_key !== key);
      }
      return [...current, { ...item, selection_key: key }];
    });
  }

  return (
    <main className="min-h-screen">
      <header className="border-b border-border bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
          <div>
            <div className="text-xl font-semibold">Jakerton&apos;s Garden Planning Tool</div>
            <div className="text-sm text-foreground/60">JakeGPT</div>
          </div>
          <StepIndicator step={step} />
        </div>
      </header>
      <section className="mx-auto max-w-6xl px-5 py-6">
        {error ? <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
        {step === "login" ? <LoginForm onSubmit={handleLogin} /> : null}
        {step === "address" ? <AddressForm onSubmit={handleAddress} geocode={geocode} onConfirm={confirmProperty} /> : null}
        {step === "map" && property ? (
          <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
            <GardenMap
              property={property}
              garden={garden}
              onPolygon={(polygon, areaSqM) => {
                setDraftPolygon(polygon);
                setDraftAreaSqM(areaSqM);
              }}
              onClearPolygon={() => {
                setDraftPolygon(null);
                setDraftAreaSqM(null);
              }}
              canSaveBoundary={Boolean(draftPolygon ?? garden?.polygon_geojson)}
            />
            <Card className="self-start">
              <h2 className="mb-3 text-lg font-semibold">Draw Map</h2>
              <DrawMapStepPanel hasPolygon={Boolean(draftPolygon ?? garden?.polygon_geojson)} hasSavedGarden={Boolean(garden)} />
              <div className="mb-4 rounded-md border border-border bg-muted/40 p-3 text-sm">
                <div className="text-xs font-medium uppercase text-foreground/50">Confirmed property</div>
                <div>{property.normalized_address}</div>
              </div>
              <AreaPanel areaSqM={draftAreaSqM ?? garden?.area_sq_m ?? null} />
              {garden ? <div className="mt-4 rounded-md border border-primary/20 bg-primary/10 p-3 text-sm">Saved area: {garden.area_sq_ft.toFixed(0)} sq ft</div> : null}
              <Button className="mt-4 w-full" disabled={savingGarden || !Boolean(draftPolygon ?? garden?.polygon_geojson)} onClick={() => saveGardenBoundary(true)}>
                {savingGarden ? "Saving..." : "Save and Continue"}
              </Button>
            </Card>
          </div>
        ) : null}
        {step === "context" && garden ? <ContextForm garden={garden} context={context} goals={goals} setGoals={setGoals} onSave={saveContext} onRecalculate={recalculateContext} onSunlightChange={updateSunlight} onContinue={continueToSetup} /> : null}
        {step === "setup" ? <GoalsSetupForm goals={goals} setGoals={setGoals} onContinue={continueToPlants} /> : null}
        {step === "plants" ? (
          <PlantSelectionPanel
            plantResults={plantResults}
            plantQuery={plantQuery}
            setPlantQuery={setPlantQuery}
            selectedPlants={selectedPlants}
            onToggleSelection={toggleSelection}
            recommendations={recommendations}
            goals={goals}
            onGenerateRecommendations={loadSuggestions}
            onGenerateLayout={() => generateLayout("layout")}
            loadingRecommendations={loadingRecommendations}
            showIncompatiblePlants={showIncompatiblePlants}
            setShowIncompatiblePlants={setShowIncompatiblePlants}
          />
        ) : null}
        {step === "layout" && property && garden && layout ? (
          <LayoutScreen layout={layout} onRegenerate={() => generateLayout("layout")} onContinue={generatePlan} onBack={() => setStep("plants")} />
        ) : null}
        {step === "plan" && property && garden && plan && layout ? (
          <PlanScreen layout={layout} plan={plan} onRegenerate={generatePlan} onContinue={() => setStep("plants")} onBack={() => setStep("layout")} onSave={savePlan} />
        ) : null}
      </section>
    </main>
  );
}

function LoginForm({ onSubmit }: { onSubmit: (event: FormEvent<HTMLFormElement>) => void }) {
  return (
    <Card className="mx-auto max-w-md">
      <h1 className="mb-4 text-2xl font-semibold">JakeGPT Login</h1>
      <form onSubmit={onSubmit} className="space-y-3">
        <Input name="email" type="email" defaultValue="demo@jakegpt.ai" />
        <Input name="password" type="password" defaultValue="JakePass" />
        <Button className="w-full">Login</Button>
      </form>
    </Card>
  );
}

function AddressForm({ onSubmit, geocode, onConfirm }: { onSubmit: (event: FormEvent<HTMLFormElement>) => void; geocode: GeocodeResult | null; onConfirm: () => void }) {
  return (
    <Card className="mx-auto max-w-xl">
      <h1 className="mb-4 text-2xl font-semibold">Enter Property Address</h1>
      <form onSubmit={onSubmit} className="flex gap-2">
        <Input name="address" placeholder="123 Garden Lane, Detroit, MI" defaultValue="123 Garden Lane, Detroit, MI" />
        <Button><MapPin className="mr-2 h-4 w-4" />Find</Button>
      </form>
      {geocode ? (
        <div className="mt-4 rounded-md border border-border bg-muted/40 p-4 text-sm">
          <div className="text-xs font-medium uppercase text-foreground/50">Best result</div>
          <div className="mt-1 font-semibold">{geocode.normalized_address}</div>
          <div className="mt-1 text-foreground/60">{geocode.provider} · {geocode.latitude.toFixed(5)}, {geocode.longitude.toFixed(5)}</div>
          <Button className="mt-4" onClick={onConfirm}>Confirm this property</Button>
        </div>
      ) : null}
    </Card>
  );
}

function AreaPanel({ areaSqM }: { areaSqM: number | null }) {
  const areaSqFt = areaSqM == null ? null : areaSqM * 10.7639;
  const warning = areaSqFt == null ? null : areaWarning(areaSqFt);
  const confirmedAreaSqM = areaSqM ?? 0;
  return (
    <div className="rounded-md border border-border bg-muted/30 p-3 text-sm">
      <div className="text-xs font-medium uppercase text-foreground/50">Garden area</div>
      {areaSqFt == null ? (
        <div className="mt-1 text-foreground/60">Draw a boundary to calculate area.</div>
      ) : (
        <>
          <div className="mt-1 text-lg font-semibold">{areaSqFt.toFixed(0)} sq ft</div>
          <div>{confirmedAreaSqM.toFixed(1)} sq m · {areaCategory(areaSqFt)}</div>
          {warning ? <div className="mt-2 rounded border border-amber-200 bg-amber-50 p-2 text-amber-900">{warning}</div> : null}
        </>
      )}
    </div>
  );
}

function DrawMapStepPanel({ hasPolygon, hasSavedGarden }: { hasPolygon: boolean; hasSavedGarden: boolean }) {
  const steps = [
    { label: "Confirm property", active: false, complete: true, detail: "Use the satellite map to make sure the pin is centered on the right yard." },
    { label: "Draw planting area", active: !hasPolygon, complete: hasPolygon, detail: "Draw only the space where plants will go. Skip patios, lawn, paths, and buildings." },
    { label: "Save and continue", active: hasPolygon, complete: hasSavedGarden, detail: hasPolygon ? "Save the boundary and move to Garden Context." : "This unlocks after a garden boundary exists." }
  ];
  return (
    <div className="mb-4 space-y-2">
      {steps.map((item, index) => (
        <div key={item.label} className={`rounded-md border p-3 text-sm ${item.active ? "border-primary bg-primary/10" : item.complete ? "border-emerald-200 bg-emerald-50" : "border-border bg-muted/30"}`}>
          <div className="flex items-center justify-between gap-3">
            <div className="font-semibold">Step {index + 1}: {item.label}</div>
            <div className="text-xs text-foreground/60">{item.complete ? "Done" : item.active ? "Current" : "Next"}</div>
          </div>
          {item.active ? <div className="mt-1 text-foreground/70">{item.detail}</div> : null}
        </div>
      ))}
      <div className="rounded-md border border-border bg-muted/30 p-3 text-xs text-foreground/70">Tip: most backyard beds are 25-500 sq ft. Zoom in before drawing corners.</div>
    </div>
  );
}

function ContextForm({
  garden,
  context,
  goals,
  setGoals,
  onSave,
  onRecalculate,
  onSunlightChange,
  onContinue
}: {
  garden: GardenRead;
  context: GardenContextRead | null;
  goals: GardenGoals;
  setGoals: (goals: GardenGoals) => void;
  onSave: () => void;
  onRecalculate: () => void;
  onSunlightChange: (value: string) => void;
  onContinue: () => void;
}) {
  const sunlightValue = context?.sunlight.user_override ?? context?.sunlight.category ?? sunlightToApi(goals.sunlight);
  return (
    <Card className="mx-auto max-w-3xl">
      <h1 className="mb-4 text-2xl font-semibold">Garden Context</h1>
      <div className="mb-4 grid gap-3 text-sm sm:grid-cols-2">
        <ContextMetric label="Garden Area" value={`${(context?.geometry.area_sq_ft ?? garden.area_sq_ft).toFixed(0)} sq ft`} detail={`${(context?.geometry.area_sq_m ?? garden.area_sq_m).toFixed(1)} sq m`} />
        {context ? (
          <>
            <ContextMetric label="Planting Zone" value={context.hardiness.zone ?? "Unknown"} detail={`${context.hardiness.source ?? "unknown"} · ${context.hardiness.confidence ?? "unknown"} confidence`} />
            <ContextMetric label="Last Frost" value={context.frost.estimated_last_frost_date ? formatDate(context.frost.estimated_last_frost_date) : "Unknown"} detail={`${context.frost.source ?? "unknown"} · estimated`} />
            <ContextMetric label="First Frost" value={context.frost.estimated_first_frost_date ? formatDate(context.frost.estimated_first_frost_date) : "Unknown"} detail={`${context.frost.growing_season_days ?? "Unknown"} growing-season days`} />
            <ContextMetric label="Annual Precipitation" value={precipitationLabel(context.precipitation.category)} detail={`${formatMm(context.precipitation.expected_annual_precipitation_mm)} annual · ${formatMm(context.precipitation.expected_growing_season_precipitation_mm)} growing season`} />
            <ContextMetric label="Sunlight" value={sunlightLabel(context.sunlight.category)} detail={`${context.sunlight.method ?? "unknown"} · ${context.sunlight.confidence ?? "unknown"} confidence`} />
          </>
        ) : null}
        <label className="sm:col-span-2">How sunny is this garden area during the growing season?
          <select className="mt-1 h-10 w-full rounded-md border border-border px-3" value={sunlightValue} onChange={(event) => context ? onSunlightChange(event.target.value) : setGoals({ ...goals, sunlight: apiToGoalSunlight(event.target.value) })}>
            <option value="full_sun">Full sun: 6+ hours</option>
            <option value="part_sun">Part sun: 4-6 hours</option>
            <option value="part_shade">Part shade: 2-4 hours</option>
            <option value="shade">Shade: less than 2 hours</option>
            <option value="unknown">I am not sure</option>
          </select>
        </label>
      </div>
      {context?.assumptions.length ? (
        <ContextList title="Assumptions" items={context.assumptions} />
      ) : null}
      {context?.warnings.length ? (
        <ContextList title="Warnings" items={context.warnings} tone="warning" />
      ) : null}
      <div className="flex flex-wrap gap-2">
        {!context ? <Button onClick={onSave}>Calculate Context</Button> : null}
        {context ? <Button onClick={onContinue}>Continue to Goals & Setup</Button> : null}
      </div>
      {context ? (
        <details className="mt-4 rounded-md border border-border bg-muted/30 p-3 text-sm">
          <summary className="cursor-pointer font-semibold">Advanced estimates</summary>
          <p className="mt-2 text-foreground/70">Use this if you changed the garden boundary or sunlight estimate.</p>
          <Button className="mt-3 bg-muted text-foreground" onClick={onRecalculate}>Refresh estimates</Button>
        </details>
      ) : null}
    </Card>
  );
}

function ContextMetric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-md border border-border bg-muted/40 p-3">
      <div className="text-xs font-medium uppercase text-foreground/55">{label}</div>
      <div className="mt-1 text-lg font-semibold">{value}</div>
      <div className="text-xs text-foreground/60">{detail}</div>
    </div>
  );
}

function precipitationLabel(category?: string | null) {
  if (!category) return "Unknown";
  const labels: Record<string, string> = {
    low: "Low",
    medium: "Medium",
    high: "High"
  };
  return labels[category] ?? category;
}

function formatMm(value?: number | null) {
  return typeof value === "number" ? `${value.toFixed(0)} mm` : "unknown";
}

function sunlightToApi(value: string) {
  const values: Record<string, string> = {
    "Full Sun": "full_sun",
    "Part Sun": "part_sun",
    "Part Shade": "part_shade",
    Shade: "shade",
    "I am not sure": "unknown"
  };
  return values[value] ?? "unknown";
}

function apiToGoalSunlight(value: string) {
  const values: Record<string, string> = {
    full_sun: "Full Sun",
    part_sun: "Part Sun",
    part_shade: "Part Shade",
    shade: "Shade",
    unknown: "I am not sure"
  };
  return values[value] ?? "I am not sure";
}

function sunlightLabel(value?: string | null) {
  const values: Record<string, string> = {
    full_sun: "Full sun",
    part_sun: "Part sun",
    part_shade: "Part shade",
    shade: "Shade",
    unknown: "Unknown"
  };
  return values[value ?? "unknown"] ?? "Unknown";
}

function ContextList({ title, items, tone = "default" }: { title: string; items: string[]; tone?: "default" | "warning" }) {
  return (
    <div className={`mb-4 rounded-md border p-3 text-sm ${tone === "warning" ? "border-amber-200 bg-amber-50 text-amber-900" : "border-border bg-muted/40"}`}>
      <div className="mb-2 font-semibold">{title}</div>
      <ul className="list-inside list-disc space-y-1">
        {items.map((item) => <li key={item}>{item}</li>)}
      </ul>
    </div>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-US", { month: "long", day: "numeric" }).format(new Date(`${value}T12:00:00`));
}

function GoalsSetupForm({
  goals,
  setGoals,
  onContinue
}: {
  goals: GardenGoals;
  setGoals: (goals: GardenGoals) => void;
  onContinue: () => void;
}) {
  const organizationMode = organizationModeFromGoals(goals);
  const usingRaisedBeds = organizationMode === "raised_beds";
  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <Card>
        <h2 className="mb-2 text-lg font-semibold">Goals & Setup</h2>
        <p className="mb-4 text-sm text-foreground/70">Tell JakeGPT how you want to use the garden before you choose plants.</p>
        <div className="grid gap-4 md:grid-cols-2">
          <LabelSelect label="What is your main goal?" value={goals.goal} onChange={(value) => setGoals({ ...goals, goal: value, goals: recommendationGoals({ ...goals, goal: value }) })} options={["Food", "Flowers", "Shade", "Pollinators", "Herbs", "Fruit", "Native plants", "Combination"]} />
          <LabelSelect label="Maintenance preference" value={goals.maintenance_preference} onChange={(value) => setGoals({ ...goals, maintenance_preference: value })} options={["Low", "Moderate", "High"]} />
          <LabelSelect label="Experience" value={goals.experience_level ?? "beginner"} onChange={(value) => setGoals({ ...goals, experience_level: value })} options={["Beginner", "Intermediate", "Advanced"]} />
          <LabelSelect
            label="How do you like to organize your garden?"
            value={organizationMode}
            onChange={(value) => setGoals(applyGardenOrganization(goals, value as "raised_beds" | "rows" | "chaos"))}
            options={["raised_beds", "rows", "chaos"]}
            displayOptions={["Raised Beds", "Rows", "Chaos"]}
          />
          <LabelSelect
            label="How do you prefer to get plant starts?"
            value={goals.start_preference ?? "no_preference"}
            onChange={(value) => setGoals(syncStartPreference(goals, value as GardenGoals["start_preference"]))}
            options={["germinate_myself", "buy_from_nursery", "no_preference"]}
            displayOptions={["Germinate myself indoors or in a greenhouse", "Buy starts from a nursery", "No preference"]}
          />
          <LabelSelect
            label="Direct sow preference"
            value={goals.direct_sow_preference ?? "no_preference"}
            onChange={(value) => setGoals({ ...goals, direct_sow_preference: value as GardenGoals["direct_sow_preference"] })}
            options={["direct_sow_when_reasonable", "prefer_transplants", "no_preference"]}
            displayOptions={["Direct sow when reasonable", "Prefer transplants", "No preference"]}
          />
        </div>
        {organizationMode === "chaos" ? (
          <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
            Chaos mode gives you a loose planting strategy instead of a precise map. JakeGPT will recommend hardy, lower-maintenance plants and flag combinations that should not be clustered together.
          </div>
        ) : null}
        <label className="mt-4 block text-sm">
          Preferences
          <textarea
            className="mt-1 min-h-28 w-full rounded-md border border-border p-3 text-sm"
            placeholder="I want to have some food each week rather than one big harvest"
            value={goals.free_text_preferences ?? ""}
            onChange={(event) => setGoals({ ...goals, free_text_preferences: event.target.value })}
          />
        </label>
      </Card>

      {usingRaisedBeds ? (
        <Card>
          <h3 className="mb-2 text-base font-semibold">Raised bed setup</h3>
          <p className="mb-4 text-sm text-foreground/70">Future versions will let you drag raised-bed shapes onto the map. For now, JakeGPT will use these dimensions to guide layout.</p>
          <div className="grid gap-4 md:grid-cols-2">
            <NumberField label="Number of beds" value={goals.raised_beds?.number_of_beds ?? null} onChange={(value) => setGoals({ ...goals, raised_beds: { ...(goals.raised_beds ?? {}), number_of_beds: value } })} />
            <LabelSelect
              label="Bed shape"
              value={(goals.raised_beds?.bed_shape ?? "rectangle") as string}
              onChange={(value) => setGoals({ ...goals, raised_beds: { ...(goals.raised_beds ?? {}), bed_shape: value as "rectangle" | "square" | "custom" } })}
              options={["rectangle", "square", "custom"]}
            />
            <NumberField label="Bed length (ft)" value={goals.raised_beds?.bed_length_ft ?? null} onChange={(value) => setGoals({ ...goals, raised_beds: { ...(goals.raised_beds ?? {}), bed_length_ft: value } })} />
            <NumberField label="Bed width (ft)" value={goals.raised_beds?.bed_width_ft ?? null} onChange={(value) => setGoals({ ...goals, raised_beds: { ...(goals.raised_beds ?? {}), bed_width_ft: value } })} />
            <NumberField label="Bed area (sq ft)" value={goals.raised_beds?.bed_area_sq_ft ?? null} onChange={(value) => setGoals({ ...goals, raised_beds: { ...(goals.raised_beds ?? {}), bed_area_sq_ft: value } })} />
            <label className="block text-sm">
              Notes
              <textarea
                className="mt-1 min-h-20 w-full rounded-md border border-border p-3 text-sm"
                placeholder="Any notes about the beds"
                value={goals.raised_beds?.notes ?? ""}
                onChange={(event) => setGoals({ ...goals, raised_beds: { ...(goals.raised_beds ?? {}), notes: event.target.value } })}
              />
            </label>
          </div>
        </Card>
      ) : null}

      <div className="flex justify-end">
        <Button onClick={onContinue}>Continue to Plant Selection</Button>
      </div>
    </div>
  );
}

function PlantSelection(props: {
  plantResults: PlantSearchResult[];
  plantQuery: string;
  setPlantQuery: (query: string) => void;
  selectedPlants: SelectedPlantItem[];
  onToggleSelection: (plant: PlantSearchResult) => void;
  recommendations: GardenRecommendationResult | null;
  goals: GardenGoals;
  loadSuggestions: () => void;
  generateLayout: () => Promise<LayoutResult | void>;
}) {
  const selectedKeys = new Set(props.selectedPlants.map((item) => item.selection_key));
  const species = props.plantResults.filter((item) => item.result_type === "species");
  const cultivars = props.plantResults.filter((item) => item.result_type === "cultivar");
  const recommendationCards = props.recommendations?.recommendations.slice(0, 8) ?? [];
  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
      <div className="space-y-5">
        <Card>
          <h2 className="mb-2 text-lg font-semibold">Search plants</h2>
          <p className="mb-4 text-sm text-foreground/70">Search species and cultivars. Cultivar names appear under their parent species.</p>
          <div className="flex gap-2">
            <Input value={props.plantQuery} onChange={(event) => props.setPlantQuery(event.target.value)} placeholder="Search tomato, basil, Sungold..." />
            <Button className="shrink-0" onClick={props.loadSuggestions}><Sprout className="mr-2 h-4 w-4" />Generate Recommendations</Button>
          </div>
        </Card>

        {props.recommendations ? (
          <Card>
            <h3 className="mb-3 text-lg font-semibold">Recommendations</h3>
            <p className="mb-4 text-sm text-foreground/70">{props.recommendations.summary}</p>
            {props.recommendations.warnings.length ? (
              <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                {props.recommendations.warnings.map((warning) => (
                  <div key={`${warning.warning_type}-${warning.plant_slugs.join("-")}`}>{warning.message}</div>
                ))}
              </div>
            ) : null}
            <div className="grid gap-3 lg:grid-cols-2">
              {recommendationCards.map((item) => {
                const selectionKey = recommendationSelectionKey(item.plant_slug, item.cultivar_recommendations[0]?.cultivar_slug ?? null);
                const selected = selectedKeys.has(selectionKey);
                const targetPlant = recommendationTarget(item, props.plantResults);
                return (
                  <div key={`${item.plant_slug}-${item.cultivar_recommendations[0]?.cultivar_slug ?? "species"}`} className="rounded-md border border-border bg-white p-3 text-sm">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="font-semibold">{displayRecommendationName(item.plant_common_name, item.cultivar_recommendations[0]?.cultivar_name)}</div>
                        <div className="mt-1 flex flex-wrap gap-2 text-xs text-foreground/60">
                          <span className="rounded-full border border-border bg-muted/40 px-2 py-0.5">{recommendationLabel(item.recommendation_type)}</span>
                          <span className="rounded-full border border-border bg-muted/40 px-2 py-0.5">{fitLabel(item.score)}</span>
                        </div>
                      </div>
                      <Button
                        className={selected ? "h-8 bg-emerald-600 px-3 text-xs text-white" : "h-8 px-3 text-xs"}
                        onClick={() => targetPlant ? props.onToggleSelection(targetPlant) : undefined}
                      >
                        {selected ? "Added ✓" : "Add"}
                      </Button>
                    </div>
                    <div className="mt-2 space-y-1 text-foreground/70">
                      <div>{item.explanation}</div>
                      <ul className="list-inside list-disc text-xs">
                        {recommendationReasons(item.reason_codes, item.explanation).map((reason) => <li key={reason}>{reason}</li>)}
                      </ul>
                    </div>
                    {item.warnings.length ? <div className="mt-2 rounded border border-amber-200 bg-amber-50 p-2 text-xs text-amber-900">{item.warnings.join(" ")}</div> : null}
                  </div>
                );
              })}
            </div>
          </Card>
        ) : null}

        <Card>
          <h3 className="mb-3 text-lg font-semibold">Species</h3>
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {species.map((plant) => (
              <PlantCard key={selectionKeyForResult(plant)} plant={plant} selected={selectedKeys.has(selectionKeyForResult(plant))} onToggle={props.onToggleSelection} />
            ))}
          </div>
        </Card>

        {cultivars.length ? (
          <Card>
            <h3 className="mb-3 text-lg font-semibold">Cultivars</h3>
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
              {cultivars.map((plant) => (
                <PlantCard key={selectionKeyForResult(plant)} plant={plant} selected={selectedKeys.has(selectionKeyForResult(plant))} onToggle={props.onToggleSelection} />
              ))}
            </div>
          </Card>
        ) : null}
      </div>

      <div className="space-y-4">
        <SelectedPlantsTray selectedPlants={props.selectedPlants} onToggleSelection={props.onToggleSelection} />
        <Card>
          <h3 className="mb-3 text-lg font-semibold">Next steps</h3>
          <div className="space-y-2 text-sm text-foreground/70">
            <div>Selected plants: {props.selectedPlants.length}</div>
            <div>Goal: {props.goals.goal}</div>
            <div>Planting style: {props.goals.planting_style ?? "rows"}</div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button className="w-full" disabled={props.selectedPlants.length === 0} onClick={props.generateLayout}>Generate Layout</Button>
          </div>
        </Card>
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
    <Card className="sticky top-4">
      <h3 className="mb-2 text-lg font-semibold">Selected for your garden</h3>
      <div className="mb-4 text-sm text-foreground/70">Selected plants: {selectedPlants.length}</div>
      <div className="space-y-2">
        {selectedPlants.length ? selectedPlants.map((item) => (
          <div key={item.selection_key} className="flex items-center justify-between gap-2 rounded-md border border-border bg-muted/30 px-3 py-2 text-sm">
            <div>
              <div className="font-medium">{displayResultLabel(item)}</div>
              <div className="text-xs text-foreground/60">{item.result_type === "cultivar" ? "Cultivar" : "Species"}</div>
            </div>
            <Button className="h-8 px-3 text-xs bg-muted text-foreground" onClick={() => onToggleSelection(item)}>Remove</Button>
          </div>
        )) : <div className="text-sm text-foreground/60">Nothing selected yet.</div>}
      </div>
    </Card>
  );
}

function PlantCard({ plant, selected, onToggle }: { plant: PlantSearchResult; selected: boolean; onToggle: (plant: PlantSearchResult) => void }) {
  return (
    <button
      onClick={() => onToggle(plant)}
      className={`rounded-md border p-3 text-left text-sm transition-colors ${selected ? "border-emerald-500 bg-emerald-50" : "border-border bg-white hover:border-primary/50"}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-semibold">{displayResultLabel(plant)}</div>
          <div className="mt-1 text-xs text-foreground/60">{plant.result_type === "cultivar" ? "Cultivar" : "Species"}</div>
        </div>
        <span className="rounded-full border border-border bg-muted/40 px-2 py-0.5 text-xs">{selected ? "Added ✓" : "Add"}</span>
      </div>
      <div className="mt-2 text-foreground/60">{plant.sunlight_requirement} · zone {plant.min_zone}-{plant.max_zone}</div>
    </button>
  );
}

function LayoutScreen({
  layout,
  onRegenerate,
  onContinue,
  onBack
}: {
  layout: LayoutResult;
  onRegenerate: () => void;
  onContinue: () => void;
  onBack: () => void;
}) {
  return (
    <div className="space-y-5">
      <Card className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Layout</h2>
          <p className="mt-1 text-sm text-foreground/70">{layout.summary}</p>
          <div className="mt-2 text-sm font-semibold">{layoutQualityLabel(layout.score_breakdown?.total_score)}</div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={onContinue}>Continue to Plan</Button>
          <Button className="bg-accent text-foreground" onClick={onRegenerate}>Regenerate Layout</Button>
          <Button className="bg-muted text-foreground" onClick={onBack}>Back to Recommendations</Button>
        </div>
      </Card>
      <GardenLayoutGrid layout={layout} title="Layout" />
    </div>
  );
}

function PlanScreen({
  layout,
  plan,
  onRegenerate,
  onContinue,
  onBack,
  onSave
}: {
  layout: LayoutResult;
  plan: GeneratedPlan;
  onRegenerate: () => void;
  onContinue: () => void;
  onBack: () => void;
  onSave: () => void;
}) {
  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
      <div className="space-y-5">
        <GardenLayoutGrid layout={layout} title="Plan" />
      </div>
      <Card>
        <h2 className="mb-3 text-lg font-semibold">Generated Plan</h2>
        <p className="text-sm text-foreground/70">{plan.summary}</p>
        <div className="mt-4 space-y-2 text-sm">
          {plan.items.map((item) => (
            <div key={`${item.plant_id}-${item.row}-${item.col}`}>{item.label}: {item.quantity} plantings</div>
          ))}
        </div>
        <div className="mt-4 space-y-2 text-sm text-foreground/70">
          {plan.companion_notes.map((note) => <div key={note}>{note}</div>)}
        </div>
        <div className="mt-5 flex flex-wrap gap-2">
          <Button onClick={onSave}><Save className="mr-2 h-4 w-4" />Save Plan</Button>
          <Button className="bg-accent text-foreground" onClick={onRegenerate}>Regenerate</Button>
          <Button className="bg-muted text-foreground" onClick={onBack}>Back to Layout</Button>
          <Button className="bg-muted text-foreground" onClick={onContinue}>Back to Plant Selection</Button>
        </div>
      </Card>
    </div>
  );
}

function LabelSelect({
  label,
  value,
  onChange,
  options,
  displayOptions
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
  displayOptions?: string[];
}) {
  return (
    <label className="block text-sm">
      {label}
      <select className="mt-1 h-10 w-full rounded-md border border-border px-3" value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option, index) => <option key={option} value={option}>{displayOptions?.[index] ?? option}</option>)}
      </select>
    </label>
  );
}

function NumberField({ label, value, onChange }: { label: string; value: number | null; onChange: (value: number | null) => void }) {
  return (
    <label className="block text-sm">
      {label}
      <Input
        type="number"
        className="mt-1"
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value === "" ? null : Number(event.target.value))}
      />
    </label>
  );
}

function SelectedKeyPreview({ item }: { item: SelectedPlantItem }) {
  return <span>{displayResultLabel(item)}</span>;
}

function displayResultLabel(item: SelectedPlantItem | PlantSearchResult) {
  return item.result_type === "cultivar"
    ? displayCultivarName(item.common_name, item.cultivar_name ?? "")
    : displayPlantName(item.common_name);
}

function displayRecommendationName(commonName: string, cultivarName?: string | null) {
  return cultivarName ? displayCultivarName(commonName, cultivarName) : displayPlantName(commonName);
}

function recommendationTarget(item: GardenRecommendationResult["recommendations"][number], results: PlantSearchResult[]) {
  const cultivarSlug = item.cultivar_recommendations[0]?.cultivar_slug;
  if (cultivarSlug) {
    return results.find((result) => result.result_type === "cultivar" && result.cultivar_slug === cultivarSlug) ?? results.find((result) => result.result_type === "species" && result.slug === item.plant_slug) ?? null;
  }
  return results.find((result) => result.result_type === "species" && result.slug === item.plant_slug) ?? null;
}

function recommendationSelectionKey(plantSlug: string, cultivarSlug: string | null) {
  return cultivarSlug ? `cultivar:${cultivarSlug}` : `species:${plantSlug}`;
}

function selectionKeyForResult(item: PlantSearchResult) {
  return item.result_type === "cultivar"
    ? recommendationSelectionKey(item.slug ?? "", item.cultivar_slug ?? null)
    : recommendationSelectionKey(item.slug ?? "", null);
}

function recommendationReasons(reasonCodes: string[], explanation: string) {
  const reasons = reasonCodes.slice(0, 3).map((code) => recommendationReasonLabel(code)).filter(Boolean);
  return reasons.length ? reasons : [explanation];
}

function MessageList({ title, items, className = "border-border bg-muted/40 text-foreground/70" }: { title: string; items: string[]; className?: string }) {
  if (!items.length) return null;
  return (
    <div className={`mt-4 rounded-md border p-3 text-xs ${className}`}>
      <div className="mb-1 font-semibold text-foreground">{title}</div>
      {items.map((item) => <div key={item}>{item}</div>)}
    </div>
  );
}

function StepIndicator({ step }: { step: Step }) {
  const labels: Record<Step, string> = {
    login: "Login",
    address: "Address",
    map: "Draw Map",
    context: "Garden Context",
    setup: "Goals & Setup",
    plants: "Plants",
    layout: "Layout",
    plan: "Plan"
  };
  return <div className="hidden text-sm text-foreground/60 sm:block">{labels[step]}</div>;
}

function goalToApi(goal: string) {
  const values: Record<string, string> = {
    Food: "food",
    Flowers: "flowers",
    Shade: "shade",
    Pollinators: "pollinators",
    Herbs: "herbs",
    Fruit: "fruit",
    "Native plants": "native_plants",
    Combination: "combination"
  };
  return values[goal] ?? "combination";
}

function experienceToApi(value?: string | null) {
  const normalized = (value ?? "beginner").toLowerCase();
  if (normalized === "intermediate" || normalized === "advanced") return normalized;
  return "beginner";
}

function recommendationGoals(goals: GardenGoals) {
  const primary = goalToApi(goals.goal);
  return primary === "combination" ? ["food", "flowers", "pollinators", "combination"] : [primary];
}

function syncStartPreference(goals: GardenGoals, startPreference: GardenGoals["start_preference"]) {
  const next = startPreference ?? "no_preference";
  const legacy =
    next === "germinate_myself"
      ? { can_start_seeds_indoors: true, prefers_buying_starts: false, direct_sow_preference: "no_preference" as const }
      : next === "buy_from_nursery"
        ? { can_start_seeds_indoors: false, prefers_buying_starts: true, direct_sow_preference: "prefer_transplants" as const }
        : { can_start_seeds_indoors: null, prefers_buying_starts: null, direct_sow_preference: "no_preference" as const };
  return { ...goals, start_preference: next, ...legacy };
}
