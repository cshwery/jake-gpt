from fastapi import APIRouter, Depends
from geoalchemy2 import WKTElement
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core import get_settings
from app.db.session import get_db
from app.models import Property, User
from app.schemas.property import PropertyCreate, PropertyRead
from app.services.geocoding import get_geocoder

router = APIRouter(prefix="/properties", tags=["properties"])


@router.post("", response_model=PropertyRead)
def create_property(payload: PropertyCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Property:
    result = get_geocoder(get_settings().geocoder_api_key).geocode(payload.address)
    prop = Property(
        user_id=user.id,
        address_raw=payload.address,
        normalized_address=result.normalized_address,
        latitude=result.latitude,
        longitude=result.longitude,
        point=WKTElement(f"POINT({result.longitude} {result.latitude})", srid=4326),
    )
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop


@router.get("", response_model=list[PropertyRead])
def list_properties(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[Property]:
    return list(db.query(Property).filter(Property.user_id == user.id).order_by(Property.id.desc()).all())
