from pydantic import BaseModel


class PropertyCreate(BaseModel):
    address: str


class PropertyRead(BaseModel):
    id: int
    address_raw: str
    normalized_address: str
    latitude: float
    longitude: float

    model_config = {"from_attributes": True}
