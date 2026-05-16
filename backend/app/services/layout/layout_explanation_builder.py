class LayoutExplanationBuilder:
    def assumptions(self) -> list[str]:
        return ["LayoutEngine v0 uses a deterministic rectangular grid and does not optimize against the drawn polygon shape yet."]

    def explanations(self) -> list[str]:
        return ["Tall plants are placed toward the north/top edge; access space is represented by sparse grid rows."]
