export type PropertyRead = {
  id: number;
  address_raw: string;
  normalized_address: string;
  latitude: number;
  longitude: number;
  geocoder_provider?: string | null;
  geocoder_accuracy?: string | null;
  geocoder_confidence?: string | null;
  geocoder_bbox?: number[] | null;
};

export type GeocodeResult = {
  provider: string;
  query: string;
  normalized_address: string;
  latitude: number;
  longitude: number;
  accuracy?: string | null;
  confidence?: string | null;
  bbox?: number[] | null;
  place_name?: string | null;
  raw_result: Record<string, unknown>;
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
  garden_id: number;
  geometry: {
    centroid: { lat: number; lon: number };
    bbox: { min_lat: number; min_lon: number; max_lat: number; max_lon: number };
    area_sq_m: number;
    area_sq_ft: number;
  };
  hardiness: {
    zone?: string | null;
    source?: string | null;
    confidence?: string | null;
  };
  frost: {
    estimated_last_frost_date?: string | null;
    estimated_first_frost_date?: string | null;
    growing_season_days?: number | null;
    source?: string | null;
    confidence?: string | null;
  };
  precipitation: {
    expected_annual_precipitation_mm?: number | null;
    expected_growing_season_precipitation_mm?: number | null;
    category?: string | null;
    source?: string | null;
    confidence?: string | null;
  };
  sunlight: {
    category?: string | null;
    method?: string | null;
    confidence?: string | null;
    user_override?: string | null;
  };
  assumptions: string[];
  warnings: string[];
  raw_context: Record<string, unknown>;
};

export type PlantRead = {
  id: number;
  slug?: string | null;
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

export type GardenRecommendationResult = {
  garden_id: number;
  summary: string;
  selected: string[];
  recommendations: Array<{
    plant_slug: string;
    plant_common_name: string;
    cultivar_recommendations: Array<{
      cultivar_slug: string;
      cultivar_name: string;
      score: number;
      reason_codes: string[];
    }>;
    recommendation_type: string;
    score: number;
    score_breakdown: Record<string, number>;
    reason_codes: string[];
    warnings: string[];
    explanation: string;
  }>;
  warnings: Array<{
    warning_type: string;
    plant_slugs: string[];
    severity: string;
    message: string;
  }>;
  excluded: Array<{
    plant_slug: string;
    reason_codes: string[];
    message: string;
  }>;
  assumptions: string[];
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

export type RaisedBedsSetup = {
  number_of_beds?: number | null;
  bed_shape?: "rectangle" | "square" | "custom" | null;
  bed_length_ft?: number | null;
  bed_width_ft?: number | null;
  bed_area_sq_ft?: number | null;
  notes?: string | null;
};

export type LayoutResult = {
  layout_id?: number | null;
  garden_id?: number | null;
  garden_plan_id?: number | null;
  recommendation_run_id?: number | null;
  summary: string;
  area_sq_ft?: number | null;
  area_category?: string | null;
  approximate_dimensions_ft?: { width: number; height: number; grid_area_sq_ft?: number } | null;
  grid: {
    rows: number;
    cols: number;
    cell_size_ft: number;
    orientation: string;
    cells: Array<{
      cell_id: string;
      row: number;
      col: number;
      available: boolean;
      is_path: boolean;
      plant_slug?: string | null;
      cultivar_slug?: string | null;
      label?: string | null;
      placement_role?: string | null;
      notes: string[];
    }>;
    access_paths: string[];
  };
  placements: Array<{
    plant_slug: string;
    plant_common_name: string;
    cultivar_slug?: string | null;
    cultivar_name?: string | null;
    quantity: number;
    grid_cells: string[];
    spacing_inches?: number | null;
    row_spacing_inches?: number | null;
    placement_role?: string | null;
    location_notes?: string | null;
    warnings: string[];
  }>;
  paths: Array<{ path_id: string; grid_cells: string[]; width_ft: number; notes?: string | null }>;
  score_breakdown: Record<string, number>;
  warnings: string[];
  explanations: string[];
  assumptions: string[];
};

export type GardenGoals = {
  goals?: string[];
  goal: string;
  maintenance_preference: string;
  experience_level?: string;
  sunlight: string;
  free_text_preferences?: string | null;
  planting_style?: "rows" | "intensive_grid" | "raised_beds" | "mixed";
  using_raised_beds?: boolean | null;
  raised_beds?: RaisedBedsSetup | null;
  start_preference?: "germinate_myself" | "buy_from_nursery" | "no_preference" | null;
  can_start_seeds_indoors?: boolean | null;
  prefers_buying_starts?: boolean | null;
  direct_sow_preference?: "direct_sow_when_reasonable" | "prefer_transplants" | "no_preference" | null;
};

export type PlantSearchResult = PlantRead & {
  result_type: "species" | "cultivar";
  plant_id?: number | null;
  cultivar_id?: number | null;
  cultivar_slug?: string | null;
  cultivar_name?: string | null;
  display_name?: string | null;
  cultivar_notes?: string | null;
};
