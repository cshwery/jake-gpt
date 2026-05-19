from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class GeocodeResult:
    provider: str
    query: str
    normalized_address: str
    latitude: float
    longitude: float
    accuracy: str | None = None
    confidence: str | None = None
    bbox: list[float] | None = None
    place_name: str | None = None
    raw_result: dict[str, Any] = field(default_factory=dict)


class GeocodingError(RuntimeError):
    pass


class Geocoder:
    provider = "unknown"

    def geocode(self, address: str) -> GeocodeResult:
        raise NotImplementedError


class MapboxGeocoder(Geocoder):
    provider = "mapbox"

    def __init__(self, access_token: str, timeout_seconds: float = 6.0) -> None:
        self.access_token = access_token
        self.timeout_seconds = timeout_seconds

    def geocode(self, address: str) -> GeocodeResult:
        query = _clean_query(address)
        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{quote(query)}.json"
        params = {
            "access_token": self.access_token,
            "limit": 1,
            "types": "address,place,postcode,locality,neighborhood",
        }
        try:
            request = Request(f"{url}?{urlencode(params)}", headers={"User-Agent": "JakeGPT/0.1"})
            with urlopen(request, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise GeocodingError(f"Mapbox geocoding failed with status {exc.code}.") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise GeocodingError("Mapbox geocoding request failed.") from exc
        features = data.get("features") or []
        if not features:
            raise GeocodingError("No geocoding results found for that address.")
        feature = features[0]
        center = feature.get("center") or []
        if len(center) < 2:
            raise GeocodingError("Mapbox returned a result without coordinates.")
        properties = feature.get("properties") or {}
        return GeocodeResult(
            provider=self.provider,
            query=query,
            normalized_address=feature.get("place_name") or feature.get("text") or query,
            latitude=float(center[1]),
            longitude=float(center[0]),
            accuracy=properties.get("accuracy"),
            confidence=str(feature.get("relevance")) if feature.get("relevance") is not None else None,
            bbox=feature.get("bbox"),
            place_name=feature.get("place_name"),
            raw_result={"feature": feature},
        )


class MockGeocoder(Geocoder):
    provider = "mock"

    def geocode(self, address: str) -> GeocodeResult:
        cleaned = _clean_query(address)
        lowered = cleaned.lower()
        if "detroit" in lowered or "michigan" in lowered or " mi" in lowered:
            lat, lon = 42.3314, -83.0458
        elif "chicago" in lowered:
            lat, lon = 41.8781, -87.6298
        elif "seattle" in lowered:
            lat, lon = 47.6062, -122.3321
        else:
            lat, lon = 42.2808, -83.7430
        return GeocodeResult(
            provider=self.provider,
            query=cleaned,
            normalized_address=f"{cleaned} (mock geocode)",
            latitude=lat,
            longitude=lon,
            accuracy="mock",
            confidence="low",
            bbox=[lon - 0.001, lat - 0.001, lon + 0.001, lat + 0.001],
            place_name=f"{cleaned} (mock geocode)",
            raw_result={"mock": True, "query": cleaned},
        )


def get_geocoder(provider: str = "mock", mapbox_access_token: str | None = None, legacy_api_key: str | None = None) -> Geocoder:
    token = mapbox_access_token or legacy_api_key
    if provider == "mapbox" and token:
        return MapboxGeocoder(token)
    return MockGeocoder()


def _clean_query(address: str) -> str:
    cleaned = " ".join(address.strip().split())
    if not cleaned:
        raise GeocodingError("Address is required.")
    return cleaned
