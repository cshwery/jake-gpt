from pydantic import BaseModel, Field


class PropertyCreate(BaseModel):
    address: str


class GeocodeRequest(BaseModel):
    address: str


class GeocodeRead(BaseModel):
    provider: str
    query: str
    normalized_address: str
    latitude: float
    longitude: float
    accuracy: str | None = None
    confidence: str | None = None
    bbox: list[float] | None = None
    place_name: str | None = None
    raw_result: dict = Field(default_factory=dict)


class PropertyRead(BaseModel):
    id: int
    address_raw: str
    normalized_address: str
    latitude: float
    longitude: float
    geocoder_provider: str | None = None
    geocoder_accuracy: str | None = None
    geocoder_confidence: str | None = None
    geocoder_bbox: list[float] | None = None

    model_config = {"from_attributes": True}
