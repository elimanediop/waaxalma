from typing import Protocol

from app.core.realtime_translation_session import (
    RealtimeTranslationSession,
)


class RealtimeTranslationProvider(
    Protocol
):

    @property
    def name(self) -> str:
        ...


    @property
    def model(self) -> str:
        ...


    async def create_session(
        self,
        *,
        target_language: str,
    ) -> RealtimeTranslationSession:
        ...