# Waaxalma v0.4.4 — Slice 5

## Full Duplex Session Control

Slice 5 coordinates the outbound realtime interpreter and the inbound
conference interpreter as one local conferencing session.

```text
                         Full Duplex Controller
                         Start / Stop / Status
                              │           │
                   ┌──────────┘           └──────────┐
                   ▼                                 ▼
             OUTBOUND                           INBOUND

Physical microphone                         Remote participant
      ↓                                            ↓
Direct / Enhanced                                 Teams
      ↓                                            ↓
translated audio                            Virtual Path B
      ↓                                            ↓
Primary / Conference Output                 Conference Input
      ↓                                            ↓
Virtual Path A                              Enhanced STT
      ↓                                            ↓
Teams microphone                            Translation / TTS
      ↓                                            ↓
Remote participant                          Local Monitor
                                                   ↓
                                               Headphones
```

### Browser coordination

The existing independently implemented clients remain separate. Slice 5 uses
same-origin browser storage as a lightweight coordination bus:

```text
waaxalma.fullDuplex.command
waaxalma.fullDuplex.desired

waaxalma.fullDuplex.outbound.direct.status
waaxalma.fullDuplex.outbound.enhanced.status
waaxalma.fullDuplex.inbound.status
```

`Start Full Duplex` starts the currently selected outbound mode plus inbound.
`Stop All` stops both.

If either direction publishes an error while Full Duplex is active, the
controller automatically issues `Stop All` so the other direction does not
remain orphaned.

### Existing boundaries preserved

- outbound physical microphone selection remains owned by AudioInputManager;
- outbound translated audio remains on Primary / Conference Output;
- inbound capture remains owned by ConferenceInputManager;
- inbound translated audio remains Local Monitor only;
- Direct and Enhanced remain independent outbound execution models;
- Enhanced and inbound PCM carry-byte / 20 ms buffering remain unchanged.

### Validation state

This slice can be developed and syntax/architecture checked without the second
virtual audio path.

The real Full Duplex conferencing POC remains pending until two independent
virtual paths are available.

Do not create the final v0.4.4 release tag until the real bidirectional call,
backend regression suite, and release documentation are complete.
