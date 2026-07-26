from app.providers.openai_provider import (
    OpenAISpeechToTextProvider,
)


class SpeechToTextSkill:

    def __init__(
        self,
        provider: OpenAISpeechToTextProvider,
    ) -> None:
        self.provider = provider

    async def execute(
        self,
        audio_path: str,
    ) -> str:
        return await self.provider.transcribe(
            audio_path=audio_path,
        )