from pathlib import Path
from typing import Any

import requests
import streamlit as st
import streamlit.components.v1 as components

from config import API_URL


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Waaxalma",
    page_icon="🎙️",
    layout="centered",
)

NORMALIZED_API_URL = API_URL.rstrip("/")

DEFAULT_TARGET_LANGUAGE = "English"

TARGET_LANGUAGES = [
    "English",
    "French",
    "Spanish",
    "Wolof",
]

REQUEST_TIMEOUT_SECONDS = 120

STREAMLIT_DIR = Path(__file__).resolve().parent

REALTIME_CLIENT_FILE = (
    STREAMLIT_DIR
    / "realtime_client.html"
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
            f"Erreur HTTP {response.status_code}: "
            f"{response.text or 'Réponse invalide du serveur.'}"
        )

    detail = body.get("detail")

    if isinstance(detail, dict):
        code = detail.get(
            "code",
            "API_ERROR",
        )

        message = detail.get(
            "message",
            "Une erreur est survenue pendant le traitement.",
        )

        return f"{code} — {message}"

    if isinstance(detail, str):
        return detail

    return (
        f"Erreur HTTP {response.status_code}."
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
        f"{NORMALIZED_API_URL}/"
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
            "Le backend a retourné "
            "une réponse JSON invalide."
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
            "Réponse incomplète du backend. "
            "Champs manquants : "
            f"{', '.join(sorted(missing_fields))}."
        )

    return result


# ---------------------------------------------------------------------------
# Realtime helpers
# ---------------------------------------------------------------------------

def load_realtime_client() -> str:
    if not REALTIME_CLIENT_FILE.exists():
        raise FileNotFoundError(
            "Realtime client not found: "
            f"{REALTIME_CLIENT_FILE}"
        )

    html = (
        REALTIME_CLIENT_FILE
        .read_text(
            encoding="utf-8"
        )
    )

    # Allows realtime_client.html to avoid
    # hardcoding http://127.0.0.1:8000.
    html = html.replace(
        "__WAAXALMA_API_URL__",
        NORMALIZED_API_URL,
    )

    return html


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("🎙️ Waaxalma")

st.caption(
    "Parle dans ta langue, "
    "Waaxalma interprète et parle pour toi."
)

st.divider()


# ---------------------------------------------------------------------------
# Main modes
# ---------------------------------------------------------------------------

standard_tab, realtime_tab = st.tabs(
    [
        "🎙️ Interprétation",
        "⚡ Traduction en direct",
    ]
)


# ===========================================================================
# STANDARD MODE
# ===========================================================================

with standard_tab:

    st.subheader(
        "Interprétation standard"
    )

    st.caption(
        "Pipeline complet : transcription → contexte → "
        "traduction → qualité → synthèse vocale."
    )


    st.selectbox(
        "Langue cible",
        options=TARGET_LANGUAGES,
        key="target_language",
        help=(
            "Langue dans laquelle Waaxalma "
            "doit interpréter le message."
        ),
    )


    audio_widget_key = (
        "voice_recording_"
        f"{st.session_state.audio_widget_version}"
    )


    audio_value = st.audio_input(
        "Enregistre ta voix",
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
            "Interpréter",
            type="primary",
            disabled=(
                audio_value is None
            ),
            use_container_width=True,
        )


    with button_right:
        st.button(
            "Réinitialiser",
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
                "Waaxalma interprète "
                "votre message..."
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
                "Le délai maximal a été dépassé. "
                "Le service met trop de temps "
                "à répondre."
            )

        except requests.ConnectionError:
            st.session_state.request_error = (
                "Impossible de joindre le backend "
                "Waaxalma. Vérifie que FastAPI "
                "est démarré."
            )

        except requests.RequestException as exc:
            st.session_state.request_error = (
                "Erreur de communication avec "
                f"le backend : {exc}"
            )

        except RuntimeError as exc:
            st.session_state.request_error = (
                str(exc)
            )

        except Exception:
            st.session_state.request_error = (
                "Une erreur inattendue est survenue."
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
            "Interprétation terminée.",
            icon="✅",
        )

        st.subheader(
            "Résultat"
        )


        source_tab, interpretation_tab = (
            st.tabs(
                [
                    "Texte détecté",
                    "Interprétation",
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
                "Audio interprété"
            )

            st.audio(
                build_audio_url(
                    audio_url
                )
            )

        else:
            st.info(
                "Aucun fichier audio "
                "n’a été retourné "
                "par le backend."
            )


        quality = result.get(
            "quality"
        )


        if quality is not None:
            with st.expander(
                "Qualité"
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
                "Informations techniques"
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
        "Traduction en direct"
    )

    st.caption(
        "Le microphone est transmis en temps réel "
        "au moteur de traduction. "
        "L’audio traduit et le texte sont produits "
        "pendant que tu parles."
    )

    st.info(
        "Le mode Live privilégie la faible latence. "
        "Il n’utilise pas le pipeline Context / Quality "
        "du mode standard.",
        icon="⚡",
    )

    try:
        realtime_html = (
            load_realtime_client()
        )

        components.html(
            realtime_html,
            height=330,
            scrolling=False,
        )

    except FileNotFoundError as exc:
        st.error(
            str(exc),
            icon="⚠️",
        )

        st.code(
            "streamlit/realtime_client.html",
            language=None,
        )