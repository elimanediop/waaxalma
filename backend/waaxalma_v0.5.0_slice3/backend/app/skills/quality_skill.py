from typing import Protocol

from app.core.quality_result import QualityResult


class QualityProvider(Protocol):

    @property
    def name(self) -> str:
        ...

    async def evaluate(
        self,
        *,
        source_text: str,
        interpreted_text: str,
        target_language: str,
    ) -> QualityResult:
        ...


class QualitySkill:

    def __init__(
        self,
        provider: QualityProvider,
    ) -> None:
        self.provider = provider

    @property
    def provider_name(self) -> str:
        return self.provider.name

    async def execute(
        self,
        *,
        source_text: str,
        interpreted_text: str,
        target_language: str,
    ) -> QualityResult:
        return await self.provider.evaluate(
            source_text=source_text,
            interpreted_text=interpreted_text,
            target_language=target_language,
        )