from app.seed.data import PLANTS
from app.api.plants import _dedupe_species


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
