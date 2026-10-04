## Layout

The persistent, collapsible Streamlit sidebar holds the workspace mode, target language, Enhanced source language/terminology, and browser audio devices. A Device settings selector displays one audio panel at a time; its iframe uses content-based height instead of a fixed height, avoiding nested scrollbars. The wide main area shows one active workspace: Standard recording/results, Direct, or Enhanced. Experimental inbound/Full Duplex controls remain in a collapsed section below the workspace. On narrow screens use Streamlit's sidebar toggle.

Stop realtime interpretation before changing settings or mode: Streamlit reruns and can recreate the iframe. Start the new session after the new settings appear. Source-language selection is available in Enhanced; Direct keeps its provider-native behavior. The supported realtime language choices remain English/French/Spanish, with Auto also available for Enhanced source. Standard retains its existing language choices.

Browser scripts/styles are stored under `assets/js/` and `assets/css/`; HTML skeletons under `assets/html/`. `ui/assets.py` assembles them inline before iframe rendering, so there is no need for a new static HTTP endpoint. `ui/settings_panel.py` renders settings and `ui/workspace.py` applies settings to the live browser client. Separate iframe CSS remains independent of the Streamlit theme.

## Validation

- Clean installation of the existing hashed UI lock. Use a separate UI environment: the system/backend Python may not have the UI dependencies.
- Python and all nested JavaScript syntax checks passed.
- All extracted HTML reassembled to the original browser content before sidebar customization.
- Device selectors, Standard audio playback, conferencing clients and customized live client scripts loaded and passed Node syntax checks.
- Streamlit AppTest: initial Standard rendering and switching Direct/Enhanced/Standard passed without application exceptions.
- UI CI now tests the sidebar/workspace rendering and nested assets using explicit UTF-8.

No physical microphone, WebRTC provider call, Teams bridge or Docker engine was tested in this environment. Repeat those browser acceptance checks after applying the overlay, and let the existing Linux/Windows/container CI validate the commit.

## Windows UI environment

From the repository root, if the UI environment is not already available:

```powershell
python -m venv .venv-ui
.\.venv-ui\Scripts\Activate.ps1
python -m pip install --require-hashes -r streamlit/requirements.lock
python ci/ui_render_checks.py
python ci/static_checks.py
```

If a dedicated UI environment already exists, activate it instead of creating another. GitHub's ui-install job already creates and uses its isolated UI environment. Global Python does not need these packages.

Content-based iframe sizing removes the fixed-height scrollbar in device selectors. A small screen or a long workspace transcript can still require scrolling the page; the patch does not hide overflowing content.
