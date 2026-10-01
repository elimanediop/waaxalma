# Waaxalma v0.4.4 — Streamlit UI Redesign

This redesign changes presentation only; the v0.4.4 Slice 1-3 audio logic is preserved.

## Main changes

- `layout="wide"` to give embedded browser audio controls enough width.
- Compact hero header.
- One `Audio Devices & Conferencing` expander instead of four vertically stacked iframes.
- Four device tabs:
  - Microphone
  - Conference Output
  - Local Monitor
  - Conference Input
- Conference Input remains full-width inside its tab, avoiding the narrow layout that caused buttons to stack and the iframe to scroll.
- Standard mode top controls use a two-column layout.
- Existing Direct / Enhanced / Standard behavior is unchanged.

## Expected effect

The page no longer shows all audio controls at once. The browser device controls remain available, but the main Interpretation / Live Translation workspace stays visible without excessive vertical scrolling.
