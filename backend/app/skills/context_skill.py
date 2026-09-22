from typing import Protocol

from app.core.context_result import ContextResult


class ContextProvider(Protocol):

    @property
    def name(self) -> str:
        ...

    async def enrich(
        self,
        *,
        text: str,
        metadata: dict,
    ) -> ContextResult:
        ...


class ContextSkill:

    def __init__(
        self,
        provider: ContextProvider,
    ) -> None:
        self.provider = provider

    @property
    def provider_name(self) -> str:
        return self.provider.name

    async def execute(
        self,
        *,
        text: str,
        metadata: dict,
    ) -> ContextResult:
        return await self.provider.enrich(
            text=text,
            metadata=metadata,
        )