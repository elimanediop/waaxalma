import pytest

from app.skills.translation_skill import TranslationSkill


class FakeTranslationProvider:

    @property
    def name(self) -> str:
        return "fake"

    async def translate(
        self,
        text: str,
        target_language: str,
    ) -> str:
        return f"[{target_language}] {text}"


@pytest.mark.asyncio
async def test_translation_skill_accepts_interchangeable_provider() -> None:
    provider = FakeTranslationProvider()

    skill = TranslationSkill(
        provider=provider,
    )

    result = await skill.execute(
        text="Bonjour",
        target_language="English",
    )

    assert result == "[English] Bonjour"
    assert skill.provider_name == "fake"