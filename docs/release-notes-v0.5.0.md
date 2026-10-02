# v0.5.0 release candidate notes

Adds persistent SQLite conversations and explicit owners; self-declared client isolation with strict headers; typed development/test/production settings; wheel and non-root containers; universal hashed dependency locks; Windows/Linux CI quality gates; business JSON events and request correlation; provider/session metrics and optional OTLP traces; explicit closed-session retention, maintenance commands and shutdown/restart governance.

Compatibility: protected requests now require X-Client-Id. Existing Slice 1 rows migrate with null owners and require verified offline assignment before protected access. Do not merge backend/UI dependency environments. Clients must use returned audio URLs, since correlation IDs are independent of file names. New automated cleanup is disabled by default and never deletes active conversations.

Operational acceptance and final tagging follow release-v0.5.0.md. No cloud deployment, public GitHub Release or final tag is performed by this distribution. Inbound conferencing/full-duplex remain experimental. Previous v0.4.x latency examples are historical measurements, not new v0.5 service guarantees.
