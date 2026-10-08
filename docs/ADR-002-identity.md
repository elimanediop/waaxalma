# ADR-002 — Application Identity and Sessions

**Status:** Proposed · **Version:** v1.2.0 · **Date:** 2026-10-08

## Decision
Use email/password accounts with Argon2id, verification/reset flows and server-managed opaque sessions stored hashed in PostgreSQL. Use Secure HttpOnly SameSite cookies, session rotation and CSRF protection. Resolve owner from server-side session; `X-Client-Id` is not a trust boundary for public users.

## Consequences
Requires email delivery, brute-force protection, cookie/origin design for subdomains and WebSocket/WebRTC authentication. Does not introduce OAuth/OIDC/JWT or an IAM platform.
