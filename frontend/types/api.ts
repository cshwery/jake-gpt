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
      group_id?: string | null;
      group_label?: string | null;
      notes: string[];
    }>;
    layout_style?: string;
    layout_metadata?: Record<string, unknown>;
    access_paths: string[];
  };
  placements: Array<{
    plant_slug: string;
    plant_common_name: string;
    cultivar_slug?: string | null;
    cultivar_name?: string | null;
    quantity: number;
    grid_cells: string[];
    row?: number | null;
    col?: number | null;
    width?: number;
    height?: number;
    x_pct?: number | null;
    y_pct?: number | null;
    spacing_inches?: number | null;
    row_spacing_inches?: number | null;
    placement_role?: string | null;
    location_notes?: string | null;
    warnings: string[];
  }>;
  paths: Array<{ path_id: string; grid_cells: string[]; width_ft: number; notes?: string | null }>;
  score_breakdown: Record<string, number>;
  design_plan?: PlantingDesignPlan | null;
  layout_blueprint?: LayoutBlueprint | null;
  warnings: string[];
  explanations: string[];
  assumptions: string[];
};

export type PlantSymbol = {
  symbol: string;
  plant_slug: string;
  cultivar_slug?: string | null;
  display_name: string;
  role: string;
};

export type LayoutBlueprint = {
  layout_style: "raised_beds" | "rows" | "chaos" | "grid" | "mixed";
  summary: string;
  plant_symbols: PlantSymbol[];
  row_blueprint?: {
    rows: Array<{
      row_number: number;
      row_label: string;
      primary_plants: string[];
      companion_plants: string[];
      border_plants: string[];
      spacing_from_prior_row_inches?: number | null;
      in_row_spacing_inches?: number | null;
      row_role: string;
      notes: string[];
    }>;
    row_spacing_notes: string[];
    diagram_label_frequency: number;
    north_orientation: string;
    tree_shrub_symbols: string[];
  } | null;
  raised_bed_blueprint?: {
    beds: Array<{
      bed_id: string;
      bed_name: string;
      length_ft: number;
      width_ft: number;
      symbol_legend: PlantSymbol[];
      plantings: Array<DesignedPlanting>;
      border_plantings: Array<DesignedPlanting>;
      companion_clusters: string[];
      notes: string[];
      warnings: string[];
    }>;
    unplaced_plants: string[];
    tree_shrub_symbols: string[];
  } | null;
  chaos_blueprint?: {
    suggested_plant_count_range: string;
    easy_direct_sow_plants: string[];
    low_maintenance_plants: string[];
    pollinator_support_plants: string[];
    plants_to_isolate: string[];
    keep_apart_notes: string[];
    scatter_guidance: string[];
    warnings: string[];
  } | null;
  tree_shrub_section?: {
    items: Array<{
      symbol: string;
      plant_slug: string;
      cultivar_slug?: string | null;
      display_name: string;
      placement_guidance: string;
      warning?: string | null;
    }>;
  } | null;
  placement_rules: Array<{
    rule_type: string;
    plant_slugs: string[];
    rationale: string;
    priority: string;
  }>;
  warnings: string[];
  assumptions: string[];
};

export type DesignedPlanting = {
  plant_slug: string;
  cultivar_slug?: string | null;
  symbol: string;
  quantity: number;
  role: string;
  approximate_zone: string;
  near_plant_slugs: string[];
  keep_away_from_slugs: string[];
  rationale: string;
};

export type PlantingDesignPlan = {
  organization_style: string;
  summary: string;
  plant_roles: Array<{ plant_slug: string; cultivar_slug?: string | null; role: string; rationale: string }>;
  plant_groups: Array<{
    group_id: string;
    group_type: string;
    primary_plants: string[];
    support_plants: string[];
    placement_strategy: string;
    notes: string[];
  }>;
  companion_clusters: Array<{
    cluster_id: string;
    anchor_plant_slug: string;
    companion_plant_slugs: string[];
    border_plant_slugs: string[];
    filler_plant_slugs: string[];
    rationale: string;
    placement_guidance: string;
  }>;
  pollinator_border: string[];
  separation_rules: Array<{
    plant_slugs: string[];
    relationship_type: string;
    severity: string;
    placement_guidance: string;
    rationale: string;
  }>;
  placement_guidance: {
    rows_guidance: string[];
    raised_beds_guidance: string[];
    chaos_guidance: string[];
    north_south_guidance: string[];
    border_guidance: string[];
    spacing_guidance: string[];
  };
  warnings: string[];
  assumptions: string[];
};

export type GardenGoals = {
  goals?: string[];
  goal: string;
  maintenance_preference: string;
  experience_level?: string;
  sunlight: string;
  free_text_preferences?: string | null;
  planting_style?: "rows" | "intensive_grid" | "raised_beds" | "mixed" | "chaos";
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
  hardiness_compatible?: boolean | null;
  hardiness_warning?: string | null;
};
