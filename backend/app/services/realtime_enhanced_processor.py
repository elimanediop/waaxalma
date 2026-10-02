import asyncio
import logging
import time
from collections import deque
from collections.abc import AsyncIterator
from typing import cast

from app.core.realtime_enhanced_output import (
    RealtimeEnhancedOutput,
    RealtimeEnhancedSpeechOutput,
    RealtimeEnhancedTranslationOutput,
)
from app.core.realtime_enhanced_runtime import (
    RealtimeEnhancedRuntime,
)
from app.core.speakable_text_segment import (
    SpeakableTextSegment,
)
from app.core.streaming_translation_chunk import (
    StreamingTranslationChunk,
)
from app.services.realtime_enhanced_service import (
    RealtimeEnhancedService,
)
from app.services.speakable_text_buffer import (
    SpeakableTextBuffer,
)


logger = logging.getLogger(__name__)


class RealtimeEnhancedProcessor:

    def __init__(
        self,
        *,
        runtime: RealtimeEnhancedRuntime,
        service: RealtimeEnhancedService,
        speakable_soft_max_chars: int = 80,
    ) -> None:
        self._runtime = runtime
        self._service = service

        self._speakable_text_buffer = (
            SpeakableTextBuffer(
                soft_max_chars=(
                    speakable_soft_max_chars
                ),
            )
        )


        self._source_context_history: deque[str] = (
            deque(
                maxlen=3,
            )
        )

    @property
    def session_id(self) -> str:
        return self._runtime.session_id

    @property
    def target_language(self) -> str:
        return self._runtime.target_language

    @property
    def pending_transcript(self) -> str:
        return self._runtime.pending_transcript

    def append_transcript_delta(
        self,
        delta: str,
    ) -> None:
        self._runtime.append_transcript_delta(
            delta
        )

    def _resolve_source_segment(
        self,
        *,
        final_text: str | None = None,
    ):
        segment = (
            self._runtime.commit_transcript()
        )

        if segment is None:
            return None

        normalized_final_text = (
            final_text.strip()
            if isinstance(
                final_text,
                str,
            )
            else ""
        )

        if normalized_final_text:
            segment = (
                segment.model_copy(
                    update={
                        "text":
                            normalized_final_text,
                        "metadata": {
                            **segment.metadata,
                            "transcript_source":
                                "final",
                        },
                    }
                )
            )
        else:
            segment = (
                segment.model_copy(
                    update={
                        "metadata": {
                            **segment.metadata,
                            "transcript_source":
                                "partial_buffer",
                        },
                    }
                )
            )

        return segment

    def _build_translation_context(
        self,
    ) -> str | None:
        parts: list[str] = []

        runtime_context = (
            self._runtime.context
        )

        if (
            runtime_context
            and runtime_context.strip()
        ):
            parts.append(
                runtime_context.strip()
            )

        if self._source_context_history:
            previous = "\n".join(
                (
                    f"{index}. {text}"
                    for index, text in enumerate(
                        self._source_context_history,
                        start=1,
                    )
                )
            )

            parts.append(
                (
                    "Previous source transcript segments "
                    "(context only; do not translate them "
                    "again):\n"
                    f"{previous}"
                )
            )

        if not parts:
            return None

        return "\n\n".join(
            parts
        )

    def _remember_source_segment(
        self,
        text: str,
    ) -> None:
        normalized = (
            text.strip()
        )

        if normalized:
            self._source_context_history.append(
                normalized
            )

    async def commit_and_translate(
        self,
        *,
        final_text: str | None = None,
    ) -> AsyncIterator[
        StreamingTranslationChunk
    ]:
        segment = (
            self._resolve_source_segment(
                final_text=final_text,
            )
        )

        if segment is None:
            return

        translation_context = (
            self._build_translation_context()
        )

        self._remember_source_segment(
            segment.text
        )

        async for chunk in (
            self._service.translate_stream(
                text=segment.text,
                target_language=(
                    self._runtime.target_language
                ),
                context=translation_context,
                terminology=(
                    self._runtime.terminology
                ),
            )
        ):
            metadata = {
                **chunk.metadata,
                "session_id":
                    self._runtime.session_id,
                "segment_sequence":
                    segment.sequence,
                "target_language":
                    self._runtime.target_language,
            }

            yield chunk.model_copy(
                update={
                    "metadata":
                        metadata,
                }
            )

    async def commit_translate_and_speak(
        self,
        *,
        voice_id: str,
        speech_instructions: str | None = None,
        final_text: str | None = None,
    ) -> AsyncIterator[
        RealtimeEnhancedOutput
    ]:
        source_segment = (
            self._resolve_source_segment(
                final_text=final_text,
            )
        )

        if source_segment is None:
            return

        translation_context = (
            self._build_translation_context()
        )

        self._remember_source_segment(
            source_segment.text
        )

        commit_started_at = (
            time.perf_counter()
        )

        first_translation_at: (
            float | None
        ) = None

        first_speakable_at: (
            float | None
        ) = None

        tts_started_at: (
            float | None
        ) = None

        first_audio_at: (
            float | None
        ) = None

        output_queue: asyncio.Queue = (
            asyncio.Queue()
        )

        speech_queue: asyncio.Queue = (
            asyncio.Queue()
        )

        speech_done = object()
        output_done = object()

        base_metadata = {
            "session_id":
                self._runtime.session_id,

            "source_segment_sequence":
                source_segment.sequence,

            "target_language":
                self._runtime.target_language,
        }

        async def produce_translation() -> None:
            nonlocal first_translation_at
            nonlocal first_speakable_at

            translation_request_started_at = (
                time.perf_counter()
            )

            logger.debug(
                "[EnhancedLatency] "
                "commit_to_translation_request_ms=%.1f "
                "segment=%s",
                (
                    translation_request_started_at
                    - commit_started_at
                ) * 1000,
                source_segment.sequence,
            )

            try:
                async for chunk in (
                    self._service.translate_stream(
                        text=(
                            source_segment.text
                        ),
                        target_language=(
                            self._runtime
                            .target_language
                        ),
                        context=(
                            translation_context
                        ),
                        terminology=(
                            self._runtime.terminology
                        ),
                    )
                ):
                    translation_chunk = (
                        chunk.model_copy(
                            update={
                                "metadata": {
                                    **chunk.metadata,
                                    **base_metadata,
                                }
                            }
                        )
                    )

                    if (
                        translation_chunk.text
                        and
                        first_translation_at is None
                    ):
                        first_translation_at = (
                            time.perf_counter()
                        )

                        logger.info(
                            "[EnhancedLatency] "
                            "commit_to_first_translation_ms=%.1f "
                            "translation_request_to_first_delta_ms=%.1f "
                            "segment=%s",
                            (
                                first_translation_at
                                - commit_started_at
                            ) * 1000,
                            (
                                first_translation_at
                                - translation_request_started_at
                            ) * 1000,
                            source_segment.sequence,
                        )

                    await output_queue.put(
                        RealtimeEnhancedTranslationOutput(
                            chunk=(
                                translation_chunk
                            ),
                        )
                    )

                    if translation_chunk.text:
                        speakable_segments = (
                            self
                            ._speakable_text_buffer
                            .append(
                                translation_chunk.text,
                                metadata=(
                                    base_metadata
                                ),
                            )
                        )

                        for speakable_segment in (
                            speakable_segments
                        ):
                            if (
                                first_speakable_at
                                is None
                            ):
                                first_speakable_at = (
                                    time.perf_counter()
                                )

                                logger.debug(
                                    "[EnhancedLatency] "
                                    "commit_to_first_speakable_ms=%.1f "
                                    "translation_to_speakable_ms=%.1f "
                                    "segment=%s",
                                    (
                                        first_speakable_at
                                        - commit_started_at
                                    ) * 1000,
                                    (
                                        first_speakable_at
                                        - (
                                            first_translation_at
                                            or first_speakable_at
                                        )
                                    ) * 1000,
                                    source_segment.sequence,
                                )

                            logger.debug("[Enhanced] speech segment prepared")

                            await speech_queue.put(
                                speakable_segment
                            )

            except Exception as exc:
                logger.error(
                    "[Enhanced] translation failed"
                )

                await output_queue.put(
                    exc
                )

            else:
                remaining_segment = (
                    self
                    ._speakable_text_buffer
                    .flush(
                        metadata=(
                            base_metadata
                        ),
                    )
                )

                if remaining_segment is not None:
                    if (
                        first_speakable_at
                        is None
                    ):
                        first_speakable_at = (
                            time.perf_counter()
                        )

                        logger.info(
                            "[EnhancedLatency] "
                            "commit_to_first_speakable_ms=%.1f "
                            "translation_to_speakable_ms=%.1f "
                            "segment=%s",
                            (
                                first_speakable_at
                                - commit_started_at
                            ) * 1000,
                            (
                                first_speakable_at
                                - (
                                    first_translation_at
                                    or first_speakable_at
                                )
                            ) * 1000,
                            source_segment.sequence,
                        )

                    logger.debug("[Enhanced] speech segment prepared")

                    await speech_queue.put(
                        remaining_segment
                    )

            finally:
                await speech_queue.put(
                    speech_done
                )

        async def produce_speech() -> None:
            nonlocal tts_started_at
            nonlocal first_audio_at

            try:
                while True:
                    item = (
                        await speech_queue.get()
                    )

                    if item is speech_done:
                        break

                    speakable_segment = cast(
                        SpeakableTextSegment,
                        item,
                    )

                    if tts_started_at is None:
                        tts_started_at = (
                            time.perf_counter()
                        )

                        logger.debug(
                            "[EnhancedLatency] "
                            "commit_to_tts_start_ms=%.1f "
                            "speakable_to_tts_start_ms=%.1f "
                            "segment=%s",
                            (
                                tts_started_at
                                - commit_started_at
                            ) * 1000,
                            (
                                tts_started_at
                                - (
                                    first_speakable_at
                                    or tts_started_at
                                )
                            ) * 1000,
                            source_segment.sequence,
                        )

                    logger.debug("[Enhanced] speech segment prepared")

                    async for chunk in (
                        self._service.speak_stream(
                            text=(
                                speakable_segment.text
                            ),
                            voice_id=(
                                voice_id
                            ),
                            instructions=(
                                speech_instructions
                            ),
                        )
                    ):
                        if (
                            chunk.audio
                            and first_audio_at is None
                        ):
                            first_audio_at = (
                                time.perf_counter()
                            )

                            logger.info(
                                "[EnhancedLatency] "
                                "commit_to_first_audio_ms=%.1f "
                                "tts_to_first_audio_ms=%.1f "
                                "translation_to_first_audio_ms=%.1f "
                                "segment=%s",
                                (
                                    first_audio_at
                                    - commit_started_at
                                ) * 1000,
                                (
                                    first_audio_at
                                    - (
                                        tts_started_at
                                        or first_audio_at
                                    )
                                ) * 1000,
                                (
                                    first_audio_at
                                    - (
                                        first_translation_at
                                        or first_audio_at
                                    )
                                ) * 1000,
                                source_segment.sequence,
                            )

                        logger.debug(
                            "[Enhanced] TTS chunk "
                            "bytes=%s final=%s "
                            "content_type=%s sample_rate=%s",
                            len(chunk.audio),
                            chunk.is_final,
                            chunk.content_type,
                            chunk.sample_rate,
                        )

                        speech_chunk = (
                            chunk.model_copy(
                                update={
                                    "metadata": {
                                        **chunk.metadata,
                                        **base_metadata,
                                        (
                                            "speech_segment_"
                                            "sequence"
                                        ):
                                            speakable_segment
                                            .sequence,
                                    }
                                }
                            )
                        )

                        await output_queue.put(
                            RealtimeEnhancedSpeechOutput(
                                chunk=(
                                    speech_chunk
                                ),
                            )
                        )

            except Exception as exc:
                logger.error(
                    "[Enhanced] TTS failed"
                )

                await output_queue.put(
                    exc
                )

            finally:
                await output_queue.put(
                    output_done
                )

        translation_task = (
            asyncio.create_task(
                produce_translation()
            )
        )

        speech_task = (
            asyncio.create_task(
                produce_speech()
            )
        )

        try:
            while True:
                item = (
                    await output_queue.get()
                )

                if item is output_done:
                    break

                if isinstance(
                    item,
                    Exception,
                ):
                    raise item

                yield cast(
                    RealtimeEnhancedOutput,
                    item,
                )

        finally:
            for task in (
                translation_task,
                speech_task,
            ):
                if not task.done():
                    task.cancel()

            await asyncio.gather(
                translation_task,
                speech_task,
                return_exceptions=True,
            )

    def reset(
        self,
    ) -> None:
        self._runtime.reset()

        self._speakable_text_buffer.reset()

        self._source_context_history.clear()
