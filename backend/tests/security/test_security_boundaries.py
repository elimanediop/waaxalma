from contextlib import closing
import sqlite3

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.bootstrap import container
from app.api import sessions, interpreter, voice, text
from app.security.client_identity import ClientIdentity, ClientIdentityError
from app.security.security_context import SecurityContext
from app.security.session_access_policy import SessionAccessPolicy, SessionAccessDeniedError
from app.sessions.session_manager import SessionManager
from app.sessions.session_models import ConversationSession
from app.sessions.sqlite_session_repository import SQLiteSessionRepository


@pytest.fixture
def service(monkeypatch):
    manager = SessionManager()
    for module in (container, sessions, interpreter, voice, text):
        monkeypatch.setattr(module, 'session_manager', manager)
    return manager


@pytest.fixture
def owned(service):
    return service.create_session('interpreter', owner_id='client-a')


@pytest.mark.parametrize('value', ['', ' leading', 'trailing ', 'a b', 'a/b', 'é', 'a'*129, None, 'a\n'])
def test_invalid_identity(value):
    with pytest.raises(ClientIdentityError):
        ClientIdentity(value)


@pytest.mark.parametrize('value', ['a', 'desktop-waaxalma', 'client_1.0', 'a'*128])
def test_valid_identity(value):
    assert ClientIdentity(value).client_id == value


def test_policy_rejects_other_client_and_legacy():
    context = SecurityContext(ClientIdentity('client-a'))
    for owner in (None, 'client-b'):
        session = ConversationSession.create('interpreter', owner_id=owner)
        with pytest.raises(SessionAccessDeniedError):
            SessionAccessPolicy.require_access(context=context, session=session)


@pytest.mark.parametrize('header', [None, '', 'with spaces', 'a'*129])
def test_missing_or_invalid_header(service, owned, header):
    headers = {} if header is None else {'X-Client-Id': header}
    with TestClient(app) as client:
        response = client.get('/api/sessions/'+owned.session_id, headers=headers)
    assert response.status_code == 401


def test_create_binds_owner_and_lifecycle(service):
    with TestClient(app, headers={'X-Client-Id': 'client-a'}) as client:
        created = client.post('/api/sessions', json={'agent_type': 'interpreter'})
        assert created.status_code == 200, created.text
        sid = created.json()['session_id']
        assert service.get_session(sid).owner_id == 'client-a'
        assert client.get('/api/sessions/'+sid).json()['owner_id'] == 'client-a'
        assert client.patch('/api/sessions/'+sid, json={'target_language': 'French'}).status_code == 200
        assert client.post('/api/sessions/'+sid+'/close').status_code == 200
        assert client.post('/api/sessions/'+sid+'/close').status_code == 200
        assert client.patch('/api/sessions/'+sid, json={'target_language': 'English'}).status_code == 409
        assert client.get('/api/sessions/missing').status_code == 404


@pytest.mark.parametrize('operation', ['get', 'patch', 'close', 'interpret', 'voice', 'agent', 'agent-payload', 'translate', 'speak', 'translate-and-speak'])
def test_cross_client_blocked_before_processing(service, owned, operation):
    sid = owned.session_id
    with TestClient(app, headers={'X-Client-Id': 'client-b'}) as client:
        if operation == 'get':
            response = client.get('/api/sessions/'+sid)
        elif operation == 'patch':
            response = client.patch('/api/sessions/'+sid, json={'target_language':'French'})
        elif operation == 'close':
            response = client.post('/api/sessions/'+sid+'/close')
        elif operation == 'interpret':
            response = client.post('/api/interpreter/interpret', json={'text':'hello','session_id':sid})
        elif operation == 'voice':
            response = client.post('/api/voice/interpret', data={'session_id':sid}, files={'file':('audio.wav', b'bad-audio','audio/wav')})
        elif operation.startswith('agent'):
            response = client.post('/api/agents/interpreter/execute', json={
                'operation':'interpret','session_id':sid if operation=='agent' else 'transient',
                'payload':{'text':'hello','session_id':sid}})
        else:
            response = client.post('/api/text/'+operation, json={'text':'hello','session_id':sid, 'target_language':'English'})
    assert response.status_code == 403, response.text
    assert response.json()['detail']['code'] == 'SESSION_ACCESS_DENIED'
    assert service.get_session(sid).is_active
    assert service.get_session(sid).history == []


def test_legacy_and_closed_foreign_sessions_stay_denied(service, owned):
    legacy = service.create_session('interpreter')
    service.close_session(owned.session_id)
    with TestClient(app, headers={'X-Client-Id':'client-b'}) as client:
        for sid in (legacy.session_id, owned.session_id):
            assert client.get('/api/sessions/'+sid).status_code == 403
            assert client.post('/api/interpreter/interpret',json={'text':'hello','session_id':sid}).status_code == 403


def test_websocket_missing_identity():
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect('/api/realtime/enhanced/stream'):
                pass
    assert exc.value.code == 1008


def test_sqlite_ownership_survives_restart_and_update(tmp_path):
    path = tmp_path/'sessions.db'
    repo = SQLiteSessionRepository(path)
    session = repo.create(ConversationSession.create('interpreter', owner_id='client-a'))
    session.target_language = 'French'
    # Ownership is immutable on ordinary repository updates.
    session.owner_id = 'client-b'
    repo.update(session)
    restarted = SQLiteSessionRepository(path)
    assert restarted.get(session.session_id).owner_id == 'client-a'
    assert restarted.get(session.session_id).target_language == 'French'


def test_slice1_migration_preserves_unowned_history(tmp_path):
    path=tmp_path/'legacy.db'
    with closing(sqlite3.connect(path)) as db, db:
        db.execute('''CREATE TABLE sessions (
            session_id TEXT PRIMARY KEY, agent_name TEXT NOT NULL,
            execution_mode TEXT NOT NULL, source_language TEXT NOT NULL,
            target_language TEXT NOT NULL, status TEXT NOT NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL, closed_at TEXT,
            metadata_json TEXT NOT NULL)''')
        db.execute("INSERT INTO sessions VALUES ('legacy','interpreter','standard','auto','English','active','2026-01-01T00:00:00+00:00','2026-01-01T00:00:00+00:00',NULL,'{}')")
    repo=SQLiteSessionRepository(path)
    repo.append_message('legacy', {'role':'user','content':'hello','timestamp':'2026-01-01T00:00:00+00:00'},updated_at='2026-01-01T00:00:00+00:00')
    for _ in range(2):
        repo=SQLiteSessionRepository(path)
        session=repo.get('legacy')
        assert session.owner_id is None
        assert session.history[0]['content']=='hello'
    repo.create(ConversationSession.create('interpreter',owner_id='client-a'))
    with closing(sqlite3.connect(path)) as db, db:
        assert db.execute('PRAGMA user_version').fetchone()[0]==2


@pytest.mark.parametrize('query', [False, True])
def test_websocket_foreign_persistent_session(service, owned, monkeypatch, query):
    from app.api import realtime
    monkeypatch.setattr(realtime, '_get_realtime_enhanced_service', lambda: object())
    headers = {} if query else {'X-Client-Id':'client-b'}
    url = '/api/realtime/enhanced/stream' + ('?client_id=client-b' if query else '')
    with TestClient(app) as client:
        with client.websocket_connect(url, headers=headers) as ws:
            ws.send_json({'type':'session.start', 'target_language':'English','session_id':owned.session_id})
            assert ws.receive_json()['code'] == 'SESSION_ACCESS_DENIED'
            with pytest.raises(WebSocketDisconnect) as exc:
                ws.receive_json()
            assert exc.value.code == 1008
    assert service.get_session(owned.session_id).history == []


def test_websocket_conflicting_identity():
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect('/api/realtime/enhanced/stream?client_id=client-b', headers={'X-Client-Id':'client-a'}):
                pass
        assert exc.value.code == 1008


def test_same_owner_interpretation_preserves_history(service, owned, monkeypatch):
    from app.core.agent_result import AgentResult

    class FakeOrchestrator:
        async def execute(self, *, agent_name, agent_input, context):
            assert context.session_id == owned.session_id
            return AgentResult(success=True, output={
                'request_id':'fake-request','session_id':owned.session_id,
                'agent':'interpreter','source_text':'hello','interpreted_text':'bonjour',
                'audio_url':'/static/audio/fake.mp3'})

    monkeypatch.setattr(interpreter, 'agent_orchestrator', FakeOrchestrator())
    with TestClient(app, headers={'X-Client-Id':'client-a'}) as client:
        response=client.post('/api/interpreter/interpret',json={'text':'hello','session_id':owned.session_id})
        assert response.status_code == 200, response.text
    assert [m['content'] for m in service.get_session(owned.session_id).history] == ['hello','bonjour']


@pytest.mark.parametrize('endpoint,body', [
    ('/api/sessions', {}),
    ('/api/interpreter/interpret', {'text':'hello'}),
    ('/api/agents/interpreter/execute', {'operation':'interpret','session_id':'transient','payload':{}}),
    ('/api/text/translate', {'text':'hello'}),
    ('/api/text/speak', {'text':'hello'}),
    ('/api/text/translate-and-speak', {'text':'hello'}),
    ('/api/realtime/translation/session', {'target_language':'English'}),
    ('/api/realtime/enhanced/session', {'target_language':'English'}),
])
def test_processing_endpoints_require_identity(service, endpoint, body):
    with TestClient(app) as client:
        assert client.post(endpoint,json=body).status_code==401


def test_memory_ownership_immutable(service, owned):
    owned.owner_id='client-b'
    service.repository.update(owned)
    assert service.get_session(owned.session_id).owner_id=='client-a'


def test_legacy_owner_assignment_is_explicit_and_once(tmp_path, monkeypatch):
    from scripts.assign_session_owner import main
    path=tmp_path/'legacy.db'
    repo=SQLiteSessionRepository(path)
    session=repo.create(ConversationSession.create('interpreter'))
    monkeypatch.setattr('sys.argv', ['assign_session_owner', '--database', str(path), '--session-id', session.session_id, '--client-id', 'client-a'])
    main()
    assert repo.get(session.session_id).owner_id=='client-a'
    with pytest.raises(SystemExit):
        main()
    assert repo.get(session.session_id).owner_id=='client-a'
