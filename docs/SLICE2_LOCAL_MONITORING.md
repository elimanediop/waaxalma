# Waaxalma v0.4.4 — Slice 2

## Independent Local Monitoring

Slice 2 separates the conference/primary output from the user's local
monitoring output.

Browser storage:

```text
waaxalma.audioOutputDeviceId
waaxalma.monitorOutputDeviceId
waaxalma.monitorEnabled
```

Recommended conferencing configuration:

```text
Realtime Audio Input
  = physical microphone

Primary / Conference Output
  = CABLE Input (VB-Audio Virtual Cable)

Local Monitor
  = enabled
  = physical headphones
```

Do not select speakers for local monitoring during a live microphone session
unless acoustic echo is intentionally being tested.

### Direct

The same translated WebRTC `MediaStream` is attached to two independently
managed audio elements:

```text
remote translated stream
  ├─ primary/conference audio element -> CABLE Input
  └─ local monitor audio element      -> headphones
```

### Enhanced

The existing Web Audio PCM scheduler still feeds one
`MediaStreamAudioDestinationNode`. That stream is consumed by two managed
audio elements with separate sinks.

The v0.4.2 invariants remain unchanged:

- PCM16 carry-byte handling;
- 20 ms jitter buffer;
- ordered `nextPlaybackTime`;
- final STT transcript authority;
- rolling context;
- per-utterance metrics.

### Standard

The generated audio URL is played by the visible primary player. When local
monitoring is enabled, a hidden second element mirrors play/pause/seek/rate/
volume state to the monitor sink.

### Safety rule

If the monitor and primary output have the same stored device ID, local
monitor playback is suppressed to avoid duplicate playback.
