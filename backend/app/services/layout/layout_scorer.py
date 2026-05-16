from app.models import Plant


class LayoutScorer:
    def score(self, plants: list[Plant], warnings: list[str]) -> dict[str, float]:
        return {
            "determinism_score": 1.0,
            "plant_count": float(len(plants)),
            "warning_count": float(len(warnings)),
        }
