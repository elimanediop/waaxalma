# Security policy — v0.5.0 release candidate

Waaxalma identifies clients using `X-Client-Id`. This is a self-declared namespace, not proof of identity or authentication. Anyone who can reach the API and knows another client's identifier can present it. Use a trusted, authenticated gateway that supplies/overwrites identity before exposing the backend beyond a trusted local environment. This release does not introduce OAuth, OIDC, JWT or an IAM integration.

HTTP identity is mandatory for protected operations. IDs are 1–128 ASCII characters matching `[A-Za-z0-9][A-Za-z0-9_.-]{0,127}`; comparison is case-sensitive. Persisted sessions have immutable owners. Missing/invalid identity returns 401; a foreign or legacy unowned session returns 403; a missing persisted session returns 404; a closed owned session returns 409 for active-only operations. WebSocket browser identity can use `client_id` in the query; conflicting header/query values are rejected. Generic/realtime correlation IDs that do not name a persisted session remain transient identifiers.

Health, metrics, API documentation, static audio and browser metrics are not owner-protected. Static audio URLs are opaque identifiers, not authorization controls. Use a trusted ingress, TLS and network restrictions; do not publish this Compose example directly to the Internet. Compose binds host ports to localhost by default. CORS is a browser restriction, not an authentication boundary.

Conversations and message contents are stored in SQLite without application-level encryption. The owner field isolates protected API access, not local database readers. Backups, generated audio, browser storage and logs have separate security/retention implications. The default cleanup policy applies only to explicitly closed conversation rows and their messages. It does not delete active rows, audio files, upload directories, backups or logs.

Store provider keys in environment injection or an appropriately restricted local `.env`. Never commit keys, production databases or private keys. Rotate any exposed key at its provider; removing a file from Git does not remove historical exposure. Container images install hashed dependencies, run UID/GID 10001, and use read-only root filesystems with explicit writable data/tmp mounts. Dependency hashing and non-root execution are controls, not a guarantee of vulnerability-free dependencies.

Business events omit transcript/audio/prompt/credential content. Identifiers and language metadata can still be identifying data. Restrict metrics/traces/log access. Optional OTLP exports should go to a trusted collector; this implementation does not supply exporter authentication headers.

`ci/release_checks.py` performs a targeted scan of tracked files for environment/data files and recognizable credential patterns. It reports paths, not matching values. This does not replace provider key rotation, dependency vulnerability assessment or a human review of the staged diff and Git history. Final release requires the checks in docs/release-v0.5.0.md; no security audit certification is claimed.

For a vulnerability, use the repository's private vulnerability reporting feature if enabled, or a maintainer's established private contact. Do not publish credentials or sensitive session contents in an issue. No unverified contact address is invented by this distribution.
