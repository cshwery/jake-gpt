DEFAULT_GRID_COLUMNS = 4
MIN_GRID_ROWS = 3
MAX_PLANT_QUANTITY = 12
DEFAULT_CELL_SIZE_FT = 2
DEFAULT_ACCESS_PATHS = ["between every grid row"]

POSITIVE_TYPES = {"beneficial", "guild", "pollinator_support", "pest_deterrent", "nutrient_support", "shade_support", "succession"}
NEGATIVE_TYPES = {"avoid", "disease_risk", "pest_risk", "allelopathy", "competition"}
STRONG_NEGATIVE_TYPES = {"avoid", "disease_risk", "pest_risk", "allelopathy"}

SCORE_WEIGHTS = {
    "spacing": 1.0,
    "companion": 1.0,
    "conflict": 1.3,
    "access": 0.8,
    "sunlight": 0.7,
    "size_fit": 1.0,
    "diversity": 0.5,
}

SPACING_DEFAULTS = {
    "leafy_greens": (9, 12),
    "herb": (12, 12),
    "flower": (10, 12),
    "nightshade": (24, 30),
    "cucurbit": (48, 60),
    "corn": (15, 30),
    "legume": (6, 18),
    "shrub": (36, 48),
    "tree": (120, 120),
    "default": (18, 18),
}
