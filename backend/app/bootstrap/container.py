from app.agents.agent_manager import AgentManager
from app.agents.interpreter_agent import InterpreterAgent
from app.agents.translation_agent import TranslationAgent

from app.core.config import (
    SPEECH_PROVIDER,
    SPEECH_TO_TEXT_PROVIDER,
    TRANSLATION_PROVIDER,
)

from app.orchestration.agent_orchestrator import AgentOrchestrator

from app.pipelines.sequential_pipeline import SequentialPipeline
from app.pipelines.stages.speech_stage import SpeechStage
from app.pipelines.stages.transcription_stage import (
    TranscriptionStage,
)
from app.pipelines.stages.translation_stage import (
    TranslationStage,
)

from app.providers.openai_provider import (
    OpenAISpeechProvider,
    OpenAISpeechToTextProvider,
    OpenAITranslationProvider,
)

from app.registry.agent_registry import AgentRegistry
from app.registry.pipeline_registry import PipelineRegistry
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


def build_pipeline_registry(
    *,
    translation_skill: TranslationSkill,
    speech_skill: SpeechSkill,
    speech_to_text_skill: SpeechToTextSkill,
) -> PipelineRegistry:
    registry = PipelineRegistry()

    registry.register(
        SequentialPipeline(
            name="interpreter.text",
            stages=[
                TranslationStage(
                    translation_skill=translation_skill,
                ),
                SpeechStage(
                    speech_skill=speech_skill,
                ),
            ],
        )
    )

    registry.register(
        SequentialPipeline(
            name="interpreter.audio",
            stages=[
                TranscriptionStage(
                    speech_to_text_skill=speech_to_text_skill,
                ),
                TranslationStage(
                    translation_skill=translation_skill,
                ),
                SpeechStage(
                    speech_skill=speech_skill,
                ),
            ],
        )
    )

    return registry


def build_agent_registry(
    provider_registry: ProviderRegistry,
    translation_provider_name: str = TRANSLATION_PROVIDER,
    speech_provider_name: str = SPEECH_PROVIDER,
    speech_to_text_provider_name: str = SPEECH_TO_TEXT_PROVIDER,
) -> AgentRegistry:
    registry = AgentRegistry()

    # Resolve configured providers
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

    # Build skills
    translation_skill = TranslationSkill(
        provider=translation_provider,
    )

    speech_skill = SpeechSkill(
        provider=speech_provider,
    )

    speech_to_text_skill = SpeechToTextSkill(
        provider=speech_to_text_provider,
    )

    # Build and register pipelines
    pipeline_registry = build_pipeline_registry(
        translation_skill=translation_skill,
        speech_skill=speech_skill,
        speech_to_text_skill=speech_to_text_skill,
    )

    # Register translation agent
    registry.register(
        TranslationAgent(
            translation_skill=translation_skill,
            speech_skill=speech_skill,
        )
    )

    # Register interpreter agent using pipelines
    registry.register(
        InterpreterAgent(
            text_pipeline=pipeline_registry.get(
                "interpreter.text"
            ),
            audio_pipeline=pipeline_registry.get(
                "interpreter.audio"
            ),
        )
    )

    return registry


def build_orchestrator(
    registry: AgentRegistry,
) -> AgentOrchestrator:
    return AgentOrchestrator(
        registry=registry,
    )


# ------------------------------------------------------------------
# Application composition root
# ------------------------------------------------------------------

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