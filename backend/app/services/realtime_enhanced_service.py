from collections.abc import AsyncIterator

from app.core.realtime_enhanced_session import (
    RealtimeEnhancedSession,
)
from app.core.streaming_translation_chunk import (
    StreamingTranslationChunk,
)
from app.registry.provider_registry import (
    ProviderRegistry,
)


class RealtimeEnhancedService:

    def __init__(
        self,
        *,
        provider_registry: ProviderRegistry,
        transcription_provider_name: str,
        translation_provider_name: str,
        speech_provider_name: str,
    ) -> None:
        self._provider_registry = provider_registry

        self._transcription_provider_name = (
            transcription_provider_name
        )

        self._translation_provider_name = (
            translation_provider_name
        )

        self._speech_provider_name = (
            speech_provider_name
        )

    async def create_session(
        self,
        *,
        target_language: str,
        source_languages: list[str] | None = None,
        prompt: str | None = None,
        keywords: list[str] | None = None,
    ) -> RealtimeEnhancedSession:

        normalized_target_language = (
            target_language
            .strip()
            .lower()
        )

        if not normalized_target_language:
            raise ValueError(
                "Target language cannot be empty."
            )

        provider = (
            self._provider_registry.get(
                capability=(
                    "streaming_transcription"
                ),
                name=(
                    self._transcription_provider_name
                ),
            )
        )

        transcription_session = (
            await provider.create_session(
                languages=source_languages,
                prompt=prompt,
                keywords=keywords,
                delay="low",
            )
        )

        return RealtimeEnhancedSession(
            transcription_provider=(
                transcription_session.provider
            ),
            transcription_model=(
                transcription_session.model
            ),
            target_language=(
                normalized_target_language
            ),
            client_secret=(
                transcription_session.client_secret
            ),
            expires_at=(
                transcription_session.expires_at
            ),
            metadata={
                **transcription_session.metadata,
                "mode": "enhanced",
                "stage": "streaming_transcription",
            },
        )

    def translate_stream(
        self,
        *,
        text: str,
        target_language: str,
        context: str | None = None,
        terminology: list[str] | None = None,
    ) -> AsyncIterator[
        StreamingTranslationChunk
    ]:

        provider = (
            self._provider_registry.get(
                capability=(
                    "streaming_translation"
                ),
                name=(
                    self._translation_provider_name
                ),
            )
        )

        return provider.translate_stream(
            text=text,
            target_language=target_language,
            context=context,
            terminology=terminology,
        )

    def speak_stream(
        self,
        *,
        text: str,
        voice_id: str,
        instructions: str | None = None,
    ):
        provider = self._provider_registry.get(
            capability="streaming_speech",
            name=self._speech_provider_name,
        )

        return provider.speak_stream(
            text=text,
            voice_id=voice_id,
            instructions=instructions,
        )