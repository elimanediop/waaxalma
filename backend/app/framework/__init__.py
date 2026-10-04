"""Public extension contracts for Waaxalma.

These exports preserve the identity of the original classes. Importing this
module does not configure the application or instantiate provider clients.
See docs/framework-contracts.md for the compatibility boundary.
"""

from app.agents.base_agent import BaseAgent
from app.core.agent_input import AgentInput
from app.core.agent_result import AgentResult
from app.core.execution_trace import ExecutionTrace, StageTrace
from app.core.realtime_translation_session import RealtimeTranslationSession
from app.core.session_context import SessionContext
from app.core.streaming_speech_chunk import StreamingSpeechChunk
from app.core.streaming_transcription_session import StreamingTranscriptionSession
from app.core.streaming_translation_chunk import StreamingTranslationChunk
from app.pipelines.pipeline import Pipeline
from app.pipelines.pipeline_stage import PipelineStage
from app.pipelines.pipeline_state import PipelineState
from app.pipelines.sequential_pipeline import SequentialPipeline
from app.providers.contracts.realtime_translation_provider import RealtimeTranslationProvider
from app.providers.contracts.streaming_speech_provider import StreamingSpeechProvider
from app.providers.contracts.streaming_transcription_provider import StreamingTranscriptionProvider
from app.providers.contracts.streaming_translation_provider import StreamingTranslationProvider
from app.providers.speech_provider import SpeechProvider
from app.providers.speech_to_text_provider import SpeechToTextProvider
from app.providers.translation_provider import TranslationProvider
from app.registry.agent_registry import AgentRegistry
from app.registry.pipeline_registry import PipelineRegistry
from app.registry.provider_registry import ProviderRegistry

__all__ = [
    "AgentInput", "AgentRegistry", "AgentResult", "BaseAgent",
    "ExecutionTrace", "Pipeline", "PipelineRegistry", "PipelineStage",
    "PipelineState", "ProviderRegistry", "RealtimeTranslationProvider",
    "RealtimeTranslationSession", "SequentialPipeline", "SessionContext",
    "SpeechProvider", "SpeechToTextProvider", "StageTrace",
    "StreamingSpeechChunk", "StreamingSpeechProvider",
    "StreamingTranscriptionProvider", "StreamingTranscriptionSession",
    "StreamingTranslationChunk", "StreamingTranslationProvider", "TranslationProvider",
]
