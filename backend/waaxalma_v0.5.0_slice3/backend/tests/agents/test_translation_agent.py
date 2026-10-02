import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.agents.translation_agent import TranslationAgent
from app.core.agent_input import AgentInput
from app.core.session_context import SessionContext


def create_skill(
    *,
    provider_name: str,
    result=None,
) -> SimpleNamespace:
    return SimpleNamespace(
        provider_name=provider_name,
        execute=AsyncMock(return_value=result),
    )


@pytest.mark.asyncio
async def test_translate_returns_resolved_text() -> None:
    translation_skill = create_skill(
        provider_name="fake-translation",
        result="Hello everyone",
    )

    speech_skill = create_skill(
        provider_name="fake-tts",
        result=None,
    )

    agent = TranslationAgent(
        translation_skill=translation_skill,
        speech_skill=speech_skill,
    )

    context = SessionContext(
        session_id="translation-test",
        target_language="English",
    )

    result = await agent.execute(
        agent_input=AgentInput(
            operation="translate",
            payload={
                "text": "Bonjour tout le monde",
                "target_language": "English",
            },
        ),
        context=context,
    )

    assert result.success is True
    assert result.output is not None

    translated_text = result.output["translated_text"]

    assert translated_text == "Hello everyone"

    # Regression test:
    # TranslationSkill.execute must be awaited.
    assert inspect.iscoroutine(translated_text) is False

    translation_skill.execute.assert_awaited_once_with(
        text="Bonjour tout le monde",
        target_language="English",
    )

    speech_skill.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_speak_waits_for_speech_skill() -> None:
    translation_skill = create_skill(
        provider_name="fake-translation",
    )

    speech_skill = create_skill(
        provider_name="fake-tts",
    )

    agent = TranslationAgent(
        translation_skill=translation_skill,
        speech_skill=speech_skill,
    )

    result = await agent.execute(
        agent_input=AgentInput(
            operation="speak",
            payload={
                "text": "Hello everyone",
            },
        ),
        context=SessionContext(
            session_id="speech-test",
        ),
    )

    assert result.success is True
    assert result.output is not None

    assert result.output["text"] == "Hello everyone"
    assert result.output["audio_url"].endswith(".mp3")

    speech_skill.execute.assert_awaited_once()
    translation_skill.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_translate_and_speak_awaits_both_skills() -> None:
    translation_skill = create_skill(
        provider_name="fake-translation",
        result="Hello everyone",
    )

    speech_skill = create_skill(
        provider_name="fake-tts",
    )

    agent = TranslationAgent(
        translation_skill=translation_skill,
        speech_skill=speech_skill,
    )

    result = await agent.execute(
        agent_input=AgentInput(
            operation="translate_and_speak",
            payload={
                "text": "Bonjour tout le monde",
                "target_language": "English",
            },
        ),
        context=SessionContext(
            session_id="translate-and-speak-test",
        ),
    )

    assert result.success is True
    assert result.output is not None

    assert (
        result.output["translated_text"]
        == "Hello everyone"
    )

    assert inspect.iscoroutine(
        result.output["translated_text"]
    ) is False

    translation_skill.execute.assert_awaited_once_with(
        text="Bonjour tout le monde",
        target_language="English",
    )

    speech_skill.execute.assert_awaited_once()

    _, kwargs = speech_skill.execute.await_args

    assert kwargs["text"] == "Hello everyone"


@pytest.mark.asyncio
async def test_translate_rejects_missing_text() -> None:
    translation_skill = create_skill(
        provider_name="fake-translation",
    )

    speech_skill = create_skill(
        provider_name="fake-tts",
    )

    agent = TranslationAgent(
        translation_skill=translation_skill,
        speech_skill=speech_skill,
    )

    result = await agent.execute(
        agent_input=AgentInput(
            operation="translate",
            payload={},
        ),
        context=SessionContext(
            session_id="invalid-input-test",
        ),
    )

    assert result.success is False
    assert result.output is None
    assert result.error_code == "INVALID_INPUT"

    translation_skill.execute.assert_not_awaited()
    speech_skill.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_unsupported_operation_is_rejected() -> None:
    translation_skill = create_skill(
        provider_name="fake-translation",
    )

    speech_skill = create_skill(
        provider_name="fake-tts",
    )

    agent = TranslationAgent(
        translation_skill=translation_skill,
        speech_skill=speech_skill,
    )

    result = await agent.execute(
        agent_input=AgentInput(
            operation="unknown",
            payload={
                "text": "Bonjour",
            },
        ),
        context=SessionContext(
            session_id="unsupported-operation-test",
        ),
    )

    assert result.success is False
    assert result.output is None
    assert result.error_code == "UNSUPPORTED_OPERATION"

    translation_skill.execute.assert_not_awaited()
    speech_skill.execute.assert_not_awaited()