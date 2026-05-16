export type PropertyRead = {
  id: number;
  address_raw: string;
  normalized_address: string;
  latitude: number;
  longitude: number;
};

export type GardenRead = {
  id: number;
  property_id: number;
  name: string;
  polygon_geojson: GeoJSON.Polygon;
  area_sq_m: number;
  area_sq_ft: number;
};

export type GardenContextRead = {
  id: number;
  garden_id: number;
  hardiness_zone: string;
  last_frost_date: string;
  precipitation_category: string;
  sunlight_estimate: string;
  notes?: string | null;
};

export type PlantRead = {
  id: number;
  common_name: string;
  scientific_name?: string | null;
  plant_type: string;
  edible: boolean;
  flower: boolean;
  tree: boolean;
  perennial: boolean;
  min_zone: number;
  max_zone: number;
  sunlight_requirement: string;
  water_requirement: string;
  spacing_inches: number;
  row_spacing_inches: number;
  days_to_maturity?: number | null;
  maintenance_level: string;
  planting_notes: string;
};

export type PlantSuggestion = {
  plant: PlantRead;
  score: number;
  reasons: string[];
};

export type GeneratedPlan = {
  id?: number | null;
  garden_id: number;
  summary: string;
  layout_grid: { rows: number; cols: number; access_paths?: string[] };
  items: Array<{
    id?: number | null;
    plant_id: number;
    label: string;
    row: number;
    col: number;
    width: number;
    height: number;
    quantity: number;
    x_pct: number;
    y_pct: number;
    notes?: string | null;
  }>;
  companion_notes: string[];
  goals: GardenGoals;
};

export type GardenGoals = {
  goal: string;
  maintenance_preference: string;
  sunlight: string;
  free_text_preferences?: string | null;
};
