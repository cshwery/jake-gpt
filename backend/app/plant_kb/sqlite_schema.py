SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE plants (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    common_name TEXT NOT NULL,
    scientific_name TEXT,
    plant_category TEXT NOT NULL,
    lifecycle TEXT NOT NULL,
    edible INTEGER NOT NULL,
    ornamental INTEGER NOT NULL,
    is_tree INTEGER NOT NULL,
    is_shrub INTEGER NOT NULL,
    is_native_option INTEGER NOT NULL,
    general_description TEXT,
    min_hardiness_zone INTEGER,
    max_hardiness_zone INTEGER,
    sunlight_requirement TEXT NOT NULL,
    water_requirement TEXT NOT NULL,
    soil_ph_min REAL,
    soil_ph_max REAL,
    typical_spacing_inches INTEGER,
    typical_row_spacing_inches INTEGER,
    typical_height_inches INTEGER,
    typical_spread_inches INTEGER,
    typical_days_to_maturity_min INTEGER,
    typical_days_to_maturity_max INTEGER,
    frost_tolerance TEXT NOT NULL,
    direct_sow_allowed INTEGER NOT NULL,
    transplant_recommended INTEGER NOT NULL,
    beginner_friendliness_score INTEGER,
    maintenance_level TEXT NOT NULL,
    pollinator_value_score INTEGER,
    wildlife_value_score INTEGER,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE plant_cultivars (
    id INTEGER PRIMARY KEY,
    plant_id INTEGER NOT NULL REFERENCES plants(id) ON DELETE CASCADE,
    slug TEXT NOT NULL UNIQUE,
    cultivar_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    description TEXT,
    days_to_maturity_min INTEGER,
    days_to_maturity_max INTEGER,
    min_hardiness_zone INTEGER,
    max_hardiness_zone INTEGER,
    sunlight_requirement_override TEXT,
    water_requirement_override TEXT,
    spacing_inches_override INTEGER,
    row_spacing_inches_override INTEGER,
    height_inches_min INTEGER,
    height_inches_max INTEGER,
    spread_inches_min INTEGER,
    spread_inches_max INTEGER,
    flavor_profile TEXT,
    common_uses TEXT,
    disease_resistance TEXT,
    heat_tolerance_score INTEGER,
    cold_tolerance_score INTEGER,
    drought_tolerance_score INTEGER,
    container_friendly INTEGER,
    compact_variety INTEGER,
    heirloom INTEGER,
    hybrid INTEGER,
    open_pollinated INTEGER,
    seed_saving_friendly INTEGER,
    recommended_regions TEXT,
    avoid_regions TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE plant_companion_relationships (
    id INTEGER PRIMARY KEY,
    source_plant_id INTEGER NOT NULL REFERENCES plants(id) ON DELETE CASCADE,
    target_plant_id INTEGER NOT NULL REFERENCES plants(id) ON DELETE CASCADE,
    source_cultivar_id INTEGER REFERENCES plant_cultivars(id) ON DELETE CASCADE,
    target_cultivar_id INTEGER REFERENCES plant_cultivars(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL,
    confidence TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    rationale TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_url TEXT,
    relationship_direction TEXT NOT NULL,
    min_distance_inches INTEGER,
    max_distance_inches INTEGER,
    source_notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE planting_rules (
    id INTEGER PRIMARY KEY,
    plant_id INTEGER NOT NULL REFERENCES plants(id) ON DELETE CASCADE,
    cultivar_id INTEGER REFERENCES plant_cultivars(id) ON DELETE CASCADE,
    rule_type TEXT NOT NULL,
    relative_to TEXT NOT NULL,
    offset_days_min INTEGER,
    offset_days_max INTEGER,
    min_soil_temp_f INTEGER,
    max_soil_temp_f INTEGER,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE plant_region_rules (
    id INTEGER PRIMARY KEY,
    plant_id INTEGER NOT NULL REFERENCES plants(id) ON DELETE CASCADE,
    cultivar_id INTEGER REFERENCES plant_cultivars(id) ON DELETE CASCADE,
    hardiness_zone TEXT,
    region_name TEXT,
    recommended_start_date TEXT,
    recommended_transplant_date TEXT,
    recommended_direct_sow_date TEXT,
    recommended_harvest_start TEXT,
    recommended_harvest_end TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE data_sources (
    id INTEGER PRIMARY KEY,
    source_name TEXT NOT NULL UNIQUE,
    source_url TEXT,
    source_type TEXT NOT NULL,
    license_notes TEXT,
    retrieved_at TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE seed_import_runs (
    id INTEGER PRIMARY KEY,
    run_started_at TEXT NOT NULL,
    run_completed_at TEXT,
    source_version TEXT,
    plant_count INTEGER NOT NULL DEFAULT 0,
    cultivar_count INTEGER NOT NULL DEFAULT 0,
    companion_relationship_count INTEGER NOT NULL DEFAULT 0,
    planting_rule_count INTEGER NOT NULL DEFAULT 0,
    region_rule_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    notes TEXT
);
"""
