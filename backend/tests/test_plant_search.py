from app.seed.data import PLANTS


def test_seed_data_contains_required_plant_search_targets() -> None:
    names = {plant[0] for plant in PLANTS}

    assert "tomato" in names
    assert "apple" in names
    assert [name for name in names if "basil" in name] == ["basil"]
    assert len(names) >= 100
