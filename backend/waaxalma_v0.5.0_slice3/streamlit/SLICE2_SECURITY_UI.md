# v0.5.0 Slice 2 — UI client identity fix

The client identity is `waaxalma-for-elimane` on every backend HTTP request:
standard voice interpretation, realtime Direct session creation and metrics,
Enhanced session creation, and inbound conference session creation.

Browser Enhanced/inbound WebSocket connections use
`?client_id=waaxalma-for-elimane`, supported by the Slice 2 backend. Browser
WebSocket constructors cannot set the X-Client-Id handshake header.
OpenAI WebRTC SDP calls keep their original provider authorization headers.

Keep this identity stable to retain access to sessions created with it.
Slice 3 now reads CLIENT_ID from the UI environment and injects it into the
three browser HTML clients through streamlit_app.py. See the root README.md.
No login or authentication platform is added.

Replace the streamlit directory with this archive's streamlit directory and
restart Streamlit. Refresh the browser page to reload the embedded clients.
Use with the v0.5.0 Slice 2 backend.
