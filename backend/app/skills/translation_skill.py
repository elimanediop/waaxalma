from app.providers.openai_provider import (
    OpenAITranslationProvider,
)


class TranslationSkill:

    def __init__(
        self,
        provider: OpenAITranslationProvider,
    ) -> None:
        self.provider = provider

    @property
    def provider_name(self) -> str:
        return getattr(
            self.provider,
            "name",
            self.provider.__class__.__name__,
        )

    async def execute(
        self,
        text: str,
        target_language: str,
    ) -> str:
        return await self.provider.translate(
            text=text,
            target_language=target_language,
        )