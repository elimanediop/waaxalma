import streamlit as st

def render_settings_panel(target_languages, loaders):
    with st.sidebar:
        st.header('Settings')
        mode = st.radio('Workspace mode', ['Standard', 'Direct', 'Enhanced'], key='workspace_mode')
        available_languages = target_languages if mode == 'Standard' else ['English', 'French', 'Spanish']
        if st.session_state.get('target_language') not in available_languages:
            st.session_state.target_language = 'English'
        st.selectbox('Target language', available_languages, key='target_language')
        if mode != 'Standard':
            st.session_state.realtime_mode = mode
            if mode == 'Enhanced':
                st.selectbox('Source language', ['French', 'Auto', 'English', 'Spanish'], key='source_language')
                st.text_input('Terminology', key='terminology', help='Comma-separated names and terms.')
            st.caption('Stop live interpretation before changing settings. Changes reload the browser client.')
        st.subheader('Audio devices')
        st.caption('Browser selections are saved locally and shared by the audio clients.')
        selected_device = st.selectbox('Device settings', [title for title, _, _ in loaders], key='device_settings_panel')
        loader = next(loader for title, loader, _ in loaders if title == selected_device)
        try:
            st.iframe(loader(), height='content', width='stretch')
        except (FileNotFoundError, RuntimeError) as exc:
            st.warning(str(exc))
        return mode
