# Waaxalma v0.4.4 — Freeze / Tag Checklist

Release: **v0.4.4 — Conferencing Audio & Device Control**

## Blocking release scope

The v0.4.4 release is centered on reliable outbound conferencing:

```text
Physical microphone
    → Waaxalma
    → translated audio
    → Primary / Conference Output
    → virtual audio cable
    → Teams / Meet / Zoom microphone
```

Validated implementation scope:

- explicit physical microphone selection;
- Realtime Direct selected-input support;
- Realtime Enhanced selected-input support;
- independent Local Monitor output;
- Standard / Direct / Enhanced conference-output routing;
- no dependency on Windows **Listen to this device**;
- consolidated Streamlit audio-device workspace;
- external virtual-audio prerequisites documented without redistributing
  third-party installers.

Experimental and non-blocking:

- Conference Input capture;
- inbound conference translation;
- Full Duplex Start / Stop coordination.

## Backend regression — complete

Executed from `backend`:

```powershell
python -m pytest -q
```

Freeze result:

```text
216 passed
0 failed
1 known non-blocking warning
14.90 s
```

Known warning:

```text
StarletteDeprecationWarning:
Using httpx with starlette.testclient is deprecated;
install httpx2 instead.
```

This warning is deferred beyond v0.4.4.

## Final outbound smoke test

Before creating the tag, run one short smoke test with the final working tree:

```text
Browser
= Microsoft Edge

Waaxalma microphone
= physical microphone

Primary / Conference Output
= virtual cable playback endpoint

Local Monitor
= headphones

Conferencing microphone
= virtual cable recording endpoint

Windows "Listen to this device"
= OFF
```

Verify:

```text
Waaxalma translated audio
    → virtual cable
    → conferencing microphone
    → remote participant
```

The bidirectional / second-cable POC is not a release blocker for v0.4.4.

## Freeze commands

From the repository root:

```powershell
git status
git diff
```

Confirm that no local installers, ZIP archives, secrets, `.env` files, or
generated temporary files are staged.

Then:

```powershell
git add .
git status
git commit -m "release: Waaxalma v0.4.4 conferencing audio and device control"
```

Create the annotated tag only after the final outbound smoke test succeeds:

```powershell
git tag -a v0.4.4 `
  -m "Waaxalma v0.4.4 - Conferencing Audio & Device Control"
```

Push:

```powershell
git push origin HEAD
git push origin v0.4.4
```

## Release status

```text
Backend regression        ✅ 216 passed
Explicit microphone       ✅ validated
Independent local monitor ✅ validated
Outbound conferencing     ✅ established release path
Inbound / Full Duplex      🧪 experimental, non-blocking
Final current-tree smoke  ⬜ run before tag
```
