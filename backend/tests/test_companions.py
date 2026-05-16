from types import SimpleNamespace

from app.services.companions import companion_notes, relationship_lookup


def test_companion_notes_include_beneficial_relationship() -> None:
    tomato = SimpleNamespace(id=1, common_name="tomato")
    basil = SimpleNamespace(id=2, common_name="basil")
    rel = SimpleNamespace(source_plant_id=1, target_plant_id=2, relationship_type="beneficial", rationale="Good neighbors.")

    notes = companion_notes([tomato, basil], [rel])

    assert notes == ["Tomato and Basil: beneficial. Good neighbors."]


def test_relationship_lookup_is_bidirectional() -> None:
    rel = SimpleNamespace(source_plant_id=1, target_plant_id=2, relationship_type="avoid", relationship_direction="symmetric")

    lookup = relationship_lookup([rel])

    assert lookup[(1, 2)] == "avoid"
    assert lookup[(2, 1)] == "avoid"


def test_relationship_lookup_respects_one_way_relationships() -> None:
    rel = SimpleNamespace(source_plant_id=1, target_plant_id=2, relationship_type="shade_support", relationship_direction="one_way")

    lookup = relationship_lookup([rel])

    assert lookup[(1, 2)] == "shade_support"
    assert (2, 1) not in lookup
