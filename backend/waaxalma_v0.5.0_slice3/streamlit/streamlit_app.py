from pathlib import Path

import json

from typing import Any



import requests

import streamlit as st




from config import API_URL, PUBLIC_API_URL, CLIENT_ID, REQUEST_TIMEOUT_SECONDS





# ---------------------------------------------------------------------------

# Configuration

# ---------------------------------------------------------------------------



st.set_page_config(

    page_title="Waaxalma",

    page_icon="🎙️",

    layout="wide",

)



NORMALIZED_API_URL = API_URL.rstrip("/")
PUBLIC_NORMALIZED_API_URL = PUBLIC_API_URL.rstrip("/")



DEFAULT_TARGET_LANGUAGE = "English"



TARGET_LANGUAGES = [

    "English",

    "French",

    "Spanish",

    "Wolof",

]







STREAMLIT_DIR = Path(__file__).resolve().parent



REALTIME_CLIENT_FILE = (

    STREAMLIT_DIR

    / "realtime_client.html"

)


REALTIME_ENHANCED_CLIENT_FILE = (

    STREAMLIT_DIR

    / "realtime_enhanced_client.html"

)







AUDIO_INPUT_MANAGER_FILE = (
    STREAMLIT_DIR
    / "audio_input_manager.js"
)

AUDIO_INPUT_SELECTOR_FILE = (
    STREAMLIT_DIR
    / "audio_input_selector.html"
)


AUDIO_OUTPUT_MANAGER_FILE = (
    STREAMLIT_DIR
    / "audio_output_manager.js"
)

AUDIO_OUTPUT_SELECTOR_FILE = (
    STREAMLIT_DIR
    / "audio_output_selector.html"
)

AUDIO_MONITOR_SELECTOR_FILE = (
    STREAMLIT_DIR
    / "audio_monitor_selector.html"
)

CONFERENCE_INPUT_MANAGER_FILE = (
    STREAMLIT_DIR
    / "conference_input_manager.js"
)

CONFERENCE_INPUT_SELECTOR_FILE = (
    STREAMLIT_DIR
    / "conference_input_selector.html"
)

CONFERENCE_TRANSLATION_CLIENT_FILE = (
    STREAMLIT_DIR
    / "conference_translation_client.html"
)

FULL_DUPLEX_CONTROLLER_FILE = (
    STREAMLIT_DIR
    / "full_duplex_controller.html"
)


STANDARD_AUDIO_PLAYER_FILE = (
    STREAMLIT_DIR
    / "standard_audio_player.html"
)
# ---------------------------------------------------------------------------

# Session state

# ---------------------------------------------------------------------------



def initialize_state() -> None:

    defaults: dict[str, Any] = {

        "audio_widget_version": 0,

        "target_language": DEFAULT_TARGET_LANGUAGE,

        "interpretation_result": None,

        "request_error": None,

        "realtime_mode": "Direct",

    }



    for key, value in defaults.items():

        if key not in st.session_state:

            st.session_state[key] = value





def reset_interface() -> None:

    """

    Reset the current recording, result, error and selected language.



    Incrementing the widget version gives st.audio_input a new key,

    which recreates the widget without its previous recording.

    """

    st.session_state.audio_widget_version += 1



    st.session_state.target_language = (

        DEFAULT_TARGET_LANGUAGE

    )



    st.session_state.interpretation_result = None

    st.session_state.request_error = None





initialize_state()





# ---------------------------------------------------------------------------

# API helpers

# ---------------------------------------------------------------------------



def extract_api_error(

    response: requests.Response,

) -> str:

    """

    Extract a readable error from Waaxalma's normalized API response.

    """

    try:

        body = response.json()



    except ValueError:

        return (

            f"HTTP error {response.status_code}: "

            f"{response.text or 'Invalid server response.'}"

        )



    detail = body.get("detail")



    if isinstance(detail, dict):

        code = detail.get(

            "code",

            "API_ERROR",

        )



        message = detail.get(

            "message",

            "An error occurred while processing the request.",

        )



        return f"{code} — {message}"



    if isinstance(detail, str):

        return detail



    return (

        f"HTTP error {response.status_code}."

    )





def build_audio_url(

    audio_url: str,

) -> str:

    if audio_url.startswith(

        (

            "http://",

            "https://",

        )

    ):

        return audio_url



    return (

        f"{PUBLIC_NORMALIZED_API_URL}/"

        f"{audio_url.lstrip('/')}"

    )





def call_voice_interpretation(

    audio_bytes: bytes,

    target_language: str,

) -> dict[str, Any]:

    files = {

        "file": (

            "recording.wav",

            audio_bytes,

            "audio/wav",

        )

    }



    data = {

        "target_language":

            target_language,

    }



    response = requests.post(

        (

            f"{NORMALIZED_API_URL}"

            "/api/voice/interpret"

        ),

        headers={"X-Client-Id": CLIENT_ID},

        files=files,

        data=data,

        timeout=REQUEST_TIMEOUT_SECONDS,

    )



    if not response.ok:

        raise RuntimeError(

            extract_api_error(

                response

            )

        )



    try:

        result = response.json()



    except ValueError as exc:

        raise RuntimeError(

            "The backend returned "

            "an invalid JSON response."

        ) from exc



    required_fields = {

        "source_text",

        "interpreted_text",

    }



    missing_fields = (

        required_fields.difference(

            result

        )

    )



    if missing_fields:

        raise RuntimeError(

            "Incomplete backend response. "

            "Missing fields: "

            f"{', '.join(sorted(missing_fields))}."

        )



    return result





# ---------------------------------------------------------------------------

# Realtime helpers

# ---------------------------------------------------------------------------




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

    return AUDIO_INPUT_MANAGER_FILE.read_text(
        encoding="utf-8"
    )


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

    html = AUDIO_INPUT_SELECTOR_FILE.read_text(
        encoding="utf-8"
    )

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

    return AUDIO_OUTPUT_MANAGER_FILE.read_text(
        encoding="utf-8"
    )


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

    html = AUDIO_OUTPUT_SELECTOR_FILE.read_text(
        encoding="utf-8"
    )

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

    html = AUDIO_MONITOR_SELECTOR_FILE.read_text(
        encoding="utf-8"
    )

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

    return CONFERENCE_INPUT_MANAGER_FILE.read_text(
        encoding="utf-8"
    )


def load_conference_input_selector() -> str:
    """Load the Slice 3 conference-input selector and inject its manager."""
    if not CONFERENCE_INPUT_SELECTOR_FILE.exists():
        raise FileNotFoundError(
            "Conference input selector not found: "
            f"{CONFERENCE_INPUT_SELECTOR_FILE}"
        )

    html = CONFERENCE_INPUT_SELECTOR_FILE.read_text(
        encoding="utf-8"
    )

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

    html = CONFERENCE_TRANSLATION_CLIENT_FILE.read_text(
        encoding="utf-8"
    )

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

    html = FULL_DUPLEX_CONTROLLER_FILE.read_text(
        encoding="utf-8"
    )

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

    html = STANDARD_AUDIO_PLAYER_FILE.read_text(
        encoding="utf-8"
    )

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

    html = client_file.read_text(
        encoding="utf-8"
    )

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


# ---------------------------------------------------------------------------

# UI theme

# ---------------------------------------------------------------------------


st.markdown(
    """
    <style>
        .block-container {
            max-width: 1440px;
            padding-top: 1.5rem;
            padding-bottom: 3rem;
        }

        [data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 0.5rem;
        }

        [data-testid="stTabs"] [data-baseweb="tab"] {
            height: 2.75rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }

        [data-testid="stExpander"] {
            border-radius: 12px;
        }

        .waaxalma-hero {
            padding: 1.1rem 1.25rem;
            margin-bottom: 1rem;
            border: 1px solid rgba(128, 128, 128, 0.20);
            border-radius: 14px;
        }

        .waaxalma-hero-title {
            margin: 0;
            font-size: 1.85rem;
            font-weight: 750;
            line-height: 1.1;
        }

        .waaxalma-hero-subtitle {
            margin-top: 0.35rem;
            opacity: 0.72;
            font-size: 0.96rem;
        }

        .waaxalma-section-note {
            margin-top: -0.25rem;
            margin-bottom: 0.5rem;
            opacity: 0.68;
            font-size: 0.88rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------

# Header

# ---------------------------------------------------------------------------


st.markdown(
    """
    <div class="waaxalma-hero">
        <div class="waaxalma-hero-title">🎙️ Waaxalma</div>
        <div class="waaxalma-hero-subtitle">
            Speak in your language. Waaxalma interprets and speaks for you.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)



# ---------------------------------------------------------------------------
# Audio workspace — v0.4.4
# ---------------------------------------------------------------------------


with st.expander(
    "🎛️ Audio Devices & Conferencing",
    expanded=True,
):
    st.markdown(
        '<div class="waaxalma-section-note">'
        "Configure browser audio devices once; selections are persisted "
        "locally and reused by the realtime clients."
        "</div>",
        unsafe_allow_html=True,
    )

    (
        input_device_tab,
        conference_output_tab,
        local_monitor_tab,
        conference_input_tab,
    ) = st.tabs(
        [
            "🎤 Microphone",
            "🔊 Conference Output",
            "🎧 Local Monitor",
            "🎙️ Conference Input",
        ]
    )

    with input_device_tab:
        try:
            audio_input_selector_html = (
                load_audio_input_selector()
            )

            st.iframe(
                audio_input_selector_html,
                height=150,
                width="stretch",
            )

        except (
            FileNotFoundError,
            RuntimeError,
        ) as exc:
            st.warning(
                str(exc),
                icon="🎤",
            )

    with conference_output_tab:
        try:
            audio_output_selector_html = (
                load_audio_output_selector()
            )

            st.iframe(
                audio_output_selector_html,
                height=145,
                width="stretch",
            )

        except (
            FileNotFoundError,
            RuntimeError,
        ) as exc:
            st.warning(
                str(exc),
                icon="🔊",
            )

    with local_monitor_tab:
        try:
            audio_monitor_selector_html = (
                load_audio_monitor_selector()
            )

            st.iframe(
                audio_monitor_selector_html,
                height=155,
                width="stretch",
            )

        except (
            FileNotFoundError,
            RuntimeError,
        ) as exc:
            st.warning(
                str(exc),
                icon="🎧",
            )

    with conference_input_tab:
        st.caption(
            "Use a dedicated virtual-cable recording endpoint for "
            "remote participant audio. Slice 4 adds inbound streaming "
            "STT, translation and TTS using the existing Enhanced backend."
        )

        st.markdown("#### Device & Signal Check")

        try:
            conference_input_selector_html = (
                load_conference_input_selector()
            )

            st.iframe(
                conference_input_selector_html,
                height=185,
                width="stretch",
            )

        except (
            FileNotFoundError,
            RuntimeError,
        ) as exc:
            st.warning(
                str(exc),
                icon="🎙️",
            )

        st.markdown("#### Inbound Translation")

        st.caption(
            "Stop the diagnostic capture above before starting inbound "
            "translation. Translated remote speech is routed only to the "
            "selected Local Monitor device."
        )

        try:
            conference_translation_client_html = (
                load_conference_translation_client()
            )

            st.iframe(
                conference_translation_client_html,
                height=390,
                width="stretch",
            )

        except (
            FileNotFoundError,
            RuntimeError,
        ) as exc:
            st.warning(
                str(exc),
                icon="🌐",
            )


st.divider()


# ---------------------------------------------------------------------------

# Main modes

# ---------------------------------------------------------------------------



st.markdown("### Full Duplex Conferencing")

st.caption(
    "Start and stop outbound + inbound interpretation together. "
    "Outbound uses the currently selected Live Translation mode."
)

try:
    full_duplex_controller_html = (
        load_full_duplex_controller(
            st.session_state.realtime_mode
        )
    )

    st.iframe(
        full_duplex_controller_html,
        height=145,
        width="stretch",
    )

except (FileNotFoundError, RuntimeError) as exc:
    st.warning(
        str(exc),
        icon="🔁",
    )


st.markdown("### Workspace")

st.caption(
    "Use Standard Interpretation for request/response processing, "
    "or Live Translation for realtime Direct / Enhanced sessions."
)


standard_tab, realtime_tab = st.tabs(

    [

        "🎙️ Interpretation",

        "⚡ Live Translation",

    ]

)





# ===========================================================================

# STANDARD MODE

# ===========================================================================



with standard_tab:



    st.subheader(

        "Standard Interpretation"

    )



    st.caption(

        "Full pipeline: transcription → context → "

        "translation → quality → speech synthesis."

    )





    standard_controls_left, standard_controls_right = (
        st.columns(
            [1, 2],
            gap="large",
        )
    )


    with standard_controls_left:

        st.selectbox(

            "Target language",

            options=TARGET_LANGUAGES,

            key="target_language",

            help=(

                "Language into which Waaxalma "

                "should interpret the message."

            ),

        )


    audio_widget_key = (

        "voice_recording_"

        f"{st.session_state.audio_widget_version}"

    )


    with standard_controls_right:

        audio_value = st.audio_input(

            "Record your voice",

            sample_rate=16000,

            key=audio_widget_key,

        )





    if audio_value is not None:

        st.audio(

            audio_value

        )





    button_left, button_right = (

        st.columns(2)

    )





    with button_left:

        interpret_clicked = st.button(

            "Interpret",

            type="primary",

            disabled=(

                audio_value is None

            ),

            use_container_width=True,

        )





    with button_right:

        st.button(

            "Reset",

            on_click=reset_interface,

            use_container_width=True,

        )





    # -----------------------------------------------------------------------

    # Request execution

    # -----------------------------------------------------------------------



    if (

        interpret_clicked

        and audio_value is not None

    ):

        st.session_state.interpretation_result = (

            None

        )



        st.session_state.request_error = (

            None

        )



        try:

            with st.spinner(

                "Waaxalma is interpreting "

                "your message..."

            ):

                result = (

                    call_voice_interpretation(

                        audio_bytes=(

                            audio_value

                            .getvalue()

                        ),

                        target_language=(

                            st.session_state

                            .target_language

                        ),

                    )

                )



            st.session_state.interpretation_result = (

                result

            )



        except requests.Timeout:

            st.session_state.request_error = (

                "The request timed out. "

                "The service is taking too long "

                "to respond."

            )



        except requests.ConnectionError:

            st.session_state.request_error = (

                "Unable to reach the Waaxalma backend. "

                "Make sure FastAPI "

                "is running."

            )



        except requests.RequestException as exc:

            st.session_state.request_error = (

                "Communication error with "

                f"the backend: {exc}"

            )



        except RuntimeError as exc:

            st.session_state.request_error = (

                str(exc)

            )



        except Exception:

            st.session_state.request_error = (

                "An unexpected error occurred."

            )





    # -----------------------------------------------------------------------

    # Error display

    # -----------------------------------------------------------------------



    if st.session_state.request_error:

        st.error(

            st.session_state.request_error,

            icon="⚠️",

        )





    # -----------------------------------------------------------------------

    # Result display

    # -----------------------------------------------------------------------



    result = (

        st.session_state

        .interpretation_result

    )





    if result:

        st.success(

            "Interpretation complete.",

            icon="✅",

        )



        st.subheader(

            "Result"

        )





        source_tab, interpretation_tab = (

            st.tabs(

                [

                    "Detected text",

                    "Interpretation",

                ]

            )

        )





        with source_tab:

            st.write(

                result[

                    "source_text"

                ]

            )





        with interpretation_tab:

            st.write(

                result[

                    "interpreted_text"

                ]

            )





        audio_url = result.get(

            "audio_url"

        )





        if audio_url:

            st.subheader(

                "Interpreted audio"

            )



            interpreted_audio_url = (

                build_audio_url(

                    audio_url

                )

            )


            try:

                standard_audio_player_html = (

                    load_standard_audio_player(

                        interpreted_audio_url

                    )

                )


                st.iframe(

                    standard_audio_player_html,

                    height=70,

                    width="stretch",

                )


            except (

                FileNotFoundError,

                RuntimeError,

            ) as exc:

                st.warning(

                    str(exc),

                    icon="🔊",

                )


                # Availability fallback only.
                # This fallback uses the browser default output.
                st.audio(

                    interpreted_audio_url

                )



        else:

            st.info(

                "No audio file "

                "was returned "

                "by the backend."

            )





        quality = result.get(

            "quality"

        )





        if quality is not None:

            with st.expander(

                "Quality"

            ):

                st.write(

                    "Accepted:",

                    quality.get(

                        "accepted"

                    ),

                )



                st.write(

                    "Score:",

                    quality.get(

                        "score"

                    ),

                )



                issues = quality.get(

                    "issues",

                    [],

                )



                if issues:

                    st.write(

                        "Issues:"

                    )



                    for issue in issues:

                        st.write(

                            f"- {issue}"

                        )



                metadata = quality.get(

                    "metadata"

                )



                if metadata:

                    st.json(

                        metadata

                    )





        request_id = result.get(

            "request_id"

        )





        if request_id:

            with st.expander(

                "Technical information"

            ):

                st.code(

                    (

                        "Request ID: "

                        f"{request_id}"

                    ),

                    language=None,

                )





# ===========================================================================

# REALTIME MODE

# ===========================================================================


with realtime_tab:

    st.subheader(
        "Live Translation"
    )

    realtime_mode = st.radio(
        "Realtime mode",
        options=[
            "Direct",
            "Enhanced",
        ],
        key="realtime_mode",
        horizontal=True,
        help=(
            "Direct prioritizes minimum latency over WebRTC. "
            "Enhanced adds source transcription, terminology, "
            "streaming translation, and streaming speech synthesis."
        ),
    )

    if realtime_mode == "Direct":
        st.caption(
            "The microphone is streamed in realtime "
            "to the translation engine. "
            "Translated audio and text are produced "
            "while you speak."
        )

        st.info(
            "Direct mode prioritizes low latency. "
            "It does not use the Context / Quality pipeline "
            "from Standard mode.",
            icon="⚡",
        )

        realtime_client_file = (
            REALTIME_CLIENT_FILE
        )

        realtime_client_height = 330

    else:
        st.caption(
            "Enhanced mode combines streaming source transcription, "
            "context / terminology, streaming translation, "
            "and streaming speech synthesis."
        )

        st.info(
            "Enhanced mode exposes the source transcript "
            "and applies terminology before "
            "speech synthesis. It may have higher latency "
            "than Direct mode.",
            icon="🧩",
        )

        realtime_client_file = (
            REALTIME_ENHANCED_CLIENT_FILE
        )

        realtime_client_height = 430

    try:
        realtime_html = (
            load_realtime_client(
                realtime_client_file
            )
        )

        st.iframe(
            realtime_html,
            height=realtime_client_height,
            width="stretch",
        )

    except FileNotFoundError as exc:
        st.error(
            str(exc),
            icon="⚠️",
        )

        st.code(
            (
                "streamlit/"
                f"{realtime_client_file.name}"
            ),
            language=None,
        )
