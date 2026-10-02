from pathlib import Path
import pytest
from pydantic import ValidationError
from app.core.settings import Settings, get_settings


def test_test_environment_is_explicit_and_memory_by_default(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('SESSION_STORAGE_BACKEND', raising=False)
    settings=Settings(app_env='test', _env_file=None)
    assert settings.session_storage_backend=='memory'
    assert settings.openai_api_key.get_secret_value()=='test-key-not-for-provider-calls'


@pytest.mark.parametrize('mode', ['development','production'])
def test_real_environments_require_provider_key(monkeypatch,mode):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    with pytest.raises(ValidationError,match='OPENAI_API_KEY is required'):
        Settings(app_env=mode,_env_file=None)


@pytest.mark.parametrize('field,value', [('app_env','stage'),('port',0),('port',65536),
    ('session_storage_backend','postgres'),('provider_max_attempts',0),('tts_timeout_seconds',0),
    ('provider_jitter_ratio',1.1),('cors_origins',['*']),('translation_provider','unknown')])
def test_invalid_settings_are_rejected(field,value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None,**{field:value})


def test_production_cannot_use_ephemeral_storage():
    with pytest.raises(ValidationError,match='Production requires persistent'):
        Settings(app_env='production',openai_api_key='private-test-key',session_storage_backend='memory',_env_file=None)


def test_relative_paths_resolve_from_working_directory(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    settings=Settings(app_env='test', data_dir='store',static_dir='audio-assets',upload_dir='uploads',_env_file=None)
    assert settings.session_db_path==tmp_path/'store/waaxalma_sessions.sqlite3'
    assert settings.static_dir==tmp_path/'audio-assets'


def test_errors_and_repr_do_not_disclose_secret():
    secret='private-test-secret-for-validation'
    with pytest.raises(ValidationError) as exc:
        Settings(app_env='production',openai_api_key=secret,session_storage_backend='memory',_env_file=None)
    assert secret not in str(exc.value)
    settings=Settings(app_env='production',openai_api_key=secret,_env_file=None)
    assert secret not in repr(settings)


def test_streaming_defaults_follow_standard_models():
    settings=Settings(openai_translation_model='custom-model',openai_tts_model='custom-tts',openai_tts_voice='custom-voice',_env_file=None)
    assert settings.streaming_translation_model=='custom-model'
    assert settings.streaming_speech_model=='custom-tts'
    assert settings.streaming_speech_voice=='custom-voice'


def test_development_dotenv_and_environment_precedence(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path/'.env').write_text('OPENAI_API_KEY=dotenv-test-key\nPORT=8888\n')
    monkeypatch.setenv('APP_ENV','development')
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    monkeypatch.setenv('PORT','8999')
    get_settings.cache_clear()
    try:
        settings=get_settings()
        assert settings.openai_api_key.get_secret_value()=='dotenv-test-key'
        assert settings.port==8999
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize('mode',['test','production'])
def test_non_development_never_loads_dotenv(tmp_path,monkeypatch,mode):
    monkeypatch.chdir(tmp_path)
    (tmp_path/'.env').write_text('OPENAI_API_KEY=dotenv-test-key\nPORT=8888\n')
    monkeypatch.setenv('APP_ENV',mode)
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    get_settings.cache_clear()
    try:
        if mode=='production':
            with pytest.raises(ValidationError): get_settings()
        else:
            assert get_settings().port==8000
    finally:
        get_settings.cache_clear()


@pytest.mark.parametrize('field,value', [('tts_timeout_seconds',float('nan')),('provider_max_backoff_seconds',float('inf'))])
def test_nonfinite_retry_values_rejected(field,value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None,**{field:value})


def test_retry_backoff_consistency_validated_centrally():
    with pytest.raises(ValidationError,match='PROVIDER_MAX_BACKOFF_SECONDS'):
        Settings(provider_initial_backoff_seconds=5,provider_max_backoff_seconds=1,_env_file=None)
