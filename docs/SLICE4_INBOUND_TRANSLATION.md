# Waaxalma v0.4.4 — Slice 4

## Inbound Conference Translation

```text
Remote participant
    ↓
Teams / Zoom / Meet
    ↓
Virtual Cable B
    ↓
Conference Input
    ↓
Streaming STT
    ↓
authoritative remote transcript
    ↓
existing Enhanced WebSocket
    ↓
streaming translation
    ↓
streaming TTS
    ↓
Local Monitor only
    ↓
Headphones
```

Slice 4 reuses the existing backend endpoints:

```text
POST /api/realtime/enhanced/session
WS   /api/realtime/enhanced/stream
```

No new backend route is introduced.

### Safety

Inbound TTS is bound to:

```text
waaxalma.monitorOutputDeviceId
```

and never to:

```text
waaxalma.audioOutputDeviceId
```

The inbound client refuses to start when Conference Input or Local Monitor is
not explicitly selected, when Conference Input equals the physical microphone,
or when Local Monitor equals Primary / Conference Output.

### Recommended mapping

```text
Physical microphone       = real microphone
Primary Conference Output = Cable A Input
Teams microphone          = Cable A Output
Teams speaker             = Cable B Input
Conference Input          = Cable B Output
Local Monitor             = physical headphones
```

### Preserved Enhanced behavior

- final STT transcript remains authoritative;
- terminology is passed to STT / translation;
- rolling context remains session-scoped;
- streaming translation and TTS overlap;
- PCM16 carry-byte continuity is preserved;
- 20 ms playback buffering is preserved;
- silence commit remains ~320 ms.

Slice 5 will coordinate outbound + inbound as one full-duplex session.
