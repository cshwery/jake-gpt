from app.seed.data import PLANTS
from app.api.plants import _dedupe_species
from app.engines.recommendations.hardiness import hardiness_warning, should_exclude_for_hardiness


class PlantStub:
    def __init__(self, id: int, common_name: str, slug: str | None = None) -> None:
        self.id = id
        self.common_name = common_name
        self.slug = slug


def test_seed_data_contains_required_plant_search_targets() -> None:
    names = {plant[0] for plant in PLANTS}

    assert "tomato" in names
    assert "apple" in names
    assert [name for name in names if "basil" in name] == ["basil"]
    assert len(names) >= 100


def test_plant_search_dedupes_imported_seed_and_canonical_rows() -> None:
    plants = [
        PlantStub(1, "tomato"),
        PlantStub(115, "Tomato", "tomato"),
        PlantStub(31, "basil"),
        PlantStub(145, "Basil", "basil"),
    ]

    deduped = _dedupe_species(plants)

    assert [plant.id for plant in deduped] == [145, 115]


def test_hardiness_filter_is_lifecycle_aware() -> None:
    apple = PlantStub(1, "apple", "apple")
    apple.tree = True
    apple.perennial = True
    apple.is_tree = True
    apple.is_shrub = False
    apple.min_zone = 8
    apple.max_zone = 10
    tomato = PlantStub(2, "tomato", "tomato")
    tomato.tree = False
    tomato.perennial = False
    tomato.is_tree = False
    tomato.is_shrub = False
    tomato.min_zone = 8
    tomato.max_zone = 10

    assert should_exclude_for_hardiness(apple, 5)
    assert hardiness_warning(apple, 5) == "Apple is not recommended for your hardiness zone and may not survive winter."
    assert not should_exclude_for_hardiness(tomato, 5)
