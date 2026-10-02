import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app.observability.context import bound, fields, request_id
from app.observability.events import emit, logger, EventFormatter
from app.observability.middleware import ObservabilityMiddleware
from app.observability.operations import observe, record_usage
from app.sessions.session_manager import SessionManager
from app.sessions.sqlite_session_repository import SQLiteSessionRepository


@pytest.fixture
def events(caplog, monkeypatch):
    monkeypatch.setattr(logger, 'propagate', True)
    return caplog


def records(events, name):
    return [r.event_data for r in events.records if hasattr(r, 'event_data') and r.event_data['event'] == name]


@pytest.mark.parametrize('value', ['', '../escape', 'x'*129, 'café', 'bad\nheader', 'a/b'])
def test_invalid_correlation_id_is_regenerated(value):
    from uuid import UUID
    generated = request_id(value)
    UUID(generated)
    assert generated != value


@pytest.mark.parametrize('value', ['req-1', 'A_2026.1', 'a'*128])
def test_valid_correlation_id_is_preserved(value):
    assert request_id(value) == value


def test_allowlist_never_serializes_content_or_secrets(events):
    with bound(request_id='req-privacy', session_id='s-1'):
        emit('test.event', status='success', text='SECRET_TEXT', api_key='SECRET_KEY', audio=b'SECRET_AUDIO', error=ValueError('SECRET_ERROR'))
    data = records(events, 'test.event')[0]
    output = json.dumps(data)
    assert 'SECRET' not in output
    assert data['request_id'] == 'req-privacy'
    assert fields() == {}
    record = next(r for r in events.records if hasattr(r, 'event_data'))
    assert json.loads(EventFormatter().format(record)) == data


@pytest.mark.asyncio
async def test_concurrent_requests_keep_separate_contexts(events):
    app = FastAPI()
    app.add_middleware(ObservabilityMiddleware)
    @app.get('/work/{session}')
    async def work(session: str):
        from app.observability.context import enrich
        enrich(session_id=session)
        await asyncio.sleep(.01)
        return fields()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        responses = await asyncio.gather(*[client.get('/work/'+session, headers={'X-Request-Id': 'req-'+session}) for session in ['one', 'two']])
    assert [r.json()['session_id'] for r in responses] == ['one', 'two']
    assert [r.headers['X-Request-Id'] for r in responses] == ['req-one', 'req-two']
    assert all(r['route'] == '/work/{session}' for r in records(events, 'request.completed'))
    assert fields() == {}


def test_correlation_on_auth_and_validation_errors(events):
    from app.main import app
    with TestClient(app) as client:
        response = client.post('/api/sessions', json={}, headers={'X-Request-Id': 'req-auth'})
        assert response.status_code == 401
        assert response.headers['X-Request-Id'] == 'req-auth'
        response = client.post('/api/sessions', json={'agent_type': ''}, headers={'X-Client-Id': 'owner', 'X-Request-Id': 'req-invalid'})
        assert response.status_code == 422
    failures = records(events, 'request.completed')
    assert any(r['error_type'] == 'CLIENT_ID_REQUIRED' for r in failures)
    assert any(r['error_type'] == 'REQUEST_VALIDATION_ERROR' for r in failures)


def test_server_error_has_correlation_and_never_logs_exception_text(events):
    from app.api.error_handlers import register_exception_handlers
    app = FastAPI()
    register_exception_handlers(app)
    app.add_middleware(ObservabilityMiddleware)
    @app.get('/fail')
    async def fail():
        raise RuntimeError('SECRET_PROVIDER_CONTENT')
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/fail', headers={'X-Request-Id': 'req-fail'})
    assert response.status_code == 500
    assert response.headers['X-Request-Id'] == 'req-fail'
    assert 'SECRET_PROVIDER_CONTENT' not in events.text


@pytest.mark.asyncio
async def test_provider_failure_is_counted_and_content_is_absent(events):
    labels = {'provider': 'openai', 'operation': 'translation', 'error_type': 'provider_error'}
    before = REGISTRY.get_sample_value('waaxalma_provider_errors_total', labels) or 0
    @observe('translation', model='test-model')
    async def fail():
        raise ValueError('PRIVATE_PROVIDER_TEXT')
    with bound(request_id='req-provider', session_id='session-provider', execution_mode='standard', source_language='fr', target_language='en'):
        with pytest.raises(ValueError):
            await fail()
    event = records(events, 'provider.completed')[-1]
    assert event['session_id'] == 'session-provider'
    assert event['model'] == 'test-model'
    assert event['status'] == 'error'
    assert 'PRIVATE_PROVIDER_TEXT' not in events.text
    assert REGISTRY.get_sample_value('waaxalma_provider_errors_total', labels) == before + 1


@pytest.mark.asyncio
async def test_cancelled_provider_is_not_an_error_or_swallowed(events):
    @observe('tts')
    async def cancel():
        raise asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await cancel()
    assert records(events, 'provider.completed')[-1]['status'] == 'cancelled'


@pytest.mark.asyncio
async def test_stream_partial_close_restores_context_and_records_cancellation(events):
    closed = []
    @observe('translation', model='stream-model')
    async def stream():
        try:
            yield 'private chunk'
            yield 'another private chunk'
        finally:
            closed.append(True)
    with bound(request_id='req-stream'):
        iterator = stream()
        assert await anext(iterator) == 'private chunk'
        assert fields() == {'request_id': 'req-stream'}
        await iterator.aclose()
        assert fields() == {'request_id': 'req-stream'}
    assert closed == [True]
    assert records(events, 'provider.completed')[-1]['status'] == 'cancelled'
    assert 'private chunk' not in events.text


@pytest.mark.asyncio
async def test_completed_stream_records_one_logical_call(events):
    @observe('tts', model='stream-model')
    async def stream():
        yield b'audio1'
        yield b'audio2'
    assert [chunk async for chunk in stream()] == [b'audio1', b'audio2']
    assert len(records(events, 'provider.completed')) == 1
    assert records(events, 'provider.completed')[0]['status'] == 'success'


def test_active_sessions_survive_repository_restart_and_close_is_idempotent(tmp_path):
    repo = SQLiteSessionRepository(tmp_path/'sessions.db')
    service = SessionManager(repo)
    session = service.create_session('interpreter', owner_id='owner')
    restarted = SessionManager(SQLiteSessionRepository(repo.database_path))
    assert restarted.repository.count_active() == 1
    labels = {'execution_mode': 'standard'}
    before = REGISTRY.get_sample_value('waaxalma_session_duration_seconds_count', labels) or 0
    restarted.close_session(session.session_id)
    restarted.close_session(session.session_id)
    assert restarted.repository.count_active() == 0
    assert REGISTRY.get_sample_value('waaxalma_session_duration_seconds_count', labels) == before+1


def test_metrics_scrape_does_not_recreate_removed_database(tmp_path, monkeypatch):
    from app.bootstrap import container
    from app.observability.metrics_endpoint import ActiveSessionsCollector
    repo = SQLiteSessionRepository(tmp_path/'sessions.db')
    monkeypatch.setattr(container, 'session_manager', SessionManager(repo))
    repo.database_path.unlink()
    samples = [sample for metric in ActiveSessionsCollector().collect() for sample in metric.samples]
    assert not repo.database_path.exists()
    assert not any(s.name == 'waaxalma_sessions_active' for s in samples)
    assert next(s.value for s in samples if s.name == 'waaxalma_sessions_scrape_error') == 1


def test_usage_is_reported_only_when_available_and_cost_requires_rates(events, monkeypatch):
    from app.core import settings
    monkeypatch.setattr(settings, 'get_settings', lambda: SimpleNamespace(provider_token_prices_usd_per_million={'test': {'input': 2, 'output': 4}}))
    record_usage(None, model='test')
    assert records(events, 'provider.usage') == []
    record_usage({'input_tokens': 100, 'output_tokens': 50}, model='test')
    event = records(events, 'provider.usage')[-1]
    assert event['estimated_cost_usd'] == pytest.approx(.0004)
    record_usage({'input_tokens': 100}, model='test')
    assert 'estimated_cost_usd' not in records(events, 'provider.usage')[-1]
    record_usage({'input_tokens': 100, 'output_tokens': 50}, model='unknown')
    assert 'estimated_cost_usd' not in records(events, 'provider.usage')[-1]


@pytest.mark.parametrize('rates', [{'x': {'input': -1, 'output': 0}}, {'x': {'input': 1}}, {'x': {'input': float('inf'), 'output': 1}}])
def test_bad_cost_configuration_is_rejected(rates):
    from app.core.settings import Settings
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Settings(app_env='test', provider_token_prices_usd_per_million=rates)


def test_api_body_and_provider_event_share_request_id(events, monkeypatch):
    from app.main import app
    from app.providers.openai_provider import OpenAITranslationProvider
    async def translate(self, text, target_language):
        return 'translated private text'
    monkeypatch.setattr(OpenAITranslationProvider, '_translate_once', translate)
    with TestClient(app) as client:
        response = client.post('/api/text/translate', json={'text': 'private input', 'target_language': 'English'}, headers={'X-Client-Id': 'owner', 'X-Request-Id': 'req-translation'})
    assert response.status_code == 200
    assert response.json()['request_id'] == response.headers['X-Request-Id'] == 'req-translation'
    event = records(events, 'provider.completed')[-1]
    assert event['request_id'] == 'req-translation'
    assert event['target_language'] == 'English'
    assert 'private input' not in events.text and 'translated private text' not in events.text


def test_new_metrics_exclude_identifiers_and_languages():
    from app.observability import production_metrics as m
    for metric in [m.HTTP_REQUESTS,m.HTTP_LATENCY,m.PROVIDER_CALLS,m.PROVIDER_ERRORS,m.PROVIDER_LATENCY,m.SESSION_EVENTS,m.SESSION_DURATION,m.TOKENS,m.COST]:
        assert not {'request_id','session_id','source_language','target_language','client_id','model'} & set(metric._labelnames)


@pytest.mark.asyncio
async def test_reused_request_id_never_reuses_audio_filename():
    from unittest.mock import AsyncMock
    from app.pipelines.stages.speech_stage import SpeechStage
    from app.pipelines.pipeline_state import PipelineState
    from app.core.session_context import SessionContext
    skill = SimpleNamespace(provider_name='fake', execute=AsyncMock())
    stage = SpeechStage(skill)
    outputs = []
    with bound(request_id='reused-id'):
        for _ in range(2):
            state = PipelineState(data={'agent_name':'interpreter', 'request_id':'reused-id', 'interpreted_text':'private text'})
            result = await stage.execute(state=state, context=SessionContext())
            outputs.append(result.require('audio_url'))
    assert outputs[0] != outputs[1]
    assert all('reused-id' not in url for url in outputs)


def test_compose_empty_optional_values_are_valid(monkeypatch):
    from app.core.settings import Settings
    monkeypatch.setenv('PROVIDER_TOKEN_PRICES_USD_PER_MILLION', '')
    monkeypatch.setenv('OTEL_EXPORTER_OTLP_TRACES_ENDPOINT', '')
    config = Settings(app_env='test')
    assert config.provider_token_prices_usd_per_million == {}
    assert config.otel_exporter_otlp_traces_endpoint is None
