# ADR-003 — PostgreSQL Persistence and Legacy Data

**Status:** Proposed · **Version:** v1.2.0 · **Date:** 2026-10-08

## Decision
Target PostgreSQL with SQLAlchemy 2.x and Alembic. Preserve v1.1.1 runtime until a reviewed migration path exists. Map existing session ownership to accounts explicitly; no silent claim of old data. Implement migration verification, backups and rollback.

## Consequences
New schema and migration testing, retention rules and connection pooling are needed. SQLite remains available for compatibility tests until cutover is approved.
