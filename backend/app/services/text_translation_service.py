from typing import Any

from app.core.session_context import SessionContext
from app.core.text_translation_result import TextTranslationResult
from app.pipelines.pipeline import Pipeline
from app.pipelines.pipeline_state import PipelineState


class TextTranslationService:

    def __init__(
        self,
        *,
        pipeline: Pipeline,
    ) -> None:
        self._pipeline = pipeline

    async def translate(
        self,
        *,
        text: str,
        target_language: str,
        source_language: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TextTranslationResult:
        if not isinstance(text, str) or not text.strip():
            raise ValueError(
                "Text cannot be empty."
            )

        if (
            not isinstance(target_language, str)
            or not target_language.strip()
        ):
            raise ValueError(
                "Target language cannot be empty."
            )

        normalized_text = text.strip()
        normalized_target_language = target_language.strip()

        normalized_source_language = (
            source_language.strip()
            if isinstance(source_language, str)
            and source_language.strip()
            else None
        )

        context = SessionContext(
            source_language=normalized_source_language,
            target_language=normalized_target_language,
        )

        state = PipelineState(
            data={
                "source_text": normalized_text,
                "source_language": normalized_source_language,
                "target_language": normalized_target_language,
                "agent_name": "text_translation",
                "context_metadata": dict(metadata or {}),
            }
        )

        result_state = await self._pipeline.execute(
            state=state,
            context=context,
        )

        return TextTranslationResult(
            source_text=normalized_text,
            translated_text=result_state.require(
                "interpreted_text"
            ),
            source_language=normalized_source_language,
            target_language=normalized_target_language,
            quality_accepted=result_state.require(
                "quality_accepted"
            ),
            quality_score=result_state.get(
                "quality_score"
            ),
            quality_issues=result_state.get(
                "quality_issues",
                [],
            ),
            metadata={
                "context": result_state.get(
                    "context_metadata",
                    {},
                ),
                "quality": result_state.get(
                    "quality_metadata",
                    {},
                ),
            },
        )