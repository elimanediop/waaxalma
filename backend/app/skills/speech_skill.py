from app.providers.openai_provider import (
    OpenAISpeechProvider,
)


class SpeechSkill:

    def __init__(
        self,
        provider: OpenAISpeechProvider,
    ) -> None:
        self.provider = provider

    async def execute(
        self,
        text: str,
        output_filename: str,
    ) -> str:
        return await self.provider.speak(
            text=text,
            output_filename=output_filename,
        )