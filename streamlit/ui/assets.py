from pathlib import Path
import json
import re
from config import API_URL, PUBLIC_API_URL, CLIENT_ID
NORMALIZED_API_URL = API_URL.rstrip('/')
PUBLIC_NORMALIZED_API_URL = PUBLIC_API_URL.rstrip('/')
STREAMLIT_DIR = Path(__file__).resolve().parents[1]



REALTIME_CLIENT_FILE = (

    STREAMLIT_DIR / "assets/html/realtime_client.html"

)


REALTIME_ENHANCED_CLIENT_FILE = (

    STREAMLIT_DIR / "assets/html/realtime_enhanced_client.html"

)







AUDIO_INPUT_MANAGER_FILE = (
    STREAMLIT_DIR / "assets/js/audio_input_manager.js"
)

AUDIO_INPUT_SELECTOR_FILE = (
    STREAMLIT_DIR / "assets/html/audio_input_selector.html"
)


AUDIO_OUTPUT_MANAGER_FILE = (
    STREAMLIT_DIR / "assets/js/audio_output_manager.js"
)

AUDIO_OUTPUT_SELECTOR_FILE = (
    STREAMLIT_DIR / "assets/html/audio_output_selector.html"
)

AUDIO_MONITOR_SELECTOR_FILE = (
    STREAMLIT_DIR / "assets/html/audio_monitor_selector.html"
)

CONFERENCE_INPUT_MANAGER_FILE = (
    STREAMLIT_DIR / "assets/js/conference_input_manager.js"
)

CONFERENCE_INPUT_SELECTOR_FILE = (
    STREAMLIT_DIR / "assets/html/conference_input_selector.html"
)

CONFERENCE_TRANSLATION_CLIENT_FILE = (
    STREAMLIT_DIR / "assets/html/conference_translation_client.html"
)

FULL_DUPLEX_CONTROLLER_FILE = (
    STREAMLIT_DIR / "assets/html/full_duplex_controller.html"
)


STANDARD_AUDIO_PLAYER_FILE = (
    STREAMLIT_DIR / "assets/html/standard_audio_player.html"
)

def load_template(path: Path) -> str:
    html = path.read_text(encoding='utf-8')
    def resolve(match):
        kind, name = match.groups()
        content = (STREAMLIT_DIR / 'assets' / kind.lower() / name).read_text(encoding='utf-8')
        if kind == 'CSS':
            return '<style>' + content + '</style>'
        return '<script>' + content + '</script>'
    return re.sub(r'__ASSET_(CSS|JS)_([A-Za-z0-9_.-]+)__', resolve, html)

def load_audio_input_manager() -> str:
    """
    Load the shared v0.4.4 realtime audio-input abstraction.

    Direct and Enhanced use the same selected physical microphone.
    """
    if not AUDIO_INPUT_MANAGER_FILE.exists():
        raise FileNotFoundError(
            "Audio input manager not found: "
            f"{AUDIO_INPUT_MANAGER_FILE}"
        )

    return AUDIO_INPUT_MANAGER_FILE.read_text(encoding='utf-8')


def load_audio_input_selector() -> str:
    """
    Load the global v0.4.4 realtime microphone selector and inject
    AudioInputManager before selector initialization.
    """
    if not AUDIO_INPUT_SELECTOR_FILE.exists():
        raise FileNotFoundError(
            "Audio input selector not found: "
            f"{AUDIO_INPUT_SELECTOR_FILE}"
        )

    html = load_template(AUDIO_INPUT_SELECTOR_FILE)

    placeholder = (
        "__AUDIO_INPUT_MANAGER_SCRIPT__"
    )

    if placeholder not in html:
        raise RuntimeError(
            "Audio input selector is missing "
            "the manager script placeholder."
        )

    manager_script = (
        "<script>\n"
        + load_audio_input_manager()
        + "\n</script>"
    )

    return html.replace(
        placeholder,
        manager_script,
        1,
    )

def load_audio_output_manager() -> str:
    """
    Load the shared browser-side audio-output abstraction.

    v0.4.3 injects the same manager into Standard, Direct,
    and Enhanced browser clients so all execution modes share
    one output-device implementation.
    """
    if not AUDIO_OUTPUT_MANAGER_FILE.exists():
        raise FileNotFoundError(
            "Audio output manager not found: "
            f"{AUDIO_OUTPUT_MANAGER_FILE}"
        )

    return AUDIO_OUTPUT_MANAGER_FILE.read_text(encoding='utf-8')


def load_audio_output_selector() -> str:
    """
    Load the global v0.4.3 audio-output discovery UI and inject the
    shared AudioOutputManager before selector initialization.

    The selected device is persisted browser-side and reused by
    Standard, Direct, and Enhanced playback clients.
    """
    if not AUDIO_OUTPUT_SELECTOR_FILE.exists():
        raise FileNotFoundError(
            "Audio output selector not found: "
            f"{AUDIO_OUTPUT_SELECTOR_FILE}"
        )

    html = load_template(AUDIO_OUTPUT_SELECTOR_FILE)

    placeholder = (
        "__AUDIO_OUTPUT_MANAGER_SCRIPT__"
    )

    if placeholder not in html:
        raise RuntimeError(
            "Audio output selector is missing "
            "the manager script placeholder."
        )

    manager_script = (
        "<script>\n"
        + load_audio_output_manager()
        + "\n</script>"
    )

    return html.replace(
        placeholder,
        manager_script,
        1,
    )



def load_audio_monitor_selector() -> str:
    """
    Load the v0.4.4 Slice 2 local-monitor selector.

    The selector reuses AudioOutputManager but persists an independent
    monitor sink and enable/disable flag.
    """
    if not AUDIO_MONITOR_SELECTOR_FILE.exists():
        raise FileNotFoundError(
            "Audio monitor selector not found: "
            f"{AUDIO_MONITOR_SELECTOR_FILE}"
        )

    html = load_template(AUDIO_MONITOR_SELECTOR_FILE)

    placeholder = (
        "__AUDIO_OUTPUT_MANAGER_SCRIPT__"
    )

    if placeholder not in html:
        raise RuntimeError(
            "Audio monitor selector is missing "
            "the manager script placeholder."
        )

    manager_script = (
        "<script>\n"
        + load_audio_output_manager()
        + "\n</script>"
    )

    return html.replace(
        placeholder,
        manager_script,
        1,
    )


def load_conference_input_manager() -> str:
    """
    Load the v0.4.4 Slice 3 conference-input abstraction.

    Slice 3 captures inbound conference/virtual-cable audio and exposes
    audio-energy only. It intentionally does not invoke STT, translation,
    TTS, or playback.
    """
    if not CONFERENCE_INPUT_MANAGER_FILE.exists():
        raise FileNotFoundError(
            "Conference input manager not found: "
            f"{CONFERENCE_INPUT_MANAGER_FILE}"
        )

    return CONFERENCE_INPUT_MANAGER_FILE.read_text(encoding='utf-8')


def load_conference_input_selector() -> str:
    """Load the Slice 3 conference-input selector and inject its manager."""
    if not CONFERENCE_INPUT_SELECTOR_FILE.exists():
        raise FileNotFoundError(
            "Conference input selector not found: "
            f"{CONFERENCE_INPUT_SELECTOR_FILE}"
        )

    html = load_template(CONFERENCE_INPUT_SELECTOR_FILE)

    placeholder = "__CONFERENCE_INPUT_MANAGER_SCRIPT__"
    if placeholder not in html:
        raise RuntimeError(
            "Conference input selector is missing the manager script placeholder."
        )

    manager_script = (
        "<script>\n"
        + load_conference_input_manager()
        + "\n</script>"
    )

    return html.replace(
        placeholder,
        manager_script,
        1,
    )



def load_conference_translation_client() -> str:
    """
    Load the v0.4.4 Slice 4 inbound conference translation client.

    It reuses the Enhanced backend contracts, captures the selected
    Conference Input, and routes TTS only to Local Monitor.
    """
    if not CONFERENCE_TRANSLATION_CLIENT_FILE.exists():
        raise FileNotFoundError(
            "Conference translation client not found: "
            f"{CONFERENCE_TRANSLATION_CLIENT_FILE}"
        )

    html = load_template(CONFERENCE_TRANSLATION_CLIENT_FILE)

    html = html.replace("__WAAXALMA_CLIENT_ID__", CLIENT_ID)
    html = html.replace(
        "__WAAXALMA_API_URL__",
        PUBLIC_NORMALIZED_API_URL,
    )

    manager_script = (
        "<script>\n"
        + load_conference_input_manager()
        + "\n</script>\n"
        + "<script>\n"
        + load_audio_output_manager()
        + "\n</script>\n"
    )

    if "</head>" not in html:
        raise RuntimeError(
            "Conference translation client HTML "
            "does not contain </head>."
        )

    return html.replace(
        "</head>",
        manager_script + "</head>",
        1,
    )




def load_full_duplex_controller(
    outbound_mode: str,
) -> str:
    """
    Load the v0.4.4 Slice 5 full-duplex lifecycle controller.

    It coordinates the selected outbound realtime iframe and the
    inbound conference translation iframe through same-origin
    localStorage command/status events.
    """
    if not FULL_DUPLEX_CONTROLLER_FILE.exists():
        raise FileNotFoundError(
            "Full duplex controller not found: "
            f"{FULL_DUPLEX_CONTROLLER_FILE}"
        )

    html = load_template(FULL_DUPLEX_CONTROLLER_FILE)

    normalized_mode = (
        "enhanced"
        if outbound_mode.lower() == "enhanced"
        else "direct"
    )

    mode_label = (
        "Enhanced"
        if normalized_mode == "enhanced"
        else "Direct"
    )

    return (
        html
        .replace(
            "__OUTBOUND_MODE_VALUE__",
            normalized_mode,
        )
        .replace(
            "__OUTBOUND_MODE_LABEL__",
            mode_label,
        )
    )


def load_standard_audio_player(
    audio_url: str,
) -> str:
    """
    Load the Standard interpreted-audio player and inject:

    - the shared v0.4.3 AudioOutputManager;
    - the fully qualified backend audio URL.

    The player is browser-managed so HTMLMediaElement.setSinkId()
    can route Standard audio to the same selected device used by
    Direct and Enhanced modes.
    """
    if not STANDARD_AUDIO_PLAYER_FILE.exists():
        raise FileNotFoundError(
            "Standard audio player not found: "
            f"{STANDARD_AUDIO_PLAYER_FILE}"
        )

    html = load_template(STANDARD_AUDIO_PLAYER_FILE)

    manager_placeholder = (
        "__AUDIO_OUTPUT_MANAGER_SCRIPT__"
    )

    audio_url_placeholder = (
        "__STANDARD_AUDIO_URL_JSON__"
    )

    if manager_placeholder not in html:
        raise RuntimeError(
            "Standard audio player is missing "
            "the manager script placeholder."
        )

    if audio_url_placeholder not in html:
        raise RuntimeError(
            "Standard audio player is missing "
            "the audio URL placeholder."
        )

    manager_script = (
        "<script>\n"
        + load_audio_output_manager()
        + "\n</script>"
    )

    html = html.replace(
        manager_placeholder,
        manager_script,
        1,
    )

    return html.replace(
        audio_url_placeholder,
        json.dumps(
            audio_url
        ),
        1,
    )


def load_realtime_client(
    client_file: Path,
) -> str:
    """
    Load one realtime browser client, inject the configured
    Waaxalma backend URL, then inject the shared v0.4.3
    AudioOutputManager.

    The JavaScript is embedded directly in the iframe HTML because
    local files under streamlit/ are not automatically served as
    static assets by st.iframe().
    """
    if not client_file.exists():
        raise FileNotFoundError(
            "Realtime client not found: "
            f"{client_file}"
        )

    html = load_template(client_file)

    html = html.replace("__WAAXALMA_CLIENT_ID__", CLIENT_ID)
    html = html.replace(
        "__WAAXALMA_API_URL__",
        PUBLIC_NORMALIZED_API_URL,
    )

    audio_input_manager_js = (
        load_audio_input_manager()
    )

    audio_output_manager_js = (
        load_audio_output_manager()
    )

    manager_script = (
        "<script>\n"
        + audio_input_manager_js
        + "\n</script>\n"
        + "<script>\n"
        + audio_output_manager_js
        + "\n</script>\n"
    )

    if "</head>" not in html:
        raise RuntimeError(
            "Realtime client HTML does not contain </head>: "
            f"{client_file}"
        )

    html = html.replace(
        "</head>",
        manager_script + "</head>",
        1,
    )

    return html


