# Conference audio routing and monitoring — v1.1.1

## Purpose

Separate remote conference audio from the local microphone translation path. Conference Monitor lets the user hear incoming Teams audio on a physical headset. Local Monitor remains reserved for locally monitoring Waaxalma-generated translated audio.

## Recommended Windows/Teams configuration

| Setting | Device |
| --- | --- |
| Teams Speaker | CABLE-A Input |
| Waaxalma Conference Input | CABLE-A Output |
| Conference Monitor | ON; physical headphones/headset |
| Waaxalma Realtime Audio Input | Physical microphone (e.g., Realtek) |
| Waaxalma Conference Output | CABLE-B Input |
| Teams Microphone | CABLE-B Output |

Inbound: Teams → CABLE-A Input → CABLE-A Output → reference-aware isolation and Conference Monitor → headphones.

Outbound: physical microphone → isolation → Direct/Enhanced → translation → CABLE-B Input → CABLE-B Output → Teams microphone.

The physical headset must not be the conference microphone output. Turn OFF Windows **Listen to this device** on CABLE-A Output while Conference Monitor is ON, otherwise playback can be duplicated.

## Operation

1. Select `CABLE-A Output` as Conference Input.
2. Enable Conference Monitor and explicitly select physical headphones as its output (do not select any virtual cable).
3. Configure Teams Speaker to `CABLE-A Input` and Teams Microphone to `CABLE-B Output`.
4. Set Waaxalma Conference Output to `CABLE-B Input`.
5. Confirm Teams remote speech is audible through Conference Monitor, with Windows Listen disabled.
6. Start Direct, then Enhanced, and verify local speech is translated but remote-only speech is not.
7. Test simultaneous local and remote speech separately: reference-VAD gating may suppress both.

## Independence and limitations

- Conference Monitor is independent of Full Duplex Start/Stop and inbound translation capture.
- The isolation reference is selected through `waaxalma.conferenceInputDeviceId` and should contain actual remote conference audio.
- If a reference is unavailable, a passthrough fallback cannot remove contamination already present in the microphone signal. Do not interpret passthrough as successful echo suppression.
- Browser audio playback may require a user gesture and support for output selection (`setSinkId`).
- Audio device IDs can change after reconnects, browser permission changes or driver updates; refresh the device selectors.
- The present isolation uses reference-level voice activity gating, **not signal subtraction/AEC**; full-duplex double-talk quality is not guaranteed.

## Manual acceptance checklist

- [ ] Teams audio heard in physical headphones through Conference Monitor
- [ ] Windows Listen disabled and no double playback
- [ ] Direct translates local voice only during remote-only speech
- [ ] Enhanced translates local voice only during remote-only speech
- [ ] Conference Monitor works without Full Duplex Start/Stop
- [ ] Turning monitor OFF stops local conference playback
- [ ] Disconnecting reference device fails safely (verify behavior)
- [ ] Double-talk tested and limitations documented
