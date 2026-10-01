# External Tools

This directory documents third-party tools that may be required for
specific Waaxalma features.

Third-party installers and binaries must not be committed to this repository
unless their redistribution license explicitly allows it.

## VB-Audio Virtual Cable

Waaxalma uses virtual audio devices for conferencing integration.

### v0.4.3 — Outbound conferencing

A single VB-CABLE is sufficient:

```text
Waaxalma
  → CABLE Input
  → CABLE Output
  → Teams / Zoom / Meet microphone

  