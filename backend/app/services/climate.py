from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ClimateContext:
    hardiness_zone: str
    last_frost_date: date
    precipitation_category: str
    notes: str


class GardenContextProvider:
    def context_for(self, latitude: float, longitude: float) -> ClimateContext:
        raise NotImplementedError


class MockGardenContextProvider(GardenContextProvider):
    def context_for(self, latitude: float, longitude: float) -> ClimateContext:
        if latitude >= 45:
            return ClimateContext("5b", date(2026, 5, 20), "moderate", "Mocked northern climate estimate.")
        if latitude >= 40:
            return ClimateContext("6b", date(2026, 5, 5), "moderate", "Mocked Great Lakes climate estimate.")
        if latitude >= 34:
            return ClimateContext("7b", date(2026, 4, 10), "moderate-low", "Mocked temperate climate estimate.")
        return ClimateContext("9a", date(2026, 2, 20), "variable", "Mocked warm climate estimate.")
