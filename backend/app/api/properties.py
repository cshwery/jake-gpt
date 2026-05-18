from fastapi import APIRouter, Depends, HTTPException
from geoalchemy2 import WKTElement
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core import get_settings
from app.db.session import get_db
from app.models import Property, User
from app.schemas.property import GeocodeRead, GeocodeRequest, PropertyCreate, PropertyRead
from app.services.geocoding import GeocodingError, GeocodeResult, get_geocoder

router = APIRouter(prefix="/properties", tags=["properties"])


@router.post("", response_model=PropertyRead)
def create_property(payload: PropertyCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> Property:
    result = _geocode_address(payload.address)
    prop = Property(
        user_id=user.id,
        address_raw=payload.address,
        normalized_address=result.normalized_address,
        latitude=result.latitude,
        longitude=result.longitude,
        geocoder_provider=result.provider,
        geocoder_accuracy=result.accuracy,
        geocoder_confidence=result.confidence,
        geocoder_bbox=result.bbox,
        raw_geocoder_result=result.raw_result,
        point=WKTElement(f"POINT({result.longitude} {result.latitude})", srid=4326),
    )
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop


@router.post("/geocode", response_model=GeocodeRead)
def geocode_property(payload: GeocodeRequest, user: User = Depends(get_current_user)) -> GeocodeResult:
    return _geocode_address(payload.address)


@router.get("", response_model=list[PropertyRead])
def list_properties(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[Property]:
    return list(db.query(Property).filter(Property.user_id == user.id).order_by(Property.id.desc()).all())


def _geocode_address(address: str) -> GeocodeResult:
    settings = get_settings()
    try:
        return get_geocoder(
            provider=settings.geocoder_provider,
            mapbox_access_token=settings.mapbox_access_token,
            legacy_api_key=settings.geocoder_api_key,
        ).geocode(address)
    except GeocodingError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
