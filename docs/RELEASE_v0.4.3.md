# Waaxalma v0.4.3 — Freeze / Tag Checklist

Release: **v0.4.3 — Universal Audio Output & Conferencing Bridge**

## Validated scope

- Standard audio output routing
- Realtime Direct audio output routing
- Realtime Enhanced audio output routing
- shared AudioOutputManager / setSinkId
- VB-Audio Virtual Cable transport
- Teams microphone bridge
- real Microsoft Teams call validated with Microsoft Edge
- Streamlit st.iframe migration
- production diagnostic UI cleanup

## Final pre-tag verification

From `backend`:

```powershell
python -m pytest -q
```

Expected baseline before v0.4.3 work was:

```text
216 passed
```

Do not tag if the current branch has a regression.

Then perform one smoke test:

```text
Waaxalma output = CABLE Input
Teams microphone = CABLE Output
Teams speaker = physical headset
Windows default input = physical microphone
Browser = Microsoft Edge
```

Verify one translated utterance reaches the remote participant.

## Git freeze / tag

```powershell
git status
git add .
git commit -m "release: Waaxalma v0.4.3 universal audio output"
git tag -a v0.4.3 -m "Waaxalma v0.4.3 - Universal Audio Output & Conferencing Bridge"
git push origin HEAD
git push origin v0.4.3
```

## Known release note

Microsoft Edge is the validated reference browser for the Teams/VB-CABLE POC. Chrome requires explicit site audio-device permission to expose all outputs and did not deliver the virtual-cable audio to the remote participant in the tested setup.
