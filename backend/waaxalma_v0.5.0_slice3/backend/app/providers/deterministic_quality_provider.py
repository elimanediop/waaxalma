from app.core.quality_result import QualityResult


class DeterministicQualityProvider:
    """
    Performs structural quality validation without an LLM call.

    This provider does not claim to perform semantic translation
    evaluation.
    """

    @property
    def name(self) -> str:
        return "deterministic"

    async def evaluate(
        self,
        *,
        source_text: str,
        interpreted_text: str,
        target_language: str,
    ) -> QualityResult:
        issues: list[str] = []

        if not source_text.strip():
            issues.append("empty_source_text")

        if not interpreted_text.strip():
            issues.append("empty_interpreted_text")

        if not target_language.strip():
            issues.append("missing_target_language")

        return QualityResult(
            accepted=len(issues) == 0,
            score=None,
            issues=issues,
            metadata={
                "evaluation": "deterministic",
                "semantic_evaluation": False,
                "target_language": target_language,
            },
        )