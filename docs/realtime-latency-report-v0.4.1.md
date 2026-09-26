# Waaxalma Realtime Latency Report — v0.4.1

## 1. Purpose

This report documents the first measured latency baseline for Waaxalma's **Realtime Direct** mode introduced in `v0.4.1`.

The objective is to separate:

- startup and connection latency;
- provider/session latency;
- actual interpretation latency perceived after the user starts speaking.

The same metrics will be reused later to compare:

```text
v0.4.1 — Realtime Direct
vs
v0.4.2 — Realtime Enhanced
```

---

## 2. Realtime Direct Architecture

```text
Microphone
    ↓
Waaxalma Realtime Session API
    ↓
RealtimeTranslationService
    ↓
ProviderRegistry
    ↓
RealtimeTranslationProvider
    ↓
OpenAI gpt-realtime-translate
    ↓
WebRTC
    ├── translated transcript
    └── translated audio
```

Realtime Direct intentionally bypasses the standard Waaxalma:

```text
Context
Quality
SpeechStage
```

pipeline in order to minimize latency.

---

## 3. Measurement Model

Two categories are measured independently.

### 3.1 Startup latency

Startup metrics describe the time required to establish the realtime session.

```text
Start
  ↓
Create ephemeral session
  ↓
Acquire microphone
  ↓
Establish WebRTC
  ↓
Open realtime data channel
```

Relevant metrics:

```text
session_request_ms
microphone_acquisition_ms
webrtc_connection_ms
data_channel_open_ms
remote_audio_track_available_ms
```

### 3.2 Interpretation latency

Interpretation metrics begin from the actual detected start of user speech.

```text
Speech detected
    ↓
First translated text
    ↓
First audible translated audio
```

Relevant metrics:

```text
speech_start_after_connection_ms
speech_to_first_translation_ms
speech_to_first_audio_ms
translation_to_first_audio_ms
provider_first_translation_elapsed_ms
```

---

## 4. Browser Measurement Method

The Realtime client uses `performance.now()` for local timestamps.

A lightweight local audio-energy detector is used to identify:

1. source speech start;
2. first translated audio energy.

The detector uses RMS energy thresholds.

Current baseline configuration:

```text
SOURCE_VAD_RMS_THRESHOLD = 0.035
REMOTE_AUDIO_RMS_THRESHOLD = 0.015
VAD_REQUIRED_FRAMES = 3
```

The local detector is used for observability only. It does not modify or gate the audio sent to the provider.

---

## 5. Observed Baseline

Tested with:

```text
Provider: OpenAI
Model: gpt-realtime-translate
Mode: direct
Transport: WebRTC
```

Observed browser metrics:

| Metric | Observed value |
|---|---:|
| `session_request_ms` | 1613.3 ms |
| `microphone_acquisition_ms` | 470.6 ms |
| `remote_audio_track_available_ms` | 1116.8 ms |
| `webrtc_connection_ms` | 1841.0 ms |
| `data_channel_open_ms` | 2098.2 ms |
| `speech_start_after_connection_ms` | 795.3 ms |
| `start_to_first_translation_ms` | 5498.9 ms |
| `connection_to_first_translation_ms` | 1185.6 ms |
| `speech_to_first_translation_ms` | **390.3 ms** |
| `provider_first_translation_elapsed_ms` | 1000.0 ms |
| `speech_to_first_audio_ms` | **1350.5 ms** |
| `translation_to_first_audio_ms` | 960.2 ms |

---

## 6. Interpretation of Results

### 6.1 Startup

Measured startup components:

```text
Session request             ≈ 1.61 s
Microphone acquisition      ≈ 0.47 s
WebRTC connection           ≈ 1.84 s
Data channel availability   ≈ 2.10 s from WebRTC start
```

These values represent connection setup, not realtime interpretation latency.

`start_to_first_translation_ms` must therefore not be used as the primary realtime quality metric because it includes:

- session creation;
- microphone acquisition;
- WebRTC negotiation;
- user delay before speaking;
- translation processing.

---

## 7. Primary Realtime KPIs

The most relevant user-perceived metrics are:

### Speech to first translated text

```text
speech_to_first_translation_ms
= 390.3 ms
```

This measures the delay between locally detected source speech and the first translated transcript delta.

### Speech to first translated audio

```text
speech_to_first_audio_ms
= 1350.5 ms
```

This measures the delay between source speech detection and the first detected translated audio energy.

### Translation to first translated audio

```text
translation_to_first_audio_ms
= 960.2 ms
```

This provides a useful indication of the audio-generation/playback portion after the first translated text becomes available.

---

## 8. Metric Consistency Check

The local measurements are internally consistent.

Observed:

```text
connection_to_first_translation_ms
= 1185.6 ms

speech_start_after_connection_ms
= 795.3 ms
```

Difference:

```text
1185.6 - 795.3
= 390.3 ms
```

This exactly matches:

```text
speech_to_first_translation_ms
= 390.3 ms
```

This is a positive indication that the local speech-start measurement is coherent for this test.

---

## 9. Provider-Reported Elapsed Time

The provider event reported:

```text
provider_first_translation_elapsed_ms
= 1000 ms
```

This value must be treated separately from the browser VAD timeline.

It does not necessarily share the same clock origin as:

```text
speech_to_first_translation_ms
```

Therefore it is retained as a provider diagnostic metric but is not used as a direct replacement for browser-observed speech latency.

---

## 10. Prometheus Metrics

### Backend session metrics

```text
waaxalma_realtime_sessions_total

waaxalma_realtime_session_creation_duration_seconds

waaxalma_realtime_session_errors_total
```

Example dimensions:

```text
provider="openai"
model="gpt-realtime-translate"
```

### Browser / QoE latency

Selected browser metrics are posted to:

```text
POST /api/realtime/metrics
```

and exposed through:

```text
waaxalma_realtime_client_latency_seconds
```

Current supported metric values:

```text
metric="session_request"

metric="webrtc_connection"

metric="speech_to_first_translation"

metric="speech_to_first_audio"
```

Common labels:

```text
provider="openai"

model="gpt-realtime-translate"

mode="direct"
```

---

## 11. Why Only Selected Browser Metrics Are Exported

Not every diagnostic timing is sent to Prometheus.

Prometheus receives only the metrics useful for long-term operational comparison:

```text
session_request
webrtc_connection
speech_to_first_translation
speech_to_first_audio
```

Additional diagnostics remain available in the browser console.

This avoids unnecessary metric cardinality and keeps dashboards focused on user-visible performance.

No:

```text
request_id
session_id
client_secret
```

is used as a Prometheus label.

---

## 12. Realtime Direct Baseline Summary

For the tested local environment:

```text
Startup

Session creation                 ~1.61 s
Microphone acquisition           ~0.47 s
WebRTC establishment             ~1.84 s


Interpretation

Speech → translated text         ~0.39 s
Speech → translated audio        ~1.35 s
Translated text → audio          ~0.96 s
```

The primary v0.4.1 realtime baseline is therefore:

```text
speech_to_first_translation ≈ 390 ms
speech_to_first_audio       ≈ 1.35 s
```

These values are measurements from one local benchmark and must not be interpreted as universal service-level guarantees.

---

## 13. Current Limitations

### Source transcript

Realtime Direct currently treats source transcript as optional.

The tested WebRTC session exposed:

```text
session.output_transcript.delta
```

but did not expose source transcript events in the tested flow.

The UI therefore presents translated text while displaying an explicit fallback for source transcription.

### Proper names and terminology

Direct realtime translation may alter:

- personal names;
- product names;
- organization names;
- domain-specific terminology.

This is one of the reasons for retaining a planned Realtime Enhanced architecture.

### VAD thresholds

The current RMS thresholds were validated as a useful local observability baseline, but they may behave differently across:

- microphones;
- browser audio processing;
- environmental noise;
- operating systems.

Future production hardening should validate threshold behavior across devices.

---

## 14. Realtime Enhanced Comparison Target — v0.4.2

The planned Realtime Enhanced mode is:

```text
Microphone
    ↓
Streaming STT
    ↓
partial source transcript
    ↓
Context / terminology
    ↓
Streaming Translation
    ↓
partial translated text
    ↓
Streaming TTS
    ↓
translated audio
```

Its goal is not only lower latency.

It should provide additional control over:

- source transcript;
- names and terminology;
- contextual enrichment;
- provider selection;
- output voice.

The same Prometheus labels should allow comparison through:

```text
mode="direct"
```

and later:

```text
mode="enhanced"
```

---

## 15. v0.4.2 Performance Exit Criterion

Realtime Enhanced should be evaluated against the v0.4.1 Direct baseline.

Primary comparison metrics:

```text
speech_to_first_translation
speech_to_first_audio
```

The architecture should avoid introducing significant sequential waits between:

```text
STT
Translation
TTS
```

and should instead stream or overlap work wherever possible.

The comparison should consider both:

```text
latency
and
translation controllability / quality
```

rather than latency alone.

---

## 16. v0.4.1 Observability Status

```text
✓ backend session count
✓ backend session duration
✓ normalized realtime errors
✓ error counters
✓ browser session latency
✓ WebRTC connection latency
✓ local speech-start detection
✓ first translated text latency
✓ first translated audio latency
✓ browser metrics ingestion
✓ Prometheus exposure
```

The Realtime Direct observability baseline is considered complete for `v0.4.1`.
