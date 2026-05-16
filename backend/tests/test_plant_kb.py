from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import DataSource, Plant, PlantCompanion, PlantCompanionRelationship, PlantCultivar, PlantRegionRule, PlantingRule
from app.plant_kb.builder import build_database
from app.plant_kb.companion_relationships import BENEFICIAL_TYPES, load_relationship_seed, validate_relationship_seed
from app.plant_kb.import_pg import import_from_sqlite
from app.plant_kb.service import avoid_conflicts, relationship_lookup, resolve_profile, score_cultivar, score_species, search_species_and_cultivars
from app.plant_kb.validate import validate_database


def test_building_sqlite_knowledge_base(tmp_path: Path) -> None:
    db_path = tmp_path / "plant_kb.sqlite"
    counts = build_database(db_path)

    assert db_path.exists()
    assert counts["plants"] >= 100
    assert counts["cultivars"] >= 50


def test_validation_required_fields_and_relationships(tmp_path: Path) -> None:
    db_path = tmp_path / "plant_kb.sqlite"
    build_database(db_path)

    ok, errors, counts = validate_database(db_path)

    assert ok, errors
    assert counts["plants"] >= 100
    assert counts["plant_cultivars"] >= 50


def test_cultivar_override_resolution() -> None:
    plant = Plant(
        slug="tomato",
        common_name="Tomato",
        plant_type="vegetable",
        plant_category="vegetable",
        lifecycle="annual",
        edible=True,
        flower=True,
        tree=False,
        perennial=False,
        min_zone=3,
        max_zone=10,
        min_hardiness_zone=3,
        max_hardiness_zone=10,
        sunlight_requirement="full_sun",
        water_requirement="medium",
        spacing_inches=24,
        row_spacing_inches=36,
        typical_spacing_inches=24,
        typical_row_spacing_inches=36,
        typical_days_to_maturity_min=70,
        typical_days_to_maturity_max=90,
        maintenance_level="moderate",
        planting_notes="Stake.",
    )
    cultivar = PlantCultivar(slug="tomato_sungold", cultivar_name="Sungold", normalized_name="sungold", spacing_inches_override=18, days_to_maturity_min=55, days_to_maturity_max=65)

    profile = resolve_profile(plant, cultivar)

    assert profile.display_name == "Tomato - Sungold"
    assert profile.spacing_inches == 18
    assert profile.days_to_maturity_max == 65
    assert profile.sunlight_requirement == "full_sun"


def test_companion_lookup_and_avoid_conflict_detection() -> None:
    beneficial = PlantCompanionRelationship(source_plant_id=1, target_plant_id=2, relationship_type="beneficial", confidence="medium", evidence_type="extension_service", rationale="ok", source_name="Test", relationship_direction="symmetric")
    avoid = PlantCompanionRelationship(source_plant_id=1, target_plant_id=3, relationship_type="avoid", confidence="high", evidence_type="extension_service", rationale="bad", source_name="Test", relationship_direction="symmetric")

    lookup = relationship_lookup([beneficial, avoid])
    conflicts = avoid_conflicts([1, 3], [beneficial, avoid])

    assert lookup[(2, 1)].relationship_type == "beneficial"
    assert conflicts == [avoid]


def test_companion_jsonl_seed_validation() -> None:
    result = validate_relationship_seed()
    rows = load_relationship_seed()

    assert result.ok, result.errors
    assert result.count >= 50
    assert result.symmetric_count > 0
    assert all(row["rationale"] and row["source_name"] and row["source_notes"] for row in rows)


def test_companion_jsonl_avoid_pairs_do_not_conflict_with_beneficial_types() -> None:
    rows = load_relationship_seed()
    pair_types: dict[frozenset[str], set[str]] = {}
    for row in rows:
        pair = frozenset((row["source_plant_slug"], row["target_plant_slug"]))
        pair_types.setdefault(pair, set()).add(row["relationship_type"])

    assert all(not ("avoid" in types and types & BENEFICIAL_TYPES) for types in pair_types.values())


def test_plant_search_across_species_and_cultivars() -> None:
    tomato = Plant(id=1, slug="tomato", common_name="Tomato")
    basil = Plant(id=2, slug="basil", common_name="Basil")
    sungold = PlantCultivar(plant_id=1, slug="tomato_sungold", cultivar_name="Sungold", normalized_name="sungold")

    results = search_species_and_cultivars([tomato, basil], [sungold], "sun")

    assert results == ["Tomato > Sungold"]


def test_recommendation_scoring_uses_species_and_cultivar_data() -> None:
    plant = Plant(
        id=1,
        slug="lettuce",
        common_name="Lettuce",
        edible=True,
        is_tree=False,
        tree=False,
        min_zone=2,
        max_zone=9,
        min_hardiness_zone=2,
        max_hardiness_zone=9,
        sunlight_requirement="part_sun",
        water_requirement="medium",
        spacing_inches=8,
        typical_spacing_inches=8,
        maintenance_level="low",
        beginner_friendliness_score=9,
    )
    cultivar = PlantCultivar(slug="lettuce_little_gem", cultivar_name="Little Gem", normalized_name="little gem", common_uses="fresh_eating,container", container_friendly=True, compact_variety=True, days_to_maturity_max=45)

    species_score, species_reasons = score_species(plant, hardiness_zone=6, sunlight="part_sun", water="medium", goal="food", maintenance="low", available_space_inches=12)
    cultivar_score, cultivar_reasons = score_cultivar(cultivar, plant, goal="container", max_days_to_maturity=50, container=True)

    assert species_score >= 15
    assert "hardiness match" in species_reasons
    assert cultivar_score >= 9
    assert "container friendly" in cultivar_reasons


def test_idempotent_postgresql_import(tmp_path: Path) -> None:
    db_path = tmp_path / "plant_kb.sqlite"
    build_database(db_path)
    engine = create_engine("sqlite:///:memory:", future=True)
    for table in [Plant.__table__, PlantCultivar.__table__, PlantCompanion.__table__, PlantCompanionRelationship.__table__, PlantingRule.__table__, PlantRegionRule.__table__, DataSource.__table__]:
        table.create(engine)
    with Session(engine) as session:
        first = import_from_sqlite(db_path, session)
        second = import_from_sqlite(db_path, session)
        plants = session.scalars(select(Plant)).all()
        cultivars = session.scalars(select(PlantCultivar)).all()

    assert first["plants_inserted"] >= 100
    assert second["plants_inserted"] == 0
    assert second["plants_updated"] >= 100
    assert len(plants) == first["plants_inserted"]
    assert len(cultivars) == first["cultivars_inserted"]
