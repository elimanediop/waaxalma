from app.providers.translation_provider import TranslationProvider


class TranslationSkill:

    def __init__(
        self,
        provider: TranslationProvider,
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