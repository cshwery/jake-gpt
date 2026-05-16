from __future__ import annotations

SOURCE_VERSION = "2026-05-09.1"
NOW = "2026-05-09T00:00:00"


def slugify(value: str) -> str:
    return (
        value.lower()
        .replace("&", "and")
        .replace("'", "")
        .replace("-", " ")
        .replace("/", " ")
        .replace("(", " ")
        .replace(")", " ")
        .replace(".", " ")
        .strip()
        .replace(" ", "_")
    )


PLANT_CATEGORIES = {
    "vegetable",
    "fruit",
    "herb",
    "flower",
    "tree",
    "shrub",
    "cover_crop",
    "native",
    "ornamental",
}

VEGETABLES = [
    ("tomato", "Tomato", "Solanum lycopersicum", 3, 10, "full_sun", "medium", 24, 36, 60, 90, "frost_tender", True, True, 8, "moderate"),
    ("pepper", "Pepper", "Capsicum annuum", 4, 11, "full_sun", "medium", 18, 24, 65, 95, "frost_tender", False, True, 6, "moderate"),
    ("lettuce", "Lettuce", "Lactuca sativa", 2, 9, "part_sun", "medium", 8, 12, 30, 60, "light_frost_tolerant", True, False, 9, "low"),
    ("cucumber", "Cucumber", "Cucumis sativus", 4, 11, "full_sun", "high", 18, 48, 50, 70, "frost_tender", True, False, 7, "moderate"),
    ("summer_squash", "Summer Squash", "Cucurbita pepo", 3, 10, "full_sun", "high", 36, 48, 45, 65, "frost_tender", True, False, 7, "moderate"),
    ("winter_squash", "Winter Squash", "Cucurbita maxima", 3, 10, "full_sun", "high", 48, 72, 80, 110, "frost_tender", True, False, 6, "moderate"),
    ("bean", "Bean", "Phaseolus vulgaris", 3, 10, "full_sun", "medium", 6, 24, 50, 70, "frost_tender", True, False, 8, "low"),
    ("pea", "Pea", "Pisum sativum", 2, 9, "part_sun", "medium", 4, 18, 55, 75, "light_frost_tolerant", True, False, 8, "low"),
    ("carrot", "Carrot", "Daucus carota", 3, 10, "full_sun", "medium", 3, 12, 60, 80, "light_frost_tolerant", True, False, 8, "low"),
    ("onion", "Onion", "Allium cepa", 3, 9, "full_sun", "low", 4, 12, 90, 120, "light_frost_tolerant", True, True, 7, "low"),
    ("garlic", "Garlic", "Allium sativum", 3, 8, "full_sun", "low", 6, 12, 210, 270, "frost_hardy", True, False, 8, "low"),
    ("potato", "Potato", "Solanum tuberosum", 3, 10, "full_sun", "medium", 12, 36, 80, 120, "light_frost_tolerant", True, False, 7, "moderate"),
    ("sweet_potato", "Sweet Potato", "Ipomoea batatas", 8, 11, "full_sun", "medium", 12, 36, 90, 120, "frost_tender", False, True, 6, "moderate"),
    ("corn", "Corn", "Zea mays", 3, 10, "full_sun", "high", 12, 30, 70, 95, "frost_tender", True, False, 6, "moderate"),
    ("spinach", "Spinach", "Spinacia oleracea", 2, 9, "part_sun", "medium", 6, 12, 35, 50, "frost_hardy", True, False, 8, "low"),
    ("kale", "Kale", "Brassica oleracea var. sabellica", 2, 9, "full_sun", "medium", 18, 24, 50, 70, "frost_hardy", True, True, 8, "low"),
    ("cabbage", "Cabbage", "Brassica oleracea var. capitata", 2, 9, "full_sun", "medium", 18, 30, 65, 100, "frost_hardy", False, True, 6, "moderate"),
    ("broccoli", "Broccoli", "Brassica oleracea var. italica", 3, 10, "full_sun", "medium", 18, 30, 60, 90, "light_frost_tolerant", False, True, 6, "moderate"),
    ("cauliflower", "Cauliflower", "Brassica oleracea var. botrytis", 3, 10, "full_sun", "medium", 18, 30, 65, 95, "light_frost_tolerant", False, True, 5, "high"),
    ("brussels_sprouts", "Brussels Sprouts", "Brassica oleracea var. gemmifera", 3, 9, "full_sun", "medium", 24, 30, 90, 120, "frost_hardy", False, True, 5, "moderate"),
    ("radish", "Radish", "Raphanus sativus", 2, 10, "full_sun", "medium", 2, 8, 22, 35, "light_frost_tolerant", True, False, 9, "low"),
    ("beet", "Beet", "Beta vulgaris", 2, 10, "full_sun", "medium", 4, 12, 50, 70, "light_frost_tolerant", True, False, 8, "low"),
    ("turnip", "Turnip", "Brassica rapa subsp. rapa", 2, 9, "full_sun", "medium", 4, 12, 40, 60, "frost_hardy", True, False, 8, "low"),
    ("rutabaga", "Rutabaga", "Brassica napus", 3, 9, "full_sun", "medium", 8, 18, 80, 100, "frost_hardy", True, False, 6, "low"),
    ("parsnip", "Parsnip", "Pastinaca sativa", 2, 9, "full_sun", "medium", 4, 18, 100, 130, "frost_hardy", True, False, 6, "low"),
    ("celery", "Celery", "Apium graveolens", 3, 10, "full_sun", "high", 8, 24, 100, 130, "light_frost_tolerant", False, True, 5, "high"),
    ("okra", "Okra", "Abelmoschus esculentus", 5, 11, "full_sun", "medium", 18, 36, 55, 70, "frost_tender", True, False, 7, "moderate"),
    ("eggplant", "Eggplant", "Solanum melongena", 5, 11, "full_sun", "medium", 24, 36, 70, 90, "frost_tender", False, True, 6, "moderate"),
    ("asparagus", "Asparagus", "Asparagus officinalis", 3, 8, "full_sun", "medium", 18, 48, 730, 1095, "frost_hardy", False, True, 5, "moderate"),
    ("rhubarb", "Rhubarb", "Rheum rhabarbarum", 3, 8, "full_sun", "medium", 36, 48, 365, 730, "frost_hardy", False, True, 6, "low"),
]

HERBS = [
    ("basil", "Basil", "Ocimum basilicum", 4, 11, "full_sun", "medium", 12, 18, 55, 75, "frost_tender", True, 9, "low"),
    ("parsley", "Parsley", "Petroselinum crispum", 3, 9, "part_sun", "medium", 8, 12, 70, 90, "light_frost_tolerant", True, 8, "low"),
    ("cilantro", "Cilantro", "Coriandrum sativum", 2, 10, "part_sun", "medium", 6, 12, 35, 55, "light_frost_tolerant", True, 7, "low"),
    ("dill", "Dill", "Anethum graveolens", 2, 11, "full_sun", "low", 12, 18, 40, 60, "light_frost_tolerant", True, 8, "low"),
    ("fennel", "Fennel", "Foeniculum vulgare", 4, 9, "full_sun", "low", 18, 24, 80, 100, "light_frost_tolerant", True, 5, "moderate"),
    ("mint", "Mint", "Mentha spp.", 3, 9, "part_shade", "medium", 18, 24, 60, 80, "frost_hardy", True, 7, "low"),
    ("thyme", "Thyme", "Thymus vulgaris", 5, 9, "full_sun", "low", 12, 18, 90, 120, "frost_hardy", True, 8, "low"),
    ("oregano", "Oregano", "Origanum vulgare", 4, 9, "full_sun", "low", 12, 18, 80, 100, "frost_hardy", True, 8, "low"),
    ("rosemary", "Rosemary", "Salvia rosmarinus", 7, 10, "full_sun", "low", 24, 36, 120, 180, "frost_tender", True, 6, "low"),
    ("sage", "Sage", "Salvia officinalis", 5, 9, "full_sun", "low", 18, 24, 90, 120, "frost_hardy", True, 8, "low"),
    ("chives", "Chives", "Allium schoenoprasum", 3, 9, "full_sun", "medium", 8, 12, 60, 90, "frost_hardy", True, 8, "low"),
    ("lavender", "Lavender", "Lavandula spp.", 5, 9, "full_sun", "low", 18, 24, 90, 140, "frost_hardy", False, 7, "low"),
]

FRUITS = [
    ("apple", "Apple", "Malus domestica", "tree", 4, 8, "full_sun", "medium", 180, 240, 1000, 1800, True, 6, "high"),
    ("pear", "Pear", "Pyrus communis", "tree", 4, 8, "full_sun", "medium", 180, 240, 1000, 1800, True, 6, "moderate"),
    ("peach", "Peach", "Prunus persica", "tree", 5, 9, "full_sun", "medium", 180, 240, 730, 1460, True, 5, "high"),
    ("plum", "Plum", "Prunus domestica", "tree", 4, 9, "full_sun", "medium", 180, 240, 730, 1460, True, 6, "moderate"),
    ("cherry", "Cherry", "Prunus avium", "tree", 4, 8, "full_sun", "medium", 180, 240, 1000, 1800, True, 5, "high"),
    ("fig", "Fig", "Ficus carica", "tree", 7, 10, "full_sun", "low", 120, 180, 365, 730, True, 6, "moderate"),
    ("blueberry", "Blueberry", "Vaccinium corymbosum", "shrub", 4, 8, "full_sun", "medium", 48, 60, 365, 730, True, 6, "moderate"),
    ("strawberry", "Strawberry", "Fragaria x ananassa", "fruit", 4, 9, "full_sun", "medium", 12, 24, 90, 150, False, 8, "moderate"),
    ("raspberry", "Raspberry", "Rubus idaeus", "shrub", 3, 9, "full_sun", "medium", 24, 72, 365, 730, True, 6, "moderate"),
    ("blackberry", "Blackberry", "Rubus allegheniensis", "shrub", 5, 9, "full_sun", "medium", 36, 72, 365, 730, True, 6, "moderate"),
    ("grape", "Grape", "Vitis spp.", "fruit", 4, 10, "full_sun", "low", 72, 96, 730, 1095, True, 6, "moderate"),
    ("currant", "Currant", "Ribes spp.", "shrub", 3, 8, "part_sun", "medium", 36, 48, 365, 730, True, 6, "moderate"),
]

FLOWERS_NATIVE_COVER = [
    ("sunflower", "Sunflower", "Helianthus annuus", "flower", 2, 11, "full_sun", "low", 18, 30, 70, 100, False, True, 9, 8, "low"),
    ("marigold", "Marigold", "Tagetes spp.", "flower", 2, 11, "full_sun", "low", 10, 12, 45, 60, False, True, 7, 4, "low"),
    ("zinnia", "Zinnia", "Zinnia elegans", "flower", 2, 11, "full_sun", "medium", 12, 18, 60, 75, False, True, 8, 5, "low"),
    ("nasturtium", "Nasturtium", "Tropaeolum majus", "flower", 2, 11, "part_sun", "medium", 12, 18, 45, 65, False, True, 7, 4, "low"),
    ("calendula", "Calendula", "Calendula officinalis", "flower", 2, 11, "full_sun", "medium", 12, 18, 45, 60, False, True, 8, 5, "low"),
    ("cosmos", "Cosmos", "Cosmos bipinnatus", "flower", 2, 11, "full_sun", "low", 18, 24, 70, 90, False, True, 8, 5, "low"),
    ("coneflower", "Coneflower", "Echinacea purpurea", "native", 3, 9, "full_sun", "low", 18, 24, 365, 730, True, True, 9, 8, "low"),
    ("black_eyed_susan", "Black-Eyed Susan", "Rudbeckia hirta", "native", 3, 9, "full_sun", "low", 18, 24, 90, 120, True, True, 9, 8, "low"),
    ("milkweed", "Milkweed", "Asclepias spp.", "native", 3, 9, "full_sun", "low", 18, 24, 365, 730, True, True, 10, 10, "low"),
    ("bee_balm", "Bee Balm", "Monarda fistulosa", "native", 3, 9, "full_sun", "medium", 18, 24, 365, 730, True, True, 9, 8, "moderate"),
    ("yarrow", "Yarrow", "Achillea millefolium", "native", 3, 9, "full_sun", "low", 18, 24, 90, 120, True, True, 8, 7, "low"),
    ("clover", "Clover", "Trifolium spp.", "cover_crop", 3, 10, "full_sun", "medium", 4, 6, 60, 90, False, True, 8, 6, "low"),
    ("buckwheat", "Buckwheat", "Fagopyrum esculentum", "cover_crop", 2, 11, "full_sun", "medium", 6, 8, 30, 45, False, True, 8, 5, "low"),
    ("winter_rye", "Winter Rye", "Secale cereale", "cover_crop", 3, 8, "full_sun", "medium", 2, 7, 240, 300, False, False, 6, 4, "low"),
    ("hairy_vetch", "Hairy Vetch", "Vicia villosa", "cover_crop", 4, 9, "full_sun", "medium", 4, 12, 120, 180, False, True, 7, 5, "low"),
    ("crimson_clover", "Crimson Clover", "Trifolium incarnatum", "cover_crop", 6, 10, "full_sun", "medium", 4, 8, 90, 120, False, True, 7, 5, "low"),
]

EXTRA_PLANTS = [
    ("arugula", "Arugula", "Eruca vesicaria", "vegetable", 2, 10, "part_sun", "medium", 4, 12, 25, 45),
    ("bok_choy", "Bok Choy", "Brassica rapa subsp. chinensis", "vegetable", 2, 9, "part_sun", "medium", 8, 18, 45, 60),
    ("collards", "Collards", "Brassica oleracea var. viridis", "vegetable", 2, 10, "full_sun", "medium", 18, 30, 60, 85),
    ("mustard_greens", "Mustard Greens", "Brassica juncea", "vegetable", 2, 10, "part_sun", "medium", 6, 18, 35, 55),
    ("swiss_chard", "Swiss Chard", "Beta vulgaris var. cicla", "vegetable", 3, 10, "full_sun", "medium", 12, 18, 50, 65),
    ("leek", "Leek", "Allium porrum", "vegetable", 3, 9, "full_sun", "medium", 6, 18, 100, 130),
    ("shallot", "Shallot", "Allium cepa var. aggregatum", "vegetable", 3, 9, "full_sun", "low", 6, 12, 90, 120),
    ("scallion", "Scallion", "Allium fistulosum", "vegetable", 3, 10, "full_sun", "medium", 2, 8, 55, 75),
    ("watermelon", "Watermelon", "Citrullus lanatus", "fruit", 4, 11, "full_sun", "high", 72, 96, 75, 100),
    ("cantaloupe", "Cantaloupe", "Cucumis melo", "fruit", 4, 11, "full_sun", "medium", 48, 72, 75, 95),
    ("pumpkin", "Pumpkin", "Cucurbita pepo", "vegetable", 3, 10, "full_sun", "high", 72, 96, 90, 120),
    ("artichoke", "Artichoke", "Cynara cardunculus", "vegetable", 7, 10, "full_sun", "medium", 48, 60, 120, 180),
    ("endive", "Endive", "Cichorium endivia", "vegetable", 3, 9, "part_sun", "medium", 8, 18, 45, 75),
    ("radicchio", "Radicchio", "Cichorium intybus", "vegetable", 4, 9, "part_sun", "medium", 8, 18, 60, 90),
    ("tomatillo", "Tomatillo", "Physalis philadelphica", "vegetable", 4, 11, "full_sun", "medium", 24, 36, 65, 85),
    ("ground_cherry", "Ground Cherry", "Physalis pruinosa", "fruit", 4, 11, "full_sun", "medium", 24, 36, 65, 85),
    ("cranberry", "Cranberry", "Vaccinium macrocarpon", "fruit", 2, 7, "full_sun", "high", 12, 24, 365, 730),
    ("elderberry", "Elderberry", "Sambucus canadensis", "shrub", 3, 9, "full_sun", "medium", 72, 96, 365, 730),
    ("gooseberry", "Gooseberry", "Ribes uva-crispa", "shrub", 3, 8, "part_sun", "medium", 36, 48, 365, 730),
    ("serviceberry", "Serviceberry", "Amelanchier alnifolia", "native", 3, 8, "full_sun", "medium", 120, 180, 730, 1095),
    ("persimmon", "Persimmon", "Diospyros virginiana", "tree", 4, 9, "full_sun", "medium", 180, 240, 1095, 1825),
    ("pawpaw", "Pawpaw", "Asimina triloba", "native", 5, 9, "part_shade", "medium", 120, 180, 1095, 1825),
    ("hazelnut", "Hazelnut", "Corylus americana", "shrub", 4, 8, "full_sun", "medium", 96, 144, 1095, 1825),
    ("pecan", "Pecan", "Carya illinoinensis", "tree", 6, 9, "full_sun", "medium", 360, 480, 1825, 2920),
    ("chestnut", "Chestnut", "Castanea spp.", "tree", 5, 8, "full_sun", "medium", 300, 420, 1460, 2190),
    ("apricot", "Apricot", "Prunus armeniaca", "tree", 5, 8, "full_sun", "medium", 180, 240, 730, 1460),
    ("nectarine", "Nectarine", "Prunus persica var. nucipersica", "tree", 5, 9, "full_sun", "medium", 180, 240, 730, 1460),
    ("mulberry", "Mulberry", "Morus spp.", "tree", 5, 9, "full_sun", "medium", 240, 360, 730, 1460),
    ("lemon", "Lemon", "Citrus limon", "tree", 9, 11, "full_sun", "medium", 120, 180, 365, 1095),
    ("lime", "Lime", "Citrus aurantiifolia", "tree", 9, 11, "full_sun", "medium", 120, 180, 365, 1095),
    ("orange", "Orange", "Citrus sinensis", "tree", 9, 11, "full_sun", "medium", 180, 240, 730, 1460),
    ("tarragon", "Tarragon", "Artemisia dracunculus", "herb", 4, 9, "full_sun", "low", 18, 24, 90, 120),
    ("marjoram", "Marjoram", "Origanum majorana", "herb", 6, 10, "full_sun", "low", 12, 18, 70, 90),
    ("lemon_balm", "Lemon Balm", "Melissa officinalis", "herb", 4, 9, "part_sun", "medium", 18, 24, 70, 90),
    ("catnip", "Catnip", "Nepeta cataria", "herb", 3, 9, "full_sun", "low", 18, 24, 80, 100),
    ("borage", "Borage", "Borago officinalis", "herb", 2, 11, "full_sun", "medium", 18, 24, 50, 70),
    ("chamomile", "Chamomile", "Matricaria chamomilla", "herb", 3, 9, "full_sun", "low", 8, 12, 60, 90),
    ("echinacea", "Echinacea", "Echinacea spp.", "native", 3, 9, "full_sun", "low", 18, 24, 365, 730),
    ("coreopsis", "Coreopsis", "Coreopsis spp.", "native", 4, 9, "full_sun", "low", 18, 24, 90, 120),
    ("phlox", "Phlox", "Phlox paniculata", "ornamental", 4, 8, "full_sun", "medium", 18, 24, 365, 730),
    ("salvia", "Salvia", "Salvia spp.", "flower", 4, 10, "full_sun", "low", 18, 24, 90, 140),
    ("snapdragon", "Snapdragon", "Antirrhinum majus", "flower", 5, 10, "full_sun", "medium", 8, 12, 90, 120),
    ("petunia", "Petunia", "Petunia x atkinsiana", "flower", 9, 11, "full_sun", "medium", 12, 18, 70, 90),
    ("geranium", "Geranium", "Pelargonium spp.", "ornamental", 9, 11, "full_sun", "medium", 12, 18, 90, 120),
]

CULTIVARS = {
    "tomato": ["Roma", "Brandywine", "Sungold", "Cherokee Purple", "San Marzano"],
    "pepper": ["California Wonder", "Jalapeno", "Cayenne", "Shishito", "Habanero"],
    "lettuce": ["Buttercrunch", "Romaine", "Black Seeded Simpson", "Little Gem"],
    "basil": ["Genovese", "Thai Basil", "Lemon Basil", "Purple Basil"],
    "cucumber": ["Marketmore 76", "Straight Eight", "Boston Pickling", "Diva"],
    "summer_squash": ["Black Beauty Zucchini", "Costata Romanesco", "Yellow Crookneck"],
    "bean": ["Provider", "Kentucky Wonder", "Blue Lake", "Dragon Tongue"],
    "pea": ["Sugar Snap", "Oregon Sugar Pod", "Green Arrow", "Wando"],
    "apple": ["Honeycrisp", "Gala", "Fuji", "McIntosh", "Liberty"],
    "blueberry": ["Bluecrop", "Duke", "Patriot", "Sunshine Blue"],
    "strawberry": ["Seascape", "Albion", "Earliglow", "Jewel"],
    "raspberry": ["Heritage", "Caroline", "Anne", "Latham"],
    "sunflower": ["Mammoth", "Teddy Bear", "Lemon Queen", "Autumn Beauty"],
    "marigold": ["French Dwarf", "Crackerjack", "Lemon Gem", "Tangerine Gem"],
    "zinnia": ["Benary's Giant", "State Fair", "Profusion", "Cut and Come Again"],
    "lavender": ["Munstead", "Hidcote", "Grosso", "Phenomenal"],
}

COMPANIONS = [
    ("tomato", "basil", "beneficial", "medium", "Basil fits tomato beds and is commonly used as an aromatic companion.", "symmetric", 12, 36),
    ("tomato", "marigold", "beneficial", "medium", "Marigolds provide a flowering edge and can confuse pests.", "symmetric", 12, 48),
    ("tomato", "carrot", "beneficial", "medium", "Carrots are commonly listed as compatible with tomatoes and use different soil space.", "symmetric", 6, 24),
    ("tomato", "lettuce", "beneficial", "medium", "Lettuce can use space beneath slower, taller tomato plants before the tomato canopy fills in.", "symmetric", 8, 24),
    ("tomato", "onion", "beneficial", "medium", "Onions are commonly listed as compatible with tomatoes and can add aromatic diversity.", "symmetric", 6, 24),
    ("tomato", "chives", "beneficial", "medium", "Chives are a compact allium often paired near tomatoes for aromatic diversity.", "symmetric", 6, 24),
    ("tomato", "parsley", "beneficial", "medium", "Parsley is commonly listed as a tomato herb companion and supports garden diversity.", "symmetric", 8, 24),
    ("tomato", "radish", "beneficial", "medium", "Radishes can be interplanted around tomatoes as a fast crop before tomatoes need full space.", "symmetric", 4, 18),
    ("tomato", "potato", "avoid", "high", "Both are nightshades and can share blight and pest pressure.", "symmetric", 36, None),
    ("tomato", "corn", "avoid", "medium", "Tomatoes and corn can share pest pressure and are commonly listed as a poor pairing.", "symmetric", 36, None),
    ("tomato", "cabbage", "avoid", "medium", "Tomatoes are commonly listed as a poor companion for cabbage-family crops.", "symmetric", 24, None),
    ("carrot", "onion", "beneficial", "medium", "Alliums and carrots are commonly paired for pest confusion.", "symmetric", 3, 18),
    ("carrot", "lettuce", "beneficial", "medium", "Carrots and lettuce use different root and canopy space in close plantings.", "symmetric", 3, 12),
    ("carrot", "radish", "beneficial", "medium", "Radishes can mark carrot rows and mature before carrots need full root space.", "symmetric", 2, 8),
    ("onion", "lettuce", "beneficial", "medium", "Onions and lettuce are commonly listed as compatible close-space crops.", "symmetric", 4, 12),
    ("onion", "strawberry", "beneficial", "medium", "Onions are commonly listed as compatible with strawberries in companion charts.", "symmetric", 6, 18),
    ("garlic", "strawberry", "beneficial", "low", "Garlic is an allium that can add aromatic diversity near strawberries without heavy competition.", "symmetric", 6, 18),
    ("bean", "onion", "avoid", "high", "Onions can stunt beans and should not be interplanted with them.", "symmetric", 24, None),
    ("bean", "garlic", "avoid", "high", "Garlic and other alliums are commonly listed as poor companions for beans.", "symmetric", 24, None),
    ("pea", "onion", "avoid", "high", "Onions are commonly listed as a poor pairing for peas.", "symmetric", 24, None),
    ("pea", "garlic", "avoid", "high", "Garlic and other alliums are commonly listed as poor companions for peas.", "symmetric", 24, None),
    ("bean", "corn", "beneficial", "medium", "Beans can use corn as support in three-sisters style plantings.", "one_way", 6, 18),
    ("bean", "potato", "beneficial", "medium", "Beans and potatoes are commonly listed as compatible vegetable companions.", "symmetric", 12, 36),
    ("bean", "lettuce", "beneficial", "medium", "Bush beans and leaf lettuce are compatible in close-space raised bed plantings.", "symmetric", 8, 24),
    ("bean", "beet", "beneficial", "low", "Bush beans and beets are commonly listed as compatible in raised-bed companion tables.", "symmetric", 8, 24),
    ("pea", "corn", "beneficial", "medium", "Corn can support climbing peas in mixed plantings when timing and spacing fit.", "one_way", 6, 18),
    ("corn", "summer_squash", "guild", "medium", "Squash shades soil beneath corn in a warm-season guild.", "symmetric", 18, 48),
    ("corn", "winter_squash", "guild", "medium", "Winter squash can shade soil beneath corn in a three-sisters style guild.", "symmetric", 18, 48),
    ("corn", "cucumber", "beneficial", "medium", "Corn and cucumber are commonly listed as compatible warm-season companions.", "symmetric", 18, 48),
    ("corn", "pumpkin", "guild", "medium", "Pumpkin can shade soil beneath corn in a warm-season guild.", "symmetric", 24, 60),
    ("cucumber", "nasturtium", "beneficial", "medium", "Nasturtium flowers can support pollinators and draw pests from cucumbers.", "symmetric", 12, 36),
    ("cucumber", "bean", "beneficial", "medium", "Beans and cucumbers are commonly listed as compatible warm-season companions.", "symmetric", 12, 36),
    ("cucumber", "pea", "beneficial", "medium", "Peas are commonly listed as compatible near cucumbers when seasonal timing fits.", "symmetric", 12, 36),
    ("cucumber", "sunflower", "beneficial", "low", "Sunflowers can provide vertical structure and pollinator value near cucumbers.", "symmetric", 18, 48),
    ("cucumber", "radish", "beneficial", "medium", "Radishes are commonly listed as compatible with cucumbers and mature quickly.", "symmetric", 4, 18),
    ("cucumber", "lettuce", "beneficial", "medium", "Lettuce can occupy cooler, lower space near cucumbers in raised-bed plantings.", "symmetric", 8, 24),
    ("cucumber", "potato", "avoid", "medium", "Cucumbers and potatoes are commonly listed as poor companions due to competition and disease concerns.", "symmetric", 36, None),
    ("cucumber", "sage", "avoid", "medium", "Aromatic sage is commonly listed as a poor companion for cucumbers.", "symmetric", 24, None),
    ("pepper", "basil", "beneficial", "medium", "Basil is commonly paired with peppers in warm, sunny beds.", "symmetric", 8, 24),
    ("pepper", "lettuce", "beneficial", "medium", "Lettuce can use space near peppers before pepper plants fill out.", "symmetric", 8, 24),
    ("pepper", "spinach", "beneficial", "medium", "Spinach can use lower space near peppers in raised-bed plantings.", "symmetric", 8, 24),
    ("pepper", "onion", "beneficial", "medium", "Onions are commonly listed as compatible with peppers.", "symmetric", 6, 24),
    ("cabbage", "dill", "beneficial", "low", "Dill flowers can attract beneficial insects near brassicas.", "symmetric", 12, 36),
    ("cabbage", "onion", "beneficial", "medium", "Onion-family crops are commonly listed as compatible with cabbage-family crops.", "symmetric", 8, 24),
    ("cabbage", "spinach", "beneficial", "medium", "Spinach is commonly listed as compatible with cabbage-family crops.", "symmetric", 8, 24),
    ("cabbage", "sage", "beneficial", "medium", "Sage is commonly listed as compatible with cabbage-family crops.", "symmetric", 12, 36),
    ("cabbage", "rosemary", "beneficial", "medium", "Rosemary is commonly listed as compatible with cabbage-family crops.", "symmetric", 18, 48),
    ("cabbage", "strawberry", "avoid", "medium", "Strawberries are commonly listed as poor companions for cabbage-family crops.", "symmetric", 24, None),
    ("kale", "onion", "beneficial", "medium", "Kale is a cabbage-family crop and pairs with onion-family companions in common charts.", "symmetric", 8, 24),
    ("kale", "spinach", "beneficial", "medium", "Kale and spinach are commonly listed as compatible cool-season companions.", "symmetric", 8, 24),
    ("kale", "sunflower", "beneficial", "low", "Sunflowers can support beneficial insects near cabbage-family crops when not shading them excessively.", "symmetric", 18, 48),
    ("broccoli", "beet", "beneficial", "medium", "Beets are commonly listed as compatible with broccoli and other cabbage-family crops.", "symmetric", 8, 24),
    ("broccoli", "lettuce", "beneficial", "medium", "Lettuce can occupy space near broccoli before larger brassica leaves fill out.", "symmetric", 8, 24),
    ("broccoli", "spinach", "beneficial", "medium", "Spinach is commonly listed as compatible with broccoli and other cabbage-family crops.", "symmetric", 8, 24),
    ("broccoli", "onion", "beneficial", "medium", "Onions are commonly listed as compatible with broccoli and other cabbage-family crops.", "symmetric", 8, 24),
    ("fennel", "tomato", "avoid", "medium", "Fennel is often isolated because it can suppress nearby vegetables.", "one_way", 48, None),
    ("fennel", "bean", "avoid", "medium", "Fennel is usually kept away from annual vegetable beds.", "one_way", 48, None),
    ("lettuce", "radish", "succession", "medium", "Fast radishes can mark rows and finish before lettuce needs more space.", "symmetric", 2, 8),
    ("lettuce", "strawberry", "beneficial", "medium", "Lettuce is commonly listed as compatible near strawberries and can serve as a low border crop.", "symmetric", 6, 18),
    ("spinach", "strawberry", "beneficial", "medium", "Spinach and strawberries are commonly listed as compatible close plantings.", "symmetric", 6, 18),
    ("strawberry", "borage", "pollinator_support", "low", "Borage draws pollinators near strawberry flowers.", "symmetric", 12, 36),
    ("strawberry", "bean", "beneficial", "medium", "Bush beans are commonly listed as compatible near strawberries.", "symmetric", 12, 36),
    ("strawberry", "cabbage", "avoid", "medium", "Cabbage-family crops are commonly listed as poor companions for strawberries.", "symmetric", 24, None),
    ("potato", "marigold", "beneficial", "medium", "Marigolds are commonly used around crops with beetle pressure, including potatoes.", "symmetric", 12, 36),
    ("potato", "pea", "beneficial", "medium", "Peas are commonly listed as compatible near potatoes.", "symmetric", 12, 36),
    ("potato", "raspberry", "avoid", "medium", "Potatoes and raspberries are commonly listed as a poor pairing due to disease and pest pressure.", "symmetric", 36, None),
    ("summer_squash", "marigold", "beneficial", "medium", "Marigolds are commonly used around squash-family crops for garden diversity and pest confusion.", "symmetric", 12, 36),
    ("summer_squash", "radish", "beneficial", "medium", "Radishes are commonly listed as compatible with squash-family crops.", "symmetric", 6, 24),
    ("winter_squash", "marigold", "beneficial", "medium", "Marigolds are commonly used around squash-family crops for garden diversity and pest confusion.", "symmetric", 12, 36),
    ("pumpkin", "marigold", "beneficial", "medium", "Marigolds are commonly used around pumpkin and squash plantings for garden diversity and pest confusion.", "symmetric", 12, 36),
    ("apple", "chives", "pest_deterrent", "low", "Chives are a compact allium sometimes used around fruit trees.", "one_way", 24, 72),
    ("blueberry", "clover", "neutral", "low", "Low clover can cover paths nearby but should not compete with acidic blueberry beds.", "symmetric", 24, None),
]

REGION_RULES = [
    ("tomato", "6", "Great Lakes", "2026-03-20", "2026-05-15", None, "2026-07-15", "2026-09-30"),
    ("pepper", "6", "Great Lakes", "2026-03-10", "2026-05-20", None, "2026-07-25", "2026-09-30"),
    ("lettuce", "6", "Great Lakes", "2026-03-15", None, "2026-04-01", "2026-05-01", "2026-06-15"),
    ("basil", "6", "Great Lakes", "2026-04-10", "2026-05-25", None, "2026-06-20", "2026-09-15"),
    ("cucumber", "6", "Great Lakes", "2026-04-20", "2026-05-25", "2026-05-20", "2026-07-10", "2026-09-10"),
    ("carrot", "6", "Great Lakes", None, None, "2026-04-05", "2026-06-15", "2026-10-15"),
    ("garlic", "6", "Great Lakes", None, None, "2026-10-15", "2027-07-01", "2027-07-30"),
]


def plant_records() -> list[dict]:
    records: list[dict] = []
    for slug, name, sci, min_z, max_z, sun, water, spacing, row, mat_min, mat_max, frost, direct, transplant, beginner, maintenance in VEGETABLES:
        records.append(_plant(slug, name, sci, "vegetable", "perennial" if slug in {"asparagus", "rhubarb"} else "annual", True, False, False, False, False, min_z, max_z, sun, water, spacing, row, mat_min, mat_max, frost, direct, transplant, beginner, maintenance))
    for slug, name, sci, min_z, max_z, sun, water, spacing, row, mat_min, mat_max, frost, edible, beginner, maintenance in HERBS:
        records.append(_plant(slug, name, sci, "herb", "perennial" if min_z > 2 and slug not in {"basil", "cilantro", "dill"} else "annual", edible, True, False, False, False, min_z, max_z, sun, water, spacing, row, mat_min, mat_max, frost, True, False, beginner, maintenance, pollinator=7))
    for slug, name, sci, category, min_z, max_z, sun, water, spacing, row, mat_min, mat_max, woody, beginner, maintenance in FRUITS:
        records.append(_plant(slug, name, sci, category, "perennial", True, True, category == "tree", category == "shrub", False, min_z, max_z, sun, water, spacing, row, mat_min, mat_max, "frost_hardy" if min_z <= 5 else "light_frost_tolerant", False, True, beginner, maintenance, pollinator=7, wildlife=7))
    for slug, name, sci, category, min_z, max_z, sun, water, spacing, row, mat_min, mat_max, native, ornamental, pollinator, wildlife, maintenance in FLOWERS_NATIVE_COVER:
        records.append(_plant(slug, name, sci, category, "perennial" if native and category != "cover_crop" else "annual", category in {"cover_crop"} and slug == "buckwheat", ornamental, False, False, native, min_z, max_z, sun, water, spacing, row, mat_min, mat_max, "light_frost_tolerant", True, False, 8, maintenance, pollinator=pollinator, wildlife=wildlife))
    for slug, name, sci, category, min_z, max_z, sun, water, spacing, row, mat_min, mat_max in EXTRA_PLANTS:
        is_tree = category == "tree"
        is_shrub = category == "shrub"
        edible = category in {"vegetable", "fruit", "herb", "tree", "shrub", "native"} and slug not in {"phlox", "salvia", "snapdragon", "petunia", "geranium", "coreopsis"}
        records.append(_plant(slug, name, sci, category, "perennial" if category in {"tree", "shrub", "native", "ornamental"} else "annual", edible, category in {"flower", "ornamental", "native"}, is_tree, is_shrub, category == "native", min_z, max_z, sun, water, spacing, row, mat_min, mat_max, "frost_hardy" if min_z <= 4 else "light_frost_tolerant", True, False, 6, "moderate", pollinator=7 if category in {"flower", "native", "herb"} else 4, wildlife=7 if category in {"native", "tree", "shrub"} else 4))
    return records


def cultivar_records(plants: list[dict]) -> list[dict]:
    by_slug = {plant["slug"]: plant for plant in plants}
    records = []
    for plant_slug, names in CULTIVARS.items():
        plant = by_slug[plant_slug]
        for idx, cultivar_name in enumerate(names):
            slug = f"{plant_slug}_{slugify(cultivar_name)}"
            compact = any(token in cultivar_name.lower() for token in ["dwarf", "little", "teddy", "bush", "patio", "gem"])
            records.append(
                {
                    "plant_slug": plant_slug,
                    "slug": slug,
                    "cultivar_name": cultivar_name,
                    "normalized_name": cultivar_name.lower(),
                    "description": f"Starter cultivar record for {cultivar_name} {plant['common_name']}.",
                    "days_to_maturity_min": max(20, (plant["typical_days_to_maturity_min"] or 60) - idx * 2),
                    "days_to_maturity_max": max(25, (plant["typical_days_to_maturity_max"] or 80) - idx),
                    "min_hardiness_zone": plant["min_hardiness_zone"],
                    "max_hardiness_zone": plant["max_hardiness_zone"],
                    "sunlight_requirement_override": None,
                    "water_requirement_override": None,
                    "spacing_inches_override": max(6, (plant["typical_spacing_inches"] or 12) - (6 if compact else 0)),
                    "row_spacing_inches_override": plant["typical_row_spacing_inches"],
                    "height_inches_min": 8 if compact else None,
                    "height_inches_max": 36 if compact else plant["typical_height_inches"],
                    "spread_inches_min": None,
                    "spread_inches_max": plant["typical_spread_inches"],
                    "flavor_profile": _flavor(cultivar_name),
                    "common_uses": _uses(plant_slug, cultivar_name),
                    "disease_resistance": "Catalog-specific; verify with supplier for local strains.",
                    "heat_tolerance_score": 7 if plant_slug in {"tomato", "pepper", "basil", "cucumber"} else None,
                    "cold_tolerance_score": 7 if plant_slug in {"lettuce", "pea", "apple", "blueberry", "raspberry"} else None,
                    "drought_tolerance_score": 7 if plant_slug in {"lavender", "sunflower"} else None,
                    "container_friendly": compact or plant_slug in {"basil", "lettuce", "pepper", "strawberry", "lavender"},
                    "compact_variety": compact,
                    "heirloom": any(token in cultivar_name.lower() for token in ["brandywine", "cherokee", "black seeded", "costata"]),
                    "hybrid": any(token in cultivar_name.lower() for token in ["sungold", "diva", "phenomenal", "profusion"]),
                    "open_pollinated": not any(token in cultivar_name.lower() for token in ["sungold", "diva", "phenomenal", "profusion"]),
                    "seed_saving_friendly": not any(token in cultivar_name.lower() for token in ["sungold", "diva", "phenomenal", "profusion"]),
                    "recommended_regions": "Use local extension guidance for final cultivar selection.",
                    "avoid_regions": None,
                    "notes": "Cultivar values override species defaults where present.",
                    "created_at": NOW,
                    "updated_at": NOW,
                }
            )
    return records


def planting_rules(plants: list[dict]) -> list[dict]:
    rules = []
    for plant in plants:
        if plant["transplant_recommended"]:
            rules.append(_rule(plant["slug"], "start_indoors", "last_frost", -56, -28, None, None, "Start indoors before transplanting after local frost risk."))
            rules.append(_rule(plant["slug"], "transplant", "last_frost", 7, 21, None, None, "Harden off seedlings before transplanting."))
        if plant["direct_sow_allowed"]:
            rules.append(_rule(plant["slug"], "direct_sow", "last_frost", -14 if plant["frost_tolerance"] != "frost_tender" else 7, 21, 45 if plant["frost_tolerance"] != "frost_tender" else 60, None, "Direct sow when soil and weather are suitable."))
        if plant["typical_days_to_maturity_max"] and plant["typical_days_to_maturity_max"] <= 70:
            rules.append(_rule(plant["slug"], "succession_plant", "calendar_month", None, None, None, None, "Repeat small sowings every 2-3 weeks during the suitable season."))
        if plant["frost_tolerance"] in {"light_frost_tolerant", "frost_hardy"}:
            rules.append(_rule(plant["slug"], "fall_planting", "first_frost", -70, -35, None, None, "Can be used in fall plantings when days to maturity fit before hard frost."))
    return rules


def _plant(slug: str, name: str, sci: str, category: str, lifecycle: str, edible: bool, ornamental: bool, is_tree: bool, is_shrub: bool, native: bool, min_z: int, max_z: int, sun: str, water: str, spacing: int, row: int, mat_min: int, mat_max: int, frost: str, direct: bool, transplant: bool, beginner: int, maintenance: str, pollinator: int = 4, wildlife: int = 4) -> dict:
    return {
        "slug": slug,
        "common_name": name,
        "scientific_name": sci,
        "plant_category": category if category in PLANT_CATEGORIES else "ornamental",
        "lifecycle": lifecycle,
        "edible": edible,
        "ornamental": ornamental,
        "is_tree": is_tree,
        "is_shrub": is_shrub,
        "is_native_option": native,
        "general_description": f"{name} knowledge base default record for garden planning.",
        "min_hardiness_zone": min_z,
        "max_hardiness_zone": max_z,
        "sunlight_requirement": sun,
        "water_requirement": water,
        "soil_ph_min": 5.5,
        "soil_ph_max": 7.2,
        "typical_spacing_inches": spacing,
        "typical_row_spacing_inches": row,
        "typical_height_inches": 240 if is_tree else 72 if is_shrub else max(8, spacing * 2),
        "typical_spread_inches": row,
        "typical_days_to_maturity_min": mat_min,
        "typical_days_to_maturity_max": mat_max,
        "frost_tolerance": frost,
        "direct_sow_allowed": direct,
        "transplant_recommended": transplant,
        "beginner_friendliness_score": beginner,
        "maintenance_level": maintenance,
        "pollinator_value_score": pollinator,
        "wildlife_value_score": wildlife,
        "notes": "Curated starter data; refine with local extension and supplier details.",
        "created_at": NOW,
        "updated_at": NOW,
    }


def _rule(plant_slug: str, rule_type: str, relative_to: str, offset_min: int | None, offset_max: int | None, min_soil: int | None, max_soil: int | None, notes: str) -> dict:
    return {
        "plant_slug": plant_slug,
        "cultivar_slug": None,
        "rule_type": rule_type,
        "relative_to": relative_to,
        "offset_days_min": offset_min,
        "offset_days_max": offset_max,
        "min_soil_temp_f": min_soil,
        "max_soil_temp_f": max_soil,
        "notes": notes,
        "created_at": NOW,
        "updated_at": NOW,
    }


def _flavor(name: str) -> str:
    lower = name.lower()
    if any(token in lower for token in ["sungold", "honeycrisp", "seascape", "albion"]):
        return "sweet"
    if any(token in lower for token in ["jalapeno", "cayenne", "habanero"]):
        return "hot"
    if "lemon" in lower:
        return "citrus"
    return "classic"


def _uses(plant_slug: str, name: str) -> str:
    uses = {
        "tomato": "fresh_eating,sauce,container",
        "pepper": "fresh_eating,sauce,drying,container",
        "lettuce": "fresh_eating,container",
        "basil": "fresh_eating,drying,container",
        "sunflower": "cut_flower,pollinator,ornamental",
        "marigold": "pollinator,ornamental,container",
        "zinnia": "cut_flower,pollinator,ornamental",
        "lavender": "pollinator,drying,ornamental,container",
    }
    if "Roma" in name or "San Marzano" in name:
        return "sauce,preserving"
    return uses.get(plant_slug, "fresh_eating")


def data_sources() -> list[dict]:
    return [
        {
            "source_name": "JakeGPT curated starter plant knowledge",
            "source_url": None,
            "source_type": "manual",
            "license_notes": "Internal curated facts intended for development seed data.",
            "retrieved_at": NOW,
            "notes": "Use public extension services and supplier catalogs to refine records over time.",
            "created_at": NOW,
            "updated_at": NOW,
        }
    ]
