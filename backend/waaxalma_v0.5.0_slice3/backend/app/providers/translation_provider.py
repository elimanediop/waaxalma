from typing import Protocol


class TranslationProvider(Protocol):

    @property
    def name(self) -> str:
        ...

    async def translate(
        self,
        text: str,
        target_language: str,
    ) -> str:
        ...