import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Waaxalma", page_icon="🎙️")

st.title("🎙️ Waaxalma")
st.caption("Parle dans ta langue, Waaxalma parle pour toi en anglais.")

target_language = st.selectbox(
    "Langue cible",
    ["English", "French", "Spanish", "Wolof"],
    index=0,
)

audio_value = st.audio_input("Enregistre ta voix", sample_rate=16000)

if audio_value:
    st.audio(audio_value)

    if st.button("Interpréter"):
        files = {
            "file": ("recording.wav", audio_value.getvalue(), "audio/wav")
        }

        data = {
            "target_language": target_language
        }

        with st.spinner("Waaxalma interprète..."):
            response = requests.post(
                f"{API_URL}/api/voice/interpret",
                files=files,
                data=data,
                timeout=120,
            )

        if response.status_code != 200:
            st.error(response.text)
        else:
            result = response.json()

            st.subheader("Texte détecté")
            st.write(result["source_text"])

            st.subheader("Interprétation")
            st.write(result["interpreted_text"])

            audio_url = f"{API_URL}{result['audio_url']}"
            st.audio(audio_url)