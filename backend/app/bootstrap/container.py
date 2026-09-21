from app.agents.agent_manager import AgentManager
from app.agents.interpreter_agent import InterpreterAgent
from app.agents.translation_agent import TranslationAgent

from app.core.config import (
    SPEECH_PROVIDER,
    SPEECH_TO_TEXT_PROVIDER,
    TRANSLATION_PROVIDER,
)

from app.orchestration.agent_orchestrator import AgentOrchestrator

from app.providers.openai_provider import (
    OpenAISpeechProvider,
    OpenAISpeechToTextProvider,
    OpenAITranslationProvider,
)

from app.registry.agent_registry import AgentRegistry
from app.registry.provider_registry import ProviderRegistry
from app.skills.speech_skill import SpeechSkill
from app.skills.speech_to_text_skill import SpeechToTextSkill
from app.skills.translation_skill import TranslationSkill

def build_provider_registry() -> ProviderRegistry:
    registry = ProviderRegistry()

    registry.register(
        capability="translation",
        name="openai",
        provider=OpenAITranslationProvider(),
    )

    registry.register(
        capability="speech",
        name="openai",
        provider=OpenAISpeechProvider(),
    )

    registry.register(
        capability="speech_to_text",
        name="openai",
        provider=OpenAISpeechToTextProvider(),
    )

    return registry


def build_agent_registry(
    provider_registry: ProviderRegistry,
    translation_provider_name: str = TRANSLATION_PROVIDER,
    speech_provider_name: str = SPEECH_PROVIDER,
    speech_to_text_provider_name: str = SPEECH_TO_TEXT_PROVIDER,
) -> AgentRegistry:
    registry = AgentRegistry()

    translation_provider = provider_registry.get(
        capability="translation",
        name=translation_provider_name,
    )

    speech_provider = provider_registry.get(
        capability="speech",
        name=speech_provider_name,
    )

    speech_to_text_provider = provider_registry.get(
        capability="speech_to_text",
        name=speech_to_text_provider_name,
    )

    translation_skill = TranslationSkill(
        provider=translation_provider,
    )

    speech_skill = SpeechSkill(
        provider=speech_provider,
    )

    speech_to_text_skill = SpeechToTextSkill(
        provider=speech_to_text_provider,
    )

    registry.register(
        TranslationAgent(
            translation_skill=translation_skill,
            speech_skill=speech_skill,
        )
    )

    registry.register(
        InterpreterAgent(
            translation_skill=translation_skill,
            speech_skill=speech_skill,
            speech_to_text_skill=speech_to_text_skill,
        )
    )

    return registry


def build_orchestrator(
    registry: AgentRegistry,
) -> AgentOrchestrator:
    return AgentOrchestrator(
        registry=registry,
    )


provider_registry = build_provider_registry()

agent_registry = build_agent_registry(
    provider_registry=provider_registry,
)

agent_manager = AgentManager(
    registry=agent_registry,
)

agent_orchestrator = build_orchestrator(
    registry=agent_registry,
)