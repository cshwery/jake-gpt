from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Plant, PlantCompanion, User
from app.seed.data import COMPANIONS, PLANTS
from app.services.security import hash_password


def run() -> None:
    db = SessionLocal()
    try:
        if db.scalar(select(User).where(User.email == "demo@jakegpt.ai")) is None:
            db.add(User(email="demo@jakegpt.ai", full_name="JakeGPT Demo", password_hash=hash_password("JakePass")))

        plants_by_name: dict[str, Plant] = {}
        for values in PLANTS:
            common_name = values[0]
            plant = db.scalar(select(Plant).where(Plant.common_name == common_name))
            if plant is None:
                plant = Plant(
                    common_name=values[0],
                    scientific_name=values[1],
                    plant_type=values[2],
                    edible=values[3],
                    flower=values[4],
                    tree=values[5],
                    perennial=values[6],
                    min_zone=values[7],
                    max_zone=values[8],
                    sunlight_requirement=values[9],
                    water_requirement=values[10],
                    spacing_inches=values[11],
                    row_spacing_inches=values[12],
                    days_to_maturity=values[13],
                    maintenance_level=values[14],
                    planting_notes=values[15],
                )
                db.add(plant)
                db.flush()
            plants_by_name[common_name] = plant

        for source, target, rel_type, notes in COMPANIONS:
            if source not in plants_by_name or target not in plants_by_name:
                continue
            exists = db.scalar(
                select(PlantCompanion).where(
                    PlantCompanion.plant_id == plants_by_name[source].id,
                    PlantCompanion.companion_plant_id == plants_by_name[target].id,
                )
            )
            if exists is None:
                db.add(
                    PlantCompanion(
                        plant_id=plants_by_name[source].id,
                        companion_plant_id=plants_by_name[target].id,
                        relationship_type=rel_type,
                        notes=notes,
                    )
                )
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run()
