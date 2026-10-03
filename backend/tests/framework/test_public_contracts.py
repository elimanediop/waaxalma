"""Compatibility boundary: identity, signatures, data shape and safe imports."""
import importlib
import inspect
import os
import subprocess
import sys

import pytest

from app import framework


ORIGINS = {
    "BaseAgent": "app.agents.base_agent",
    "AgentInput": "app.core.agent_input",
    "AgentResult": "app.core.agent_result",
    "SessionContext": "app.core.session_context",
    "ExecutionTrace": "app.core.execution_trace",
    "StageTrace": "app.core.execution_trace",
    "RealtimeTranslationSession": "app.core.realtime_translation_session",
    "StreamingTranscriptionSession": "app.core.streaming_transcription_session",
    "StreamingTranslationChunk": "app.core.streaming_translation_chunk",
    "StreamingSpeechChunk": "app.core.streaming_speech_chunk",
    "Pipeline": "app.pipelines.pipeline",
    "PipelineStage": "app.pipelines.pipeline_stage",
    "PipelineState": "app.pipelines.pipeline_state",
    "SequentialPipeline": "app.pipelines.sequential_pipeline",
    "TranslationProvider": "app.providers.translation_provider",
    "SpeechProvider": "app.providers.speech_provider",
    "SpeechToTextProvider": "app.providers.speech_to_text_provider",
    "RealtimeTranslationProvider": "app.providers.contracts.realtime_translation_provider",
    "StreamingTranscriptionProvider": "app.providers.contracts.streaming_transcription_provider",
    "StreamingTranslationProvider": "app.providers.contracts.streaming_translation_provider",
    "StreamingSpeechProvider": "app.providers.contracts.streaming_speech_provider",
    "AgentRegistry": "app.registry.agent_registry",
    "PipelineRegistry": "app.registry.pipeline_registry",
    "ProviderRegistry": "app.registry.provider_registry",
}


def test_public_surface_is_explicit():
    assert set(framework.__all__) == set(ORIGINS)
    assert len(framework.__all__) == len(ORIGINS)


@pytest.mark.parametrize("name,module", ORIGINS.items())
def test_legacy_imports_keep_class_identity(name, module):
    assert getattr(framework, name) is getattr(importlib.import_module(module), name)


@pytest.mark.parametrize("name,method,parameters,is_async", [
    ("BaseAgent", "execute", "self agent_input context", True),
    ("Pipeline", "execute", "self state context", True),
    ("PipelineStage", "execute", "self state context", True),
    ("TranslationProvider", "translate", "self text target_language", True),
    ("SpeechProvider", "speak", "self text output_filename", True),
    ("SpeechToTextProvider", "transcribe", "self audio_path", True),
    ("RealtimeTranslationProvider", "create_session", "self target_language", True),
    ("StreamingTranscriptionProvider", "create_session", "self languages prompt keywords delay", True),
    ("StreamingTranslationProvider", "translate_stream", "self text target_language context terminology", False),
    ("StreamingSpeechProvider", "speak_stream", "self text voice_id instructions", False),
])
def test_extension_calling_conventions(name, method, parameters, is_async):
    function = getattr(getattr(framework, name), method)
    signature = inspect.signature(function)
    assert list(signature.parameters) == parameters.split()
    assert inspect.iscoroutinefunction(function) is is_async
    for parameter in list(signature.parameters.values())[1:]:
        expected = (inspect.Parameter.KEYWORD_ONLY if name in {
            "RealtimeTranslationProvider", "StreamingTranscriptionProvider",
            "StreamingTranslationProvider", "StreamingSpeechProvider",
        } else inspect.Parameter.POSITIONAL_OR_KEYWORD)
        assert parameter.kind == expected


def test_agent_model_defaults_and_serialization():
    first = framework.AgentInput(operation="echo")
    second = framework.AgentInput(operation="echo")
    first.payload["text"] = "bonjour"
    assert second.payload == {}
    assert second.model_dump() == {"operation": "echo", "payload": {}, "metadata": {}}
    assert framework.AgentResult(success=True).model_dump() == {
        "success": True, "output": None, "error_code": None,
        "error_message": None, "duration_ms": None, "metadata": {},
    }
    context = framework.SessionContext()
    assert context.created_at.utcoffset().total_seconds() == 0
    assert context.session_id != framework.SessionContext().session_id
    context.trace.stages.clear()
    assert framework.SessionContext().trace.stages == []


def test_optional_provider_defaults():
    contracts = [
        (framework.StreamingTranscriptionProvider.create_session,
         {"languages": None, "prompt": None, "keywords": None, "delay": "low"}),
        (framework.StreamingTranslationProvider.translate_stream,
         {"context": None, "terminology": None}),
        (framework.StreamingSpeechProvider.speak_stream, {"instructions": None}),
    ]
    for function, expected in contracts:
        signature = inspect.signature(function)
        actual = {
            name: parameter.default for name, parameter in signature.parameters.items()
            if parameter.default is not inspect.Parameter.empty
        }
        assert actual == expected


def test_framework_import_needs_no_runtime_configuration():
    environment = os.environ.copy()
    environment.update(APP_ENV="invalid-for-runtime", OPENAI_API_KEY="", PYTHONDONTWRITEBYTECODE="1")
    # Run in a fresh interpreter: other API tests may already import bootstrap.
    code = """
import sys
import app.framework
assert 'app.main' not in sys.modules
assert 'app.bootstrap.container' not in sys.modules
assert 'app.core.settings' not in sys.modules
assert 'openai' not in sys.modules
"""
    subprocess.run([sys.executable, "-c", code], env=environment, check=True)
