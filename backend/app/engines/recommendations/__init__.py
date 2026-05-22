__all__ = ["GardenRecommendationService"]


def __getattr__(name: str):
    if name == "GardenRecommendationService":
        from app.engines.recommendations.service import GardenRecommendationService

        return GardenRecommendationService
    raise AttributeError(name)
