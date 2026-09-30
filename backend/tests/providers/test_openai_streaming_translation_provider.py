from types import SimpleNamespace

import pytest

from app.providers.openai_streaming_translation_provider import (
    OpenAIStreamingTranslationProvider,
)


class FakeResponseStream:

    def __init__(
        self,
        events: list[SimpleNamespace],
    ) -> None:
        self._events = events

    def __aiter__(self):
        self._iterator = iter(
            self._events
        )
        return self

    async def __anext__(self):
        try:
            return next(
                self._iterator
            )
        except StopIteration:
            raise StopAsyncIteration


class FakeResponsesAPI:

    def __init__(
        self,
        events: list[SimpleNamespace],
    ) -> None:
        self._events = events
        self.received_request: dict | None = None

    async def create(
        self,
        **kwargs,
    ) -> FakeResponseStream:

        self.received_request = kwargs

        return FakeResponseStream(
            self._events
        )


class FakeOpenAIClient:

    def __init__(
        self,
        events: list[SimpleNamespace],
    ) -> None:
        self.responses = FakeResponsesAPI(
            events
        )


@pytest.mark.asyncio
async def test_streaming_translation_emits_chunks() -> None:

    client = FakeOpenAIClient(
        events=[
            SimpleNamespace(
                type="response.output_text.delta",
                delta="Bon",
            ),
            SimpleNamespace(
                type="response.output_text.delta",
                delta="jour",
            ),
            SimpleNamespace(
                type="response.completed",
            ),
        ]
    )

    provider = OpenAIStreamingTranslationProvider(
        api_key="test-api-key",
        model="gpt-4.1-mini",
        client=client,
    )

    chunks = [
        chunk
        async for chunk
        in provider.translate_stream(
            text="Hello",
            target_language="fr",
        )
    ]

    assert len(chunks) == 3

    assert chunks[0].text == "Bon"
    assert chunks[0].is_final is False

    assert chunks[1].text == "jour"
    assert chunks[1].is_final is False

    assert chunks[2].text == ""
    assert chunks[2].is_final is True

    translated_text = "".join(
        chunk.text
        for chunk in chunks
    )

    assert translated_text == "Bonjour"


@pytest.mark.asyncio
async def test_streaming_translation_sends_expected_request() -> None:

    client = FakeOpenAIClient(
        events=[
            SimpleNamespace(
                type="response.completed",
            ),
        ]
    )

    provider = OpenAIStreamingTranslationProvider(
        api_key="test-api-key",
        model="gpt-4.1-mini",
        client=client,
    )

    chunks = [
        chunk
        async for chunk
        in provider.translate_stream(
            text=" Hello Waaxalma ",
            target_language=" FR ",
            context=(
                "Waaxalma is a product name."
            ),
            terminology=[
                "Waaxalma",
                "Elimane",
            ],
        )
    ]

    assert chunks

    request = (
        client.responses.received_request
    )

    assert request is not None

    assert (
        request["model"]
        == "gpt-4.1-mini"
    )

    assert (
        request["input"]
        == "Hello Waaxalma"
    )

    assert (
        request["stream"]
        is True
    )

    instructions = request[
        "instructions"
    ]

    assert (
        "Translate the user's text into fr."
        in instructions
    )

    assert (
        "Waaxalma is a product name."
        in instructions
    )

    assert (
        "- Waaxalma"
        in instructions
    )

    assert (
        "- Elimane"
        in instructions
    )


@pytest.mark.asyncio
async def test_empty_translation_text_is_rejected() -> None:

    client = FakeOpenAIClient(
        events=[]
    )

    provider = OpenAIStreamingTranslationProvider(
        api_key="test-api-key",
        model="gpt-4.1-mini",
        client=client,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Translation text cannot be empty."
        ),
    ):
        chunks = [
            chunk
            async for chunk
            in provider.translate_stream(
                text="   ",
                target_language="fr",
            )
        ]


@pytest.mark.asyncio
async def test_empty_target_language_is_rejected() -> None:

    client = FakeOpenAIClient(
        events=[]
    )

    provider = OpenAIStreamingTranslationProvider(
        api_key="test-api-key",
        model="gpt-4.1-mini",
        client=client,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Target language cannot be empty."
        ),
    ):
        chunks = [
            chunk
            async for chunk
            in provider.translate_stream(
                text="Hello",
                target_language="   ",
            )
        ]


@pytest.mark.asyncio
async def test_provider_error_event_is_raised() -> None:

    client = FakeOpenAIClient(
        events=[
            SimpleNamespace(
                type="error",
            ),
        ]
    )

    provider = OpenAIStreamingTranslationProvider(
        api_key="test-api-key",
        model="gpt-4.1-mini",
        client=client,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "Streaming translation provider error."
        ),
    ):
        chunks = [
            chunk
            async for chunk
            in provider.translate_stream(
                text="Hello",
                target_language="fr",
            )
        ]


def test_provider_rejects_empty_api_key() -> None:

    with pytest.raises(
        ValueError,
        match=(
            "OpenAI API key cannot be empty."
        ),
    ):
        OpenAIStreamingTranslationProvider(
            api_key="   ",
            model="gpt-4.1-mini",
        )


def test_provider_rejects_empty_model() -> None:

    with pytest.raises(
        ValueError,
        match=(
            "Streaming translation model "
            "cannot be empty."
        ),
    ):
        OpenAIStreamingTranslationProvider(
            api_key="test-api-key",
            model="   ",
        )