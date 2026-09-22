from typing import Protocol


class SpeechToTextProvider(Protocol):

    @property
    def name(self) -> str:
        ...

    async def transcribe(
        self,
        audio_path: str,
    ) -> str:
        ...