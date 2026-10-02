# Waaxalma v0.4.4 — Slice 3

## Conference Audio Input

Slice 3 introduces a dedicated inbound conference-audio boundary without yet
performing speech recognition or translation.

```text
Remote participant
    ↓
Teams / Zoom / Meet
    ↓
Conference speaker output
    ↓
Virtual Cable B — playback endpoint
    ↓
Virtual Cable B — recording endpoint
    ↓
ConferenceInputManager
    ↓
Raw inbound MediaStream
    ↓
Audio-energy diagnostic only
```

Persistent browser selection:

```text
waaxalma.conferenceInputDeviceId
```

### Safety

- Conference input is isolated from `AudioInputManager`.
- If the selected conference device disappears, capture stops.
- An explicitly selected conference input does not silently fall back to the
  physical/default microphone.
- The UI warns when Conference Input matches the physical Waaxalma microphone.
- Echo cancellation, noise suppression and automatic gain control are disabled
  on this raw inbound capture where supported.
- Slice 3 never plays captured conference audio, preventing an immediate loop.

### Two independent virtual paths

For simultaneous bidirectional conferencing, use two independent virtual audio
paths:

```text
Cable A: Waaxalma translated outbound audio -> Teams microphone
Cable B: Teams speaker / remote audio        -> Waaxalma Conference Input
```

Do not use the same virtual cable for both directions; doing so can re-inject
Waaxalma's own output into the inbound path.

### Slice 3 scope

Implemented:
- conference input discovery;
- explicit device selection and persistence;
- permission refresh;
- start/stop capture;
- clean resource release;
- incoming RMS/dBFS meter;
- selected-device loss handling;
- physical-input conflict warning.

Not implemented yet:
- streaming STT;
- inbound source transcript;
- inbound translation;
- inbound TTS;
- full-duplex orchestration.

Those belong to Slice 4.
