from typing import Any

from app.core.context_result import ContextResult


class PassthroughContextProvider:
    """
    Context provider that preserves the original text.

    It allows the context capability to be part of the framework
    without introducing an additional external/LLM call.
    """

    @property
    def name(self) -> str:
        return "passthrough"

    async def enrich(
        self,
        *,
        text: str,
        metadata: dict[str, Any],
    ) -> ContextResult:
        return ContextResult(
            original_text=text,
            enriched_text=text,
            metadata=metadata,
        )