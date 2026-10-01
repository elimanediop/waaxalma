from app.agents.agent_manager import AgentManager
from app.agents.context_agent import ContextAgent
from app.agents.interpreter_agent import InterpreterAgent
from app.agents.quality_agent import QualityAgent
from app.agents.translation_agent import TranslationAgent

from app.core.config import (
    CONTEXT_PROVIDER,
    OPENAI_API_KEY,
    QUALITY_PROVIDER,
    REALTIME_TRANSLATION_MODEL,
    REALTIME_TRANSLATION_PROVIDER,
    SPEECH_PROVIDER,
    SPEECH_TO_TEXT_PROVIDER,
    STREAMING_TRANSCRIPTION_MODEL,
    STREAMING_TRANSCRIPTION_PROVIDER,
    TRANSLATION_PROVIDER,
    STREAMING_TRANSLATION_MODEL,
    STREAMING_TRANSLATION_PROVIDER,
    STREAMING_SPEECH_MODEL,
    STREAMING_SPEECH_PROVIDER,
)

from app.orchestration.agent_orchestrator import AgentOrchestrator

from app.pipelines.sequential_pipeline import SequentialPipeline
from app.pipelines.stages.context_stage import ContextStage
from app.pipelines.stages.quality_stage import QualityStage
from app.pipelines.stages.speech_stage import SpeechStage
from app.pipelines.stages.transcription_stage import (
    TranscriptionStage,
)
from app.pipelines.stages.translation_stage import (
    TranslationStage,
)

from app.providers.deterministic_quality_provider import (
    DeterministicQualityProvider,
)
from app.providers.openai_provider import (
    OpenAISpeechProvider,
    OpenAISpeechToTextProvider,
    OpenAITranslationProvider,
)
from app.providers.openai_realtime_translation_provider import (
    OpenAIRealtimeTranslationProvider,
)
from app.providers.openai_streaming_transcription_provider import (
    OpenAIStreamingTranscriptionProvider,
)
from app.providers.openai_streaming_translation_provider import (
    OpenAIStreamingTranslationProvider,
)
from app.providers.passthrough_context_provider import (
    PassthroughContextProvider,
)
from app.providers.openai_streaming_speech_provider import (
    OpenAIStreamingSpeechProvider,
)

from app.registry.agent_registry import AgentRegistry
from app.registry.pipeline_registry import PipelineRegistry
from app.registry.provider_registry import ProviderRegistry

from app.services.realtime_enhanced_service import (
    RealtimeEnhancedService,
)
from app.services.realtime_translation_service import (
    RealtimeTranslationService,
)

from app.skills.context_skill import ContextSkill
from app.skills.quality_skill import QualitySkill
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

    registry.register(
        capability="context",
        name="passthrough",
        provider=PassthroughContextProvider(),
    )

    registry.register(
        capability="quality",
        name="deterministic",
        provider=DeterministicQualityProvider(),
    )

    registry.register(
        capability="realtime_translation",
        name="openai",
        provider=OpenAIRealtimeTranslationProvider(
            api_key=OPENAI_API_KEY,
            model=REALTIME_TRANSLATION_MODEL,
        ),
    )

    registry.register(
        capability="streaming_transcription",
        name="openai",
        provider=OpenAIStreamingTranscriptionProvider(
            api_key=OPENAI_API_KEY,
            model=STREAMING_TRANSCRIPTION_MODEL,
        ),
    )

    registry.register(
        capability="streaming_translation",
        name="openai",
        provider=OpenAIStreamingTranslationProvider(
            api_key=OPENAI_API_KEY,
            model=STREAMING_TRANSLATION_MODEL,
        ),
    )
    registry.register(
        capability="streaming_speech",
        name="openai",
        provider=OpenAIStreamingSpeechProvider(
            api_key=OPENAI_API_KEY,
            model=STREAMING_SPEECH_MODEL,
        ),
    )

    return registry


def build_pipeline_registry(
    *,
    translation_skill: TranslationSkill,
    speech_skill: SpeechSkill,
    speech_to_text_skill: SpeechToTextSkill,
    context_skill: ContextSkill,
    quality_skill: QualitySkill,
) -> PipelineRegistry:
    registry = PipelineRegistry()

    registry.register(
        SequentialPipeline(
            name="interpreter.text",
            stages=[
                ContextStage(
                    context_skill=context_skill,
                ),
                TranslationStage(
                    translation_skill=translation_skill,
                ),
                QualityStage(
                    quality_skill=quality_skill,
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
                ContextStage(
                    context_skill=context_skill,
                ),
                TranslationStage(
                    translation_skill=translation_skill,
                ),
                QualityStage(
                    quality_skill=quality_skill,
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
    context_provider_name: str = CONTEXT_PROVIDER,
    quality_provider_name: str = QUALITY_PROVIDER,
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

    context_provider = provider_registry.get(
        capability="context",
        name=context_provider_name,
    )

    quality_provider = provider_registry.get(
        capability="quality",
        name=quality_provider_name,
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

    context_skill = ContextSkill(
        provider=context_provider,
    )

    quality_skill = QualitySkill(
        provider=quality_provider,
    )

    # Build and register pipelines
    pipeline_registry = build_pipeline_registry(
        translation_skill=translation_skill,
        speech_skill=speech_skill,
        speech_to_text_skill=speech_to_text_skill,
        context_skill=context_skill,
        quality_skill=quality_skill,
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

    # Register context agent
    registry.register(
        ContextAgent(
            context_skill=context_skill,
        )
    )

    # Register quality agent
    registry.register(
        QualityAgent(
            quality_skill=quality_skill,
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


# Realtime Direct — v0.4.1
realtime_translation_service = RealtimeTranslationService(
    provider_registry=provider_registry,
    provider_name=REALTIME_TRANSLATION_PROVIDER,
)

# Realtime Enhanced — v0.4.2
realtime_enhanced_service = RealtimeEnhancedService(
    provider_registry=provider_registry,
    transcription_provider_name=STREAMING_TRANSCRIPTION_PROVIDER,
    translation_provider_name=STREAMING_TRANSLATION_PROVIDER,
    speech_provider_name=STREAMING_SPEECH_PROVIDER,
)

agent_registry = build_agent_registry(
    provider_registry=provider_registry,
)

agent_manager = AgentManager(
    registry=agent_registry,
)

agent_orchestrator = build_orchestrator(
    registry=agent_registry,
)