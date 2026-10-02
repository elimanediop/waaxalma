from app.observability.operations import observe, record_usage
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.core.streaming_speech_chunk import (
    StreamingSpeechChunk,
)


class OpenAIStreamingSpeechProvider:

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        client: AsyncOpenAI | None = None,
    ) -> None:

        if not api_key.strip():
            raise ValueError(
                "OpenAI API key cannot be empty."
            )

        if not model.strip():
            raise ValueError(
                "Streaming speech model cannot be empty."
            )

        self._model = model.strip()

        self._client = (
            client
            if client is not None
            else AsyncOpenAI(
                api_key=api_key.strip(),
            )
        )

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    @observe("tts", model=None)
    async def speak_stream(
        self,
        *,
        text: str,
        voice_id: str,
        instructions: str | None = None,
    ) -> AsyncIterator[
        StreamingSpeechChunk
    ]:

        normalized_text = text.strip()

        if not normalized_text:
            raise ValueError(
                "Speech text cannot be empty."
            )

        normalized_voice_id = (
            voice_id.strip()
        )

        if not normalized_voice_id:
            raise ValueError(
                "Voice ID cannot be empty."
            )

        request: dict = {
            "model":
                self._model,

            "voice":
                normalized_voice_id,

            "input":
                normalized_text,

            "response_format":
                "pcm",
        }

        if (
            instructions
            and instructions.strip()
        ):
            request["instructions"] = (
                instructions.strip()
            )

        async with (
            self._client
            .audio
            .speech
            .with_streaming_response
            .create(
                **request
            )
        ) as response:

            async for audio_chunk in (
                response.iter_bytes()
            ):

                if not audio_chunk:
                    continue

                yield StreamingSpeechChunk(
                    audio=audio_chunk,
                    is_final=False,
                    content_type="audio/pcm",
                    sample_rate=24000,
                    metadata={
                        "provider":
                            self.name,

                        "model":
                            self.model,

                        "voice_id":
                            normalized_voice_id,
                    },
                )

        yield StreamingSpeechChunk(
            audio=b"",
            is_final=True,
            content_type="audio/pcm",
            sample_rate=24000,
            metadata={
                "provider":
                    self.name,

                "model":
                    self.model,

                "voice_id":
                    normalized_voice_id,
            },
        )