# Waaxalma v1.2.0 — Slice 1: Architecture & Data Model

Status: **Proposed — design only**. Baseline: released v1.1.1. No runtime changes in this slice.

## Scope and decisions

- Web: **Next.js / React / TypeScript**; FastAPI remains the sole business API and owns identity, translation orchestration, persistence and provider credentials.
- Data: **PostgreSQL** as target transactional store, **SQLAlchemy 2.x + Alembic** proposed for migration management; verify current persistence abstractions before implementation.
- Auth: local accounts with Argon2id password hashes, verified email, server-side opaque sessions in PostgreSQL, Secure/HttpOnly/SameSite cookies, CSRF protection for cookie-authenticated mutations. No OAuth/OIDC/JWT or IAM platform required.
- Security: browser never supplies an authoritative user/owner ID. Resolve identity from authenticated session on every HTTP/WebSocket operation. Deny access across users with consistent 404/403 policy and audit logs without secrets.
- Audio: browser-side device enumeration, WebRTC, CABLE-A/B routing and Conference Monitor must be preserved; Next.js cannot access devices on the server. Device IDs are browser-local and should not be assumed portable.
- Existing Standard, Direct, Enhanced, Text Translation and Full Duplex behaviors remain release compatibility contracts.

## Proposed topology

```text
Browser (Next.js, HTTPS)
  ├── login / settings / text translation
  └── browser audio, WebRTC, Conference Monitor, Direct / Enhanced
           │ HTTPS + WSS / WebRTC signalling
           ▼
Reverse proxy (Caddy)
  ├── Next.js (web)
  └── FastAPI (api) ── PostgreSQL (private network)
                   └── external STT / LLM / TTS providers
```

Keep existing Streamlit UI running for parity during migration; do not publicly expose it without a deliberate access policy. Docker Compose service names proposed: `web`, `backend`, `postgres`, `caddy`; optional observability remains private.

## Proposed initial data model

| Table | Main fields | Notes |
|---|---|---|
| `users` | `id UUID PK`, `email_normalized UNIQUE`, `password_hash`, `email_verified_at`, `status`, timestamps | Do not store raw passwords |
| `auth_sessions` | `id UUID PK`, `user_id FK`, `token_hash UNIQUE`, `expires_at`, `revoked_at`, `created_at`, `last_seen_at` | Only hashed opaque session token at rest |
| `email_verification_tokens` | `id`, `user_id`, `token_hash`, `expires_at`, `used_at` | Single-use and expiring |
| `password_reset_tokens` | `id`, `user_id`, `token_hash`, `expires_at`, `used_at` | Single-use and expiring |
| `translation_sessions` | `id`, `user_id FK`, `mode`, `state`, `source_language`, `target_language`, timestamps | Migrate existing session state deliberately |
| `user_preferences` | `user_id PK/FK`, `settings_json`, `updated_at` | Whitelist schema; no API keys or nonportable device IDs |
| `usage_events` | `id`, `user_id FK`, `translation_session_id FK nullable`, `provider`, `model`, `input_tokens`, `output_tokens`, `estimated_cost_usd`, `created_at` | Metrics and cost controls; sensitive payloads excluded |

`translation_history` is **opt-in / deferred** until retention and privacy requirements are approved. Use UTC timestamps, foreign keys, indexes on ownership and expiry, and migrations with reversible downgrade where feasible.

## API contract candidates (not implemented)

| Method / path | Purpose | Auth |
|---|---|---|
| `POST /api/v1/auth/register` | Account creation | Public, rate limited |
| `POST /api/v1/auth/login` | Establish server session | Public, rate limited |
| `POST /api/v1/auth/logout` | Revoke session | Required + CSRF |
| `GET /api/v1/auth/me` | Current account | Required |
| `POST /api/v1/auth/verify-email` | Verify email token | Public, rate limited |
| `POST /api/v1/auth/password-reset/request` | Request reset | Public, rate limited |
| `POST /api/v1/auth/password-reset/confirm` | Complete reset | Public, rate limited |
| `GET /api/v1/preferences` / `PATCH ...` | Own preferences | Required |
| `GET /api/v1/translation-sessions` | List own sessions | Required |
| `POST /api/v1/translation-sessions` | Create own session | Required |
| `GET /api/v1/translation-sessions/{id}` | Read own session | Required |

Existing endpoints and WebRTC session negotiation must be inventoried and mapped before defining breaking changes. For realtime connections, validate Origin and authenticate at handshake or via a short-lived, scoped server-issued capability; do not place long-lived credentials in URLs.

## Migration strategy

1. Inventory SQLite schema, migrations, storage adapters, file uploads, retention jobs and existing `X-Client-Id` ownership semantics.
2. Define PostgreSQL models and Alembic baseline with explicit ownership constraints.
3. Introduce repository interfaces and dual-backend contract tests; avoid permanent dual-write.
4. Develop a one-time export/transform/import with dry-run, counts, FK checks, rollback and backups.
5. Explicitly decide how legacy client-owned sessions map to new users; **do not automatically assign all historical sessions to the first account**.
6. Cut over with a controlled maintenance window; retain SQLite rollback artifact until acceptance.

## Frontend migration strategy

- Slice 1: inventory Streamlit views and embedded JS assets; document event contracts, browser APIs and server endpoints.
- Subsequent slices: implement login/shell and text workspace first; port Standard, Direct and Enhanced incrementally with device-specific browser tests.
- Preserve the independent Conference Monitor and isolation reference, including local-only routing and output safety guards.
- Ensure HTTPS, permission prompts, `setSinkId` support checks, WebSocket upgrade and WebRTC behavior across browsers.

## Threat model / public beta gate

Mandatory: session fixation protection, CSRF defense, login rate limits, email verification, password-reset token expiry, per-user access control, secrets isolation, upload limits, quotas / provider-cost ceilings, log redaction, backup/restore tests, CORS allowlist, TLS and monitoring. Private beta until these controls and data-protection decisions are validated.

## Slice 1 Definition of Done

- [ ] Architecture diagram and ADRs reviewed.
- [ ] Existing API/WebSocket and Streamlit asset inventory completed.
- [ ] PostgreSQL schema and data-retention policy approved.
- [ ] Auth/session/CSRF contracts approved, including WebRTC handshake.
- [ ] Legacy session ownership migration rule approved.
- [ ] Browser audio compatibility matrix and acceptance scenarios written.
- [ ] Compose topology and secret-handling approach reviewed.
- [ ] Test plan for cross-user access, migrations, and audio regressions approved.
- [ ] No change to v1.1.1 runtime behavior.

## Next slices (proposed)

2. Persistence and migration adapters; 3. Identity and session security; 4. Next.js shell and text workspace; 5. Voice Direct/Enhanced and browser-audio parity; 6. production hardening and deployment.
