"use client";

import { FormEvent, useMemo, useState } from "react";
import { Leaf, MapPin, Save, Sprout } from "lucide-react";
import { ApiClient } from "@/lib/api";
import { GardenMap } from "@/components/GardenMap";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { GardenContextRead, GardenGoals, GardenRead, GardenRecommendationResult, GeneratedPlan, PlantRead, PlantSuggestion, PropertyRead } from "@/types/api";

type Step = "login" | "address" | "map" | "context" | "plants" | "plan";

export default function Home() {
  const [step, setStep] = useState<Step>("login");
  const [token, setToken] = useState<string | null>(() => (typeof window === "undefined" ? null : localStorage.getItem("jakegpt_token")));
  const [property, setProperty] = useState<PropertyRead | null>(null);
  const [garden, setGarden] = useState<GardenRead | null>(null);
  const [context, setContext] = useState<GardenContextRead | null>(null);
  const [plants, setPlants] = useState<PlantRead[]>([]);
  const [suggestions, setSuggestions] = useState<PlantSuggestion[]>([]);
  const [recommendations, setRecommendations] = useState<GardenRecommendationResult | null>(null);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [goals, setGoals] = useState<GardenGoals>({ goal: "Food", maintenance_preference: "Moderate", sunlight: "Full Sun", free_text_preferences: "" });
  const [plan, setPlan] = useState<GeneratedPlan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const api = useMemo(() => new ApiClient(token), [token]);

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
    try {
      const created = await api.request<PropertyRead>("/properties", {
        method: "POST",
        body: JSON.stringify({ address: form.get("address") })
      });
      setProperty(created);
      setStep("map");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Address lookup failed");
    }
  }

  async function saveGarden(polygon: GeoJSON.Polygon) {
    if (!property) return;
    setError(null);
    try {
      const created = await api.request<GardenRead>("/gardens", {
        method: "POST",
        body: JSON.stringify({ property_id: property.id, name: "Primary Garden", polygon_geojson: polygon })
      });
      setGarden(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Garden save failed");
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

  async function continueToPlants() {
    setError(null);
    try {
      const allPlants = await api.request<PlantRead[]>("/plants");
      setPlants(allPlants);
      setStep("plants");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Plant load failed");
    }
  }

  async function loadSuggestions() {
    if (!garden) return;
    const selectedSlugs = plants.filter((plant) => selectedIds.includes(plant.id)).map((plant) => plant.slug).filter(Boolean) as string[];
    const result = await api.request<GardenRecommendationResult>(`/gardens/${garden.id}/recommendations/generate`, {
      method: "POST",
      body: JSON.stringify({
        goals: recommendationGoals(goals),
        primary_goal: goalToApi(goals.goal),
        maintenance_preference: goals.maintenance_preference.toLowerCase(),
        experience_level: goals.experience_level ?? "beginner",
        selected_plant_slugs: selectedSlugs,
        selected_cultivar_slugs: [],
        excluded_plant_slugs: [],
        limit: 25,
        include_excluded: false,
        notes: goals.free_text_preferences ?? null
      })
    });
    setRecommendations(result);
    setSuggestions([]);
  }

  async function generatePlan() {
    if (!garden) return;
    setError(null);
    try {
      const generated = await api.request<GeneratedPlan>("/plans/generate", {
        method: "POST",
        body: JSON.stringify({ garden_id: garden.id, selected_plant_ids: selectedIds, goals })
      });
      setPlan(generated);
      setStep("plan");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Plan generation failed");
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
        {step === "address" ? <AddressForm onSubmit={handleAddress} /> : null}
        {step === "map" && property ? (
          <div className="grid gap-5 lg:grid-cols-[1fr_320px]">
            <GardenMap property={property} garden={garden} onPolygon={(polygon) => saveGarden(polygon)} />
            <Card>
              <h2 className="mb-2 text-lg font-semibold">Garden Area</h2>
              <p className="mb-4 text-sm text-foreground/70">Draw one polygon around the usable garden area. JakeGPT stores GeoJSON and the backend calculates authoritative PostGIS area.</p>
              {garden ? (
                <div className="space-y-2 text-sm">
                  <div>{garden.area_sq_ft.toFixed(0)} sq ft</div>
                  <div>{garden.area_sq_m.toFixed(1)} sq m</div>
                  <Button className="mt-4 w-full" onClick={() => setStep("context")}>Continue</Button>
                </div>
              ) : null}
            </Card>
          </div>
        ) : null}
        {step === "context" && garden ? <ContextForm garden={garden} context={context} goals={goals} setGoals={setGoals} onSave={saveContext} onRecalculate={recalculateContext} onSunlightChange={updateSunlight} onContinue={continueToPlants} /> : null}
        {step === "plants" ? (
          <PlantSelection plants={plants} suggestions={suggestions} recommendations={recommendations} selectedIds={selectedIds} setSelectedIds={setSelectedIds} goals={goals} setGoals={setGoals} loadSuggestions={loadSuggestions} generatePlan={generatePlan} />
        ) : null}
        {step === "plan" && property && garden && plan ? (
          <div className="grid gap-5 lg:grid-cols-[1fr_360px]">
            <GardenMap property={property} garden={garden} generatedPlan={plan} dimmed />
            <Card>
              <h2 className="mb-3 text-lg font-semibold">Generated Plan</h2>
              <p className="text-sm text-foreground/70">{plan.summary}</p>
              <div className="mt-4 space-y-2 text-sm">
                {plan.items.map((item) => <div key={`${item.plant_id}-${item.row}-${item.col}`}>{item.label}: {item.quantity} plantings</div>)}
              </div>
              <div className="mt-4 space-y-2 text-sm text-foreground/70">
                {plan.companion_notes.map((note) => <div key={note}>{note}</div>)}
              </div>
              <div className="mt-5 flex flex-wrap gap-2">
                <Button onClick={savePlan}><Save className="mr-2 h-4 w-4" />Save Plan</Button>
                <Button className="bg-accent text-foreground" onClick={generatePlan}>Regenerate</Button>
                <Button className="bg-muted text-foreground" onClick={() => setStep("plants")}>Back to Plant Selection</Button>
              </div>
            </Card>
          </div>
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

function AddressForm({ onSubmit }: { onSubmit: (event: FormEvent<HTMLFormElement>) => void }) {
  return (
    <Card className="mx-auto max-w-xl">
      <h1 className="mb-4 text-2xl font-semibold">Enter Property Address</h1>
      <form onSubmit={onSubmit} className="flex gap-2">
        <Input name="address" placeholder="123 Garden Lane, Detroit, MI" defaultValue="123 Garden Lane, Detroit, MI" />
        <Button><MapPin className="mr-2 h-4 w-4" />Find</Button>
      </form>
    </Card>
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
        <Button onClick={context ? onRecalculate : onSave}>{context ? "Recalculate Context" : "Calculate Context"}</Button>
        {context ? <Button className="bg-accent text-foreground" onClick={onContinue}>Continue to Plants</Button> : null}
      </div>
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
    Shade: "shade"
  };
  return values[value] ?? "unknown";
}

function apiToGoalSunlight(value: string) {
  const values: Record<string, string> = {
    full_sun: "Full Sun",
    part_sun: "Part Sun",
    part_shade: "Part Shade",
    shade: "Shade",
    unknown: "Part Sun"
  };
  return values[value] ?? "Part Sun";
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

function PlantSelection(props: {
  plants: PlantRead[];
  suggestions: PlantSuggestion[];
  recommendations: GardenRecommendationResult | null;
  selectedIds: number[];
  setSelectedIds: (ids: number[]) => void;
  goals: GardenGoals;
  setGoals: (goals: GardenGoals) => void;
  loadSuggestions: () => void;
  generatePlan: () => void;
}) {
  const toggle = (id: number) => props.setSelectedIds(props.selectedIds.includes(id) ? props.selectedIds.filter((item) => item !== id) : [...props.selectedIds, id]);
  return (
    <div className="grid gap-5 lg:grid-cols-[320px_1fr]">
      <Card>
        <h2 className="mb-3 text-lg font-semibold">Goals</h2>
        <label className="mb-3 block text-sm">Garden goal
          <select className="mt-1 h-10 w-full rounded-md border border-border px-3" value={props.goals.goal} onChange={(event) => props.setGoals({ ...props.goals, goal: event.target.value })}>
            {["Food", "Flowers", "Shade", "Pollinators", "Herbs", "Fruit", "Native plants", "Combination"].map((value) => <option key={value}>{value}</option>)}
          </select>
        </label>
        <label className="mb-3 block text-sm">Maintenance
          <select className="mt-1 h-10 w-full rounded-md border border-border px-3" value={props.goals.maintenance_preference} onChange={(event) => props.setGoals({ ...props.goals, maintenance_preference: event.target.value })}>
            {["Low", "Moderate", "High"].map((value) => <option key={value}>{value}</option>)}
          </select>
        </label>
        <label className="mb-3 block text-sm">Experience
          <select className="mt-1 h-10 w-full rounded-md border border-border px-3" value={props.goals.experience_level ?? "beginner"} onChange={(event) => props.setGoals({ ...props.goals, experience_level: event.target.value })}>
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>
        </label>
        <label className="mb-3 block text-sm">Preferences
          <textarea className="mt-1 min-h-24 w-full rounded-md border border-border p-3" value={props.goals.free_text_preferences ?? ""} onChange={(event) => props.setGoals({ ...props.goals, free_text_preferences: event.target.value })} />
        </label>
        <Button className="mb-2 w-full" onClick={props.loadSuggestions}><Sprout className="mr-2 h-4 w-4" />Generate Recommendations</Button>
        <Button className="w-full" disabled={props.selectedIds.length === 0} onClick={props.generatePlan}>Generate Plan</Button>
      </Card>
      <Card>
        <h2 className="mb-3 text-lg font-semibold">Plants</h2>
        {props.recommendations ? (
          <div className="mb-4 space-y-3">
            <div className="rounded-md border border-border bg-muted/40 p-3 text-sm">{props.recommendations.summary}</div>
            {props.recommendations.warnings.length ? (
              <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                {props.recommendations.warnings.map((warning) => <div key={`${warning.warning_type}-${warning.plant_slugs.join("-")}`}>{warning.message}</div>)}
              </div>
            ) : null}
            <div className="grid gap-3 lg:grid-cols-2">
              {props.recommendations.recommendations.slice(0, 8).map((item) => {
                const plant = props.plants.find((candidate) => candidate.slug === item.plant_slug);
                return (
                  <div key={item.plant_slug} className="rounded-md border border-border bg-white p-3 text-sm">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="font-semibold">{item.plant_common_name}</div>
                        <div className="text-xs text-foreground/60">{item.recommendation_type.replaceAll("_", " ")} · score {item.score.toFixed(1)}</div>
                      </div>
                      {plant ? (
                        <Button className="h-8 px-3 text-xs" onClick={() => props.setSelectedIds(props.selectedIds.includes(plant.id) ? props.selectedIds : [...props.selectedIds, plant.id])}>Add</Button>
                      ) : null}
                    </div>
                    <p className="mt-2 text-foreground/70">{item.explanation}</p>
                    {item.cultivar_recommendations.length ? (
                      <div className="mt-2 text-xs text-foreground/60">Cultivars: {item.cultivar_recommendations.map((cultivar) => cultivar.cultivar_name).join(", ")}</div>
                    ) : null}
                    {item.warnings.length ? (
                      <div className="mt-2 text-xs text-amber-700">{item.warnings.join(" ")}</div>
                    ) : null}
                  </div>
                );
              })}
            </div>
            {props.recommendations.assumptions.length ? (
              <div className="rounded-md border border-border bg-muted/40 p-3 text-xs text-foreground/70">
                {props.recommendations.assumptions.join(" ")}
              </div>
            ) : null}
          </div>
        ) : null}
        {props.suggestions.length ? (
          <div className="mb-4 rounded-md bg-muted p-3 text-sm">
            Suggested: {props.suggestions.map((item) => item.plant.common_name).join(", ")}
          </div>
        ) : null}
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {props.plants.map((plant) => (
            <button key={plant.id} onClick={() => toggle(plant.id)} className={`rounded-md border p-3 text-left text-sm ${props.selectedIds.includes(plant.id) ? "border-primary bg-primary/10" : "border-border bg-white"}`}>
              <div className="font-semibold"><Leaf className="mr-1 inline h-4 w-4" />{plant.common_name}</div>
              <div className="text-foreground/60">{plant.sunlight_requirement} · zone {plant.min_zone}-{plant.max_zone}</div>
            </button>
          ))}
        </div>
      </Card>
    </div>
  );
}

function StepIndicator({ step }: { step: Step }) {
  return <div className="hidden text-sm text-foreground/60 sm:block">{step}</div>;
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

function recommendationGoals(goals: GardenGoals) {
  const primary = goalToApi(goals.goal);
  return primary === "combination" ? ["food", "flowers", "pollinators", "combination"] : [primary];
}
