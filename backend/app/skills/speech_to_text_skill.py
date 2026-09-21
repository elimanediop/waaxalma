from app.providers.speech_to_text_provider import (
    SpeechToTextProvider,
)


class SpeechToTextSkill:

    def __init__(
        self,
        provider: SpeechToTextProvider,
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