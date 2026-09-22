from typing import Protocol


class SpeechProvider(Protocol):

    @property
    def name(self) -> str:
        ...

    async def speak(
        self,
        text: str,
        output_filename: str,
    ) -> None:
        ...