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







from ui.assets import (
    REALTIME_CLIENT_FILE,
    REALTIME_ENHANCED_CLIENT_FILE,
    AUDIO_INPUT_MANAGER_FILE,
    AUDIO_INPUT_SELECTOR_FILE,
    AUDIO_OUTPUT_MANAGER_FILE,
    AUDIO_OUTPUT_SELECTOR_FILE,
    AUDIO_MONITOR_SELECTOR_FILE,
    CONFERENCE_INPUT_MANAGER_FILE,
    CONFERENCE_INPUT_SELECTOR_FILE,
    CONFERENCE_TRANSLATION_CLIENT_FILE,
    FULL_DUPLEX_CONTROLLER_FILE,
    STANDARD_AUDIO_PLAYER_FILE,
    load_audio_input_manager,
    load_audio_input_selector,
    load_audio_output_manager,
    load_audio_output_selector,
    load_audio_monitor_selector,
    load_conference_input_manager,
    load_conference_input_selector,
    load_conference_translation_client,
    load_full_duplex_controller,
    load_standard_audio_player,
    load_realtime_client,
)
STREAMLIT_DIR = Path(__file__).resolve().parent

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




# ---------------------------------------------------------------------------

# UI theme

# ---------------------------------------------------------------------------


st.markdown('<style>' + (STREAMLIT_DIR / 'assets/css/app.css').read_text(encoding='utf-8') + '</style>', unsafe_allow_html=True)


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


from ui.settings_panel import render_settings_panel
workspace_mode = render_settings_panel(TARGET_LANGUAGES, [
    ('Microphone', load_audio_input_selector, 170),
    ('Conference output', load_audio_output_selector, 170),
    ('Local monitor', load_audio_monitor_selector, 175),
    ('Conference input', load_conference_input_selector, 210),
])

st.markdown("### Workspace")

st.caption(
    "Use Standard Interpretation for request/response processing, "
    "or Live Translation for realtime Direct / Enhanced sessions."
)


# ===========================================================================

# STANDARD MODE

# ===========================================================================



if workspace_mode == 'Standard':



    st.subheader(

        "Standard Interpretation"

    )



    st.caption(

        "Full pipeline: transcription → context → "

        "translation → quality → speech synthesis."

    )





    audio_widget_key = (

        "voice_recording_"

        f"{st.session_state.audio_widget_version}"

    )


    with st.container():

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


if workspace_mode != 'Standard':

    st.subheader(
        "Live Translation"
    )

    realtime_mode = workspace_mode

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

        from ui.workspace import configure_live_client
        realtime_html = configure_live_client(
            realtime_html, target_language=st.session_state.target_language,
            source_language=st.session_state.get('source_language', 'French'),
            terminology=st.session_state.get('terminology', ''),
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


with st.expander("Experimental conferencing", expanded=False):
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


