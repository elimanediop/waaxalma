from app.providers.openai_provider import (
    OpenAISpeechToTextProvider,
)


class SpeechToTextSkill:

    def __init__(
        self,
        provider: OpenAISpeechToTextProvider,
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
        audio_path: str,
    ) -> str:
        return await self.provider.transcribe(
            audio_path=audio_path,
        )