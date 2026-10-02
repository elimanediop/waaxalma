from app.observability.operations import observe, record_usage
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from app.core.streaming_translation_chunk import (
    StreamingTranslationChunk,
)


class OpenAIStreamingTranslationProvider:

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        client: Any | None = None,
    ) -> None:
        normalized_api_key = (
            api_key.strip()
            if api_key
            else ""
        )

        normalized_model = (
            model.strip()
            if model
            else ""
        )

        if not normalized_api_key:
            raise ValueError(
                "OpenAI API key cannot be empty."
            )

        if not normalized_model:
            raise ValueError(
                "Streaming translation model "
                "cannot be empty."
            )

        self._model = (
            normalized_model
        )

        self._client = (
            client
            if client is not None
            else AsyncOpenAI(
                api_key=(
                    normalized_api_key
                ),
            )
        )

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

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
        return self._translate_stream(
            text=text,
            target_language=target_language,
            context=context,
            terminology=terminology,
        )

    @observe("translation", model=None)
    async def _translate_stream(
        self,
        *,
        text: str,
        target_language: str,
        context: str | None = None,
        terminology: list[str] | None = None,
    ) -> AsyncIterator[
        StreamingTranslationChunk
    ]:
        normalized_text = (
            text.strip()
            if text
            else ""
        )

        normalized_target_language = (
            target_language.strip().lower()
            if target_language
            else ""
        )

        if not normalized_text:
            raise ValueError(
                "Translation text cannot be empty."
            )

        if not normalized_target_language:
            raise ValueError(
                "Target language cannot be empty."
            )

        instructions = (
            self._build_instructions(
                target_language=(
                    normalized_target_language
                ),
                context=context,
                terminology=terminology,
            )
        )

        stream = (
            await self._client.responses.create(
                model=self._model,
                instructions=instructions,
                input=normalized_text,
                stream=True,
            )
        )

        completed = False

        async for event in stream:
            event_type = getattr(
                event,
                "type",
                None,
            )

            if (
                event_type
                == "response.output_text.delta"
            ):
                delta = (
                    getattr(
                        event,
                        "delta",
                        "",
                    )
                    or ""
                )

                if not delta:
                    continue

                yield (
                    StreamingTranslationChunk(
                        text=delta,
                        is_final=False,
                        metadata={
                            "provider":
                                self.name,
                            "model":
                                self.model,
                        },
                    )
                )

                continue

            if (
                event_type
                == "response.completed"
            ):
                completed = True
                record_usage(getattr(getattr(event, "response", None), "usage", None), model=self.model)

                yield (
                    StreamingTranslationChunk(
                        text="",
                        is_final=True,
                        metadata={
                            "provider":
                                self.name,
                            "model":
                                self.model,
                        },
                    )
                )

                continue

            if event_type == "error":
                error = getattr(
                    event,
                    "error",
                    None,
                )

                message = getattr(
                    error,
                    "message",
                    None,
                )

                if not message:
                    message = (
                        "Streaming translation "
                        "provider error."
                    )

                raise RuntimeError(
                    message
                )

        if not completed:
            yield (
                StreamingTranslationChunk(
                    text="",
                    is_final=True,
                    metadata={
                        "provider":
                            self.name,
                        "model":
                            self.model,
                    },
                )
            )

    @staticmethod
    def _build_instructions(
        *,
        target_language: str,
        context: str | None,
        terminology: list[str] | None,
    ) -> str:
        parts = [
            (
                "You are a realtime speech "
                "translation engine."
            ),
            (
                "Translate the user's text into "
                f"{target_language}."
            ),
            (
                "The user's text is an automatic "
                "speech recognition transcript."
            ),
            (
                "The input comes from automatic "
                "speech recognition and may contain "
                "minor transcription errors, partial "
                "phrases, punctuation mistakes, or "
                "brief code-switching."
            ),
            (
                "When the intended phrase is reasonably "
                "clear from context or supplied "
                "terminology, silently correct only "
                "obvious ASR mistakes before translating."
            ),
            (
                "Do not invent missing information and "
                "do not add explanations."
            ),
            (
                "Produce natural spoken target-language "
                "output rather than a literal "
                "word-for-word translation."
            ),
            (
                "Preserve the original meaning, tone, "
                "proper names, product names, technical "
                "terms, numbers, and units."
            ),
            (
                "Translate only the current input text. "
                "Any conversation context supplied below "
                "is reference material only and must not "
                "be repeated or translated again."
            ),
            (
                "Return only the translation."
            ),
        ]

        normalized_context = (
            context.strip()
            if context
            else ""
        )

        if normalized_context:
            parts.append(
                (
                    "Reference context for disambiguation "
                    "only: "
                    f"{normalized_context}"
                )
            )

        normalized_terminology = [
            item.strip()
            for item in (
                terminology
                or []
            )
            if isinstance(
                item,
                str,
            )
            and item.strip()
        ]

        if normalized_terminology:
            canonical_terms = (
                "\n".join(
                    (
                        f"- {term}"
                        for term
                        in normalized_terminology
                    )
                )
            )

            parts.append(
                (
                    "Canonical terminology:\n"
                    f"{canonical_terms}\n"
                    "If the ASR transcript contains "
                    "a close phonetic or spelling "
                    "variant of one of these terms, "
                    "interpret it as the corresponding "
                    "canonical term when the context "
                    "supports that reading."
                )
            )

        return " ".join(
            parts
        )
