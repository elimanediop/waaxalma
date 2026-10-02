# Environment reference — v0.5.0 Slice 3

Names are case-insensitive. Settings are cached once per process; restart to apply changes.

| Backend variable | Default |
|---|---|
| APP_ENV | `development` |
| OPENAI_API_KEY | `derived; see notes below` |
| HOST | `0.0.0.0` |
| PORT | `8000` |
| LOG_LEVEL | `info` |
| CORS_ORIGINS | `explicit localhost origins (see .env.example)` |
| DATA_DIR | `data` |
| STATIC_DIR | `static` |
| UPLOAD_DIR | `tmp/uploads` |
| SESSION_STORAGE_BACKEND | `derived; see notes below` |
| SESSION_DB_PATH | `derived; see notes below` |
| TRANSLATION_PROVIDER | `openai` |
| SPEECH_PROVIDER | `openai` |
| SPEECH_TO_TEXT_PROVIDER | `openai` |
| CONTEXT_PROVIDER | `passthrough` |
| QUALITY_PROVIDER | `deterministic` |
| REALTIME_TRANSLATION_PROVIDER | `openai` |
| STREAMING_TRANSCRIPTION_PROVIDER | `openai` |
| STREAMING_TRANSLATION_PROVIDER | `openai` |
| STREAMING_SPEECH_PROVIDER | `openai` |
| OPENAI_TRANSLATION_MODEL | `gpt-4.1-mini` |
| OPENAI_TTS_MODEL | `gpt-4o-mini-tts` |
| OPENAI_TTS_VOICE | `coral` |
| SPEECH_VOICE | `marin` |
| OPENAI_TRANSCRIPTION_MODEL | `gpt-4o-transcribe` |
| REALTIME_TRANSLATION_MODEL | `gpt-realtime-translate` |
| REALTIME_TRANSLATION_VOICE | `marin` |
| STREAMING_TRANSCRIPTION_MODEL | `gpt-live-transcribe` |
| STREAMING_TRANSLATION_MODEL | `derived; see notes below` |
| STREAMING_SPEECH_MODEL | `derived; see notes below` |
| STREAMING_SPEECH_VOICE | `derived; see notes below` |
| PROVIDER_MAX_ATTEMPTS | `3` |
| PROVIDER_INITIAL_BACKOFF_SECONDS | `0.5` |
| PROVIDER_BACKOFF_MULTIPLIER | `2.0` |
| PROVIDER_MAX_BACKOFF_SECONDS | `4.0` |
| PROVIDER_JITTER_RATIO | `0.2` |
| STT_TIMEOUT_SECONDS | `30.0` |
| TRANSLATION_TIMEOUT_SECONDS | `20.0` |
| TTS_TIMEOUT_SECONDS | `30.0` |

## Backend rules

- APP_ENV: development, test, production only. Default development.
- OPENAI_API_KEY: required for development/production; nonblank. Test mode uses a dummy value when missing.
- SESSION_STORAGE_BACKEND: sqlite for development/production, memory for test when unset. Production rejects memory.
- Paths: expand ~ and resolve relative to process cwd. SESSION_DB_PATH defaults to DATA_DIR/waaxalma_sessions.sqlite3.
- STREAMING_TRANSLATION_MODEL follows OPENAI_TRANSLATION_MODEL when unset. STREAMING_SPEECH_MODEL/VOICE follow OPENAI_TTS_MODEL/VOICE.
- Provider choices are the implementations currently registered: openai, passthrough context, deterministic quality.
- CORS_ORIGINS is a JSON array of explicit HTTP(S) origins, without paths or wildcard. [] is permitted to disable cross-origin browser access.
- PORT: 1–65535. Timeouts: finite and positive. Attempts: 1–10. Backoffs: nonnegative, multiplier >=1, maximum >= initial. Jitter: 0–1.
- HOST/PORT apply to waaxalma-backend. If invoking uvicorn manually, pass its host/port flags explicitly.
- Production/test auto-dotenv loading is disabled. The process APP_ENV selects the mode; export it explicitly.
- Provider API keys are never sent to the UI through this configuration.

## UI variables

| Variable | Native default | Compose value |
|---|---|---|
| BACKEND_API_URL | http://127.0.0.1:8000 | http://backend:8000 |
| PUBLIC_BACKEND_URL | http://127.0.0.1:8000 | http://localhost:8000 |
| CLIENT_ID | waaxalma-for-elimane | same, configurable |
| REQUEST_TIMEOUT_SECONDS | 120 | same, configurable |

URL values require HTTP(S), with no credentials, query or fragment. CLIENT_ID
uses Slice 2 validation (1–128 ASCII alphanumeric/dot/underscore/hyphen, starts
alphanumeric). Request timeout must be finite and positive. UISettings is in
streamlit/config.py; backend Settings is in app/core/settings.py.

## Compose interpolation

The root .env supplies OPENAI_API_KEY, CLIENT_ID, PUBLIC_BACKEND_URL, BACKEND_PORT,
UI_PORT, LOG_LEVEL, CORS_ORIGINS, REQUEST_TIMEOUT_SECONDS and provider/model/retry
knobs. Compose assigns APP_ENV=production, container port 8000 and internal state
paths. Other custom paths/ports can be supplied for standalone docker run or
by explicitly editing Compose. Backend/streamlit .env.example files are for
native runs; Compose does not automatically mount those files.
