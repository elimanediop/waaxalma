import pytest

from app.core.context_result import ContextResult
from app.core.quality_result import QualityResult
from app.skills.context_skill import ContextSkill
from app.skills.quality_skill import QualitySkill


class FakeContextProvider:

    @property
    def name(self) -> str:
        return "fake-context"

    async def enrich(
        self,
        *,
        text: str,
        metadata: dict,
    ) -> ContextResult:
        return ContextResult(
            original_text=text,
            enriched_text=f"[context] {text}",
            metadata=metadata,
        )


class FakeQualityProvider:

    @property
    def name(self) -> str:
        return "fake-quality"

    async def evaluate(
        self,
        *,
        source_text: str,
        interpreted_text: str,
        target_language: str,
    ) -> QualityResult:
        return QualityResult(
            accepted=True,
            score=0.95,
            issues=[],
            metadata={
                "target_language": target_language,
            },
        )


@pytest.mark.asyncio
async def test_context_skill_uses_context_provider() -> None:
    skill = ContextSkill(
        provider=FakeContextProvider(),
    )

    result = await skill.execute(
        text="Naka nga def?",
        metadata={
            "session_id": "context-test",
        },
    )

    assert result.original_text == "Naka nga def?"
    assert result.enriched_text == "[context] Naka nga def?"
    assert skill.provider_name == "fake-context"


@pytest.mark.asyncio
async def test_quality_skill_uses_quality_provider() -> None:
    skill = QualitySkill(
        provider=FakeQualityProvider(),
    )

    result = await skill.execute(
        source_text="Naka nga def?",
        interpreted_text="How are you?",
        target_language="English",
    )

    assert result.accepted is True
    assert result.score == 0.95
    assert result.issues == []
    assert skill.provider_name == "fake-quality"