import pytest

from app.bootstrap.container import build_agent_registry
from app.core.agent_input import AgentInput
from app.core.session_context import SessionContext
from app.registry.provider_registry import ProviderRegistry


class FakeTranslationProvider:

    @property
    def name(self) -> str:
        return "fake"

    async def translate(
        self,
        text: str,
        target_language: str,
    ) -> str:
        return f"[fake:{target_language}] {text}"


class FakeSpeechProvider:

    def __init__(self) -> None:
        self.calls: list[dict] = []

    @property
    def name(self) -> str:
        return "fake"

    async def speak(
        self,
        text: str,
        output_filename: str,
    ) -> None:
        self.calls.append(
            {
                "text": text,
                "output_filename": output_filename,
            }
        )


class FakeSpeechToTextProvider:

    @property
    def name(self) -> str:
        return "fake"

    async def transcribe(
        self,
        audio_path: str,
    ) -> str:
        return "Fake transcription"

def build_fake_provider_registry() -> ProviderRegistry:
    registry = ProviderRegistry()

    registry.register(
        capability="translation",
        name="fake",
        provider=FakeTranslationProvider(),
    )

    registry.register(
        capability="speech",
        name="fake",
        provider=FakeSpeechProvider(),
    )

    registry.register(
        capability="speech_to_text",
        name="fake",
        provider=FakeSpeechToTextProvider(),
    )

    return registry

@pytest.mark.asyncio
async def test_agent_composition_uses_selected_translation_provider() -> None:
    provider_registry = build_fake_provider_registry()

    agent_registry = build_agent_registry(
        provider_registry=provider_registry,
        translation_provider_name="fake",
        speech_provider_name="fake",
        speech_to_text_provider_name="fake",
    )

    translation_agent = agent_registry.find(
        "translation"
    )

    assert translation_agent is not None

    assert (
        translation_agent.translation_skill.provider_name
        == "fake"
    )

    assert (
        translation_agent.speech_skill.provider_name
        == "fake"
    )

    result = await translation_agent.execute(
        agent_input=AgentInput(
            operation="translate",
            payload={
                "text": "Bonjour",
                "target_language": "English",
            },
        ),
        context=SessionContext(
            session_id="fake-provider-test",
        ),
    )

    assert result.success is True
    assert result.output is not None

    assert (
        result.output["translated_text"]
        == "[fake:English] Bonjour"
    )

@pytest.mark.asyncio
async def test_interpreter_uses_selected_providers() -> None:
    provider_registry = build_fake_provider_registry()

    agent_registry = build_agent_registry(
        provider_registry=provider_registry,
        translation_provider_name="fake",
        speech_provider_name="fake",
        speech_to_text_provider_name="fake",
    )

    interpreter = agent_registry.find(
        "interpreter"
    )

    assert interpreter is not None

    assert (
        interpreter.translation_skill.provider_name
        == "fake"
    )

    assert (
        interpreter.speech_skill.provider_name
        == "fake"
    )

    assert (
        interpreter.speech_to_text_skill.provider_name
        == "fake"
    )

    context = SessionContext(
        session_id="fake-interpreter-test",
        target_language="English",
    )

    result = await interpreter.execute(
        agent_input=AgentInput(
            operation="interpret_audio",
            payload={
                "audio_path": "fake.wav",
                "target_language": "English",
            },
        ),
        context=context,
    )

    assert result.success is True
    assert result.output is not None

    assert (
        result.output["source_text"]
        == "Fake transcription"
    )

    assert (
        result.output["interpreted_text"]
        == "[fake:English] Fake transcription"
    )  


def test_unknown_configured_provider_fails_fast() -> None:
    provider_registry = build_fake_provider_registry()

    with pytest.raises(
        KeyError,
        match="not registered",
    ):
        build_agent_registry(
            provider_registry=provider_registry,
            translation_provider_name="unknown",
            speech_provider_name="fake",
            speech_to_text_provider_name="fake",
        )