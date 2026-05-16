from dataclasses import dataclass


@dataclass(frozen=True)
class GeocodeResult:
    normalized_address: str
    latitude: float
    longitude: float


class Geocoder:
    def geocode(self, address: str) -> GeocodeResult:
        raise NotImplementedError


class MockGeocoder(Geocoder):
    def geocode(self, address: str) -> GeocodeResult:
        cleaned = " ".join(address.strip().split())
        lowered = cleaned.lower()
        if "detroit" in lowered or "michigan" in lowered or "mi" in lowered:
            lat, lon = 42.3314, -83.0458
        elif "chicago" in lowered:
            lat, lon = 41.8781, -87.6298
        elif "seattle" in lowered:
            lat, lon = 47.6062, -122.3321
        else:
            lat, lon = 42.2808, -83.7430
        return GeocodeResult(normalized_address=f"{cleaned} (mock geocode)", latitude=lat, longitude=lon)


def get_geocoder(api_key: str | None = None) -> Geocoder:
    return MockGeocoder()
