# Waaxalma — Slice 4.1 (Next.js frontend)

This directory is a **new, independent** frontend. The existing `streamlit/` and `backend/` remain unchanged.

## Prerequisites
- Node.js 22+
- Running FastAPI backend, PostgreSQL migrated through identity migration `0002`, `WAAXALMA_AUTH_ENABLED=true`
- Backend `WAAXALMA_AUTH_ALLOWED_ORIGINS=http://localhost:3000` (add additional explicit origins if needed)

## Run
```powershell
cd frontend
Copy-Item .env.example .env.local
npm install
npm run dev
```
Open http://localhost:3000. Use **Create an account** (password >= 12 chars), then sign in. Successful login routes to `/dashboard`.

## Architecture / security
- Browser calls relative `/api/*` paths. Next.js rewrites them to `WAAXALMA_BACKEND_URL` server-side. This avoids cross-origin cookies in local development.
- Backend owns authentication, CSRF and HttpOnly `waaxalma_session` cookie (Path=/api). No session secrets in localStorage.
- `/dashboard` verifies session through `/api/auth/me` on load and redirects unauthenticated users to `/login`. This is a **client-side access guard**, not server-side authorization; backend endpoints must always enforce ownership.
- Logout sends `X-CSRF-Token` from `/auth/me` to `/auth/logout`.
- Sidebar tools are intentionally disabled pending Slices 4.3–4.5; capability cards describe the framework and do not invent usage statistics.
- Next.js `rewrites()` proxies HTTP APIs only. Authenticated WebSocket integration requires separate design in Slice 4.5.

## Quality checks
```powershell
npm run lint
npm run typecheck
npm run build
```

## Scope
Slice 4.1 delivers foundation + dashboard + a minimal login/register/logout flow to enable the requested post-login experience. Slice 4.2 will harden and test authentication UX and session handling.
