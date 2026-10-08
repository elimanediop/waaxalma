# ADR-001 — Waaxalma Web Platform

**Status:** Proposed · **Version:** v1.2.0 · **Date:** 2026-10-08

## Context
v1.1.1 is a FastAPI + Streamlit application with SQLite-backed sessions and client-header isolation. A public, multi-user service requires authenticated identity, persistent shared data and a frontend suited to browser audio and account flows.

## Decision
Adopt Next.js/React/TypeScript for web, retain FastAPI for API and orchestration, use PostgreSQL for transactional data, and deploy initially with Docker Compose and a TLS reverse proxy. Maintain Streamlit temporarily for migration parity.

## Consequences
Browser audio and WebRTC components require deliberate porting and parity testing. More operational responsibility for database backups, schema migration, authentication and security. No rewrite of the AI provider pipeline is required by this decision.

## Alternatives
Continue Streamlit: smaller initial migration, less flexible public product UI. Full backend rewrite: unnecessary risk. Kubernetes: unnecessary for initial scale.
