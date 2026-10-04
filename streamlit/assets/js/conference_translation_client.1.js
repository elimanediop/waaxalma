
    // ------------------------------------------------------------
    // Configuration
    // ------------------------------------------------------------

    const WAAXALMA_CLIENT_ID = "__WAAXALMA_CLIENT_ID__";

    const WAAXALMA_API_URL =
        "__WAAXALMA_API_URL__";

    const OPENAI_REALTIME_URL =
        "https://api.openai.com/v1/realtime/calls";


    const DEBUG_ENHANCED =
        false;


    function debugLog(
        ...args
    ) {
        if (
            DEBUG_ENHANCED
        ) {
            console.debug(
                ...args
            );
        }
    }


    // ------------------------------------------------------------
    // Local VAD
    // ------------------------------------------------------------

    const SOURCE_VAD_RMS_THRESHOLD =
        0.012;

    const VAD_REQUIRED_FRAMES =
        3;

    const SILENCE_REQUIRED_FRAMES =
        16;

    const MIN_PLAYBACK_BUFFER_MS =
        20;


    /*
     * Inbound direction:
     * Conference Input -> Enhanced pipeline -> Local Monitor.
     *
     * The existing Enhanced playback path is intentionally rebound to the
     * Local Monitor key. Primary / Conference Output is never used here.
     */
    const AUDIO_OUTPUT_STORAGE_KEY =
        "waaxalma.monitorOutputDeviceId";

    const AUDIO_INPUT_STORAGE_KEY =
        "waaxalma.conferenceInputDeviceId";

    const PHYSICAL_INPUT_STORAGE_KEY =
        "waaxalma.audioInputDeviceId";

    const PRIMARY_CONFERENCE_OUTPUT_STORAGE_KEY =
        "waaxalma.audioOutputDeviceId";

    const MONITOR_OUTPUT_STORAGE_KEY =
        "waaxalma.monitorOutputDeviceId";

    const MONITOR_ENABLED_STORAGE_KEY =
        "waaxalma.monitorEnabled";


    const FULL_DUPLEX_COMMAND_KEY =
        "waaxalma.fullDuplex.command";

    const FULL_DUPLEX_DESIRED_KEY =
        "waaxalma.fullDuplex.desired";

    const FULL_DUPLEX_STATUS_KEY =
        "waaxalma.fullDuplex.inbound.status";

    const FULL_DUPLEX_MODE =
        "inbound";


    // ------------------------------------------------------------
    // DOM
    // ------------------------------------------------------------

    const sourceLanguageElement =
        document.getElementById(
            "sourceLanguage"
        );


    const targetLanguageElement =
        document.getElementById(
            "targetLanguage"
        );

    const terminologyElement =
        document.getElementById(
            "terminology"
        );

    const startButton =
        document.getElementById(
            "startButton"
        );

    const stopButton =
        document.getElementById(
            "stopButton"
        );

    const statusDot =
        document.getElementById(
            "statusDot"
        );

    const statusText =
        document.getElementById(
            "statusText"
        );

    const sourceTranscriptElement =
        document.getElementById(
            "sourceTranscript"
        );

    const translationTranscriptElement =
        document.getElementById(
            "translationTranscript"
        );

    const metricsElement =
        document.getElementById(
            "metrics"
        );


    // ------------------------------------------------------------
    // Runtime state
    // ------------------------------------------------------------

    let peerConnection = null;
    let openAIDataChannel = null;
    let backendSocket = null;
    let microphoneStream = null;

    let audioContext = null;
    let analyser = null;
    let vadTimer = null;

    let playbackAudioContext = null;
    let playbackStreamDestination = null;
    let playbackAudioElement = null;
    let audioOutputManager = null;
    let audioInputManager = null;

    let monitorOutputManager = null;
    let monitorAudioElement = null;

    let nextPlaybackTime = 0;
    let pcmCarryByte = null;

    let pendingPlaybackSamples =
        new Float32Array(0);

    let playbackSampleRate =
        24000;

    let started = false;
    let speechActive = false;
    let speechFrames = 0;
    let silenceFrames = 0;
    let audioTurnHasContent = false;

    let sourceTranscript = "";
    let sourceCommittedTranscript = "";
    let sourcePartialTranscript = "";

    let translationTranscript = "";

    let sessionStartedAt = null;
    let speechStartedAt = null;
    let speechEndDetectedAt = null;
    let firstSourceDeltaAt = null;
    let transcriptionCompletedAt = null;
    let commitSentAt = null;
    let firstTranslationAt = null;
    let firstAudioAt = null;

    let currentUtteranceSequence = 0;
    let activeMetricsSegmentSequence = null;

    let lastTranslationSegmentSequence =
        null;




    function publishFullDuplexStatus(
        state,
        message
    ) {
        try {
            localStorage.setItem(
                FULL_DUPLEX_STATUS_KEY,
                JSON.stringify(
                    {
                        state:
                            state || "stopped",

                        message:
                            message || "",

                        mode:
                            FULL_DUPLEX_MODE,

                        updatedAt:
                            Date.now(),
                    }
                )
            );
        }
        catch (_) {
        }
    }


    // ------------------------------------------------------------
    // UI helpers
    // ------------------------------------------------------------

    function setStatus(
        state,
        message
    ) {
        statusDot.className =
            "status-dot";

        if (state) {
            statusDot.classList.add(
                state
            );
        }

        statusText.textContent =
            message;

        publishFullDuplexStatus(
            state || "stopped",
            message
        );
    }


    function updateButtons() {
        startButton.disabled =
            started;

        stopButton.disabled =
            !started;
    }


    function resetTranscripts() {
        sourceTranscript = "";
        sourceCommittedTranscript = "";
        sourcePartialTranscript = "";

        translationTranscript = "";

        lastTranslationSegmentSequence =
            null;

        currentUtteranceSequence =
            0;

        activeMetricsSegmentSequence =
            null;

        sourceTranscriptElement.textContent =
            (
                "Start speaking to see "
                + "the source transcript."
            );

        sourceTranscriptElement.classList.add(
            "placeholder"
        );

        translationTranscriptElement.textContent =
            (
                "Translation will "
                + "appear here."
            );

        translationTranscriptElement.classList.add(
            "placeholder"
        );
    }


    function renderSourceTranscript() {
        const parts = [];

        if (sourceCommittedTranscript) {
            parts.push(
                sourceCommittedTranscript
            );
        }

        if (sourcePartialTranscript) {
            parts.push(
                sourcePartialTranscript
            );
        }

        sourceTranscript =
            parts.join(
                " "
            );

        sourceTranscriptElement.classList.remove(
            "placeholder"
        );

        sourceTranscriptElement.textContent =
            sourceTranscript;
    }


    function renderTranslationTranscript() {
        translationTranscriptElement.classList.remove(
            "placeholder"
        );

        translationTranscriptElement.textContent =
            translationTranscript;
    }


    function renderMetrics() {
        const parts = [];

        if (
            speechStartedAt !== null
            && firstSourceDeltaAt !== null
        ) {
            parts.push(
                (
                    "speech → transcript: "
                    + Math.round(
                        firstSourceDeltaAt
                        - speechStartedAt
                    )
                    + " ms"
                )
            );
        }

        if (
            speechEndDetectedAt !== null
            && transcriptionCompletedAt !== null
        ) {
            parts.push(
                (
                    "VAD-end → STT: "
                    + Math.round(
                        transcriptionCompletedAt
                        - speechEndDetectedAt
                    )
                    + " ms"
                )
            );
        }

        if (
            commitSentAt !== null
            && firstTranslationAt !== null
        ) {
            parts.push(
                (
                    "commit → translation: "
                    + Math.round(
                        firstTranslationAt
                        - commitSentAt
                    )
                    + " ms"
                )
            );
        }

        if (
            firstTranslationAt !== null
            && firstAudioAt !== null
        ) {
            parts.push(
                (
                    "translation → audio: "
                    + Math.round(
                        firstAudioAt
                        - firstTranslationAt
                    )
                    + " ms"
                )
            );
        }

        if (
            speechEndDetectedAt !== null
            && firstAudioAt !== null
        ) {
            parts.push(
                (
                    "VAD-end → audio: "
                    + Math.round(
                        firstAudioAt
                        - speechEndDetectedAt
                    )
                    + " ms"
                )
            );
        }

        metricsElement.textContent =
            parts.join(
                " · "
            );
    }


    // ------------------------------------------------------------
    // URL helpers
    // ------------------------------------------------------------

    function buildBackendWebSocketUrl() {
        const url =
            new URL(
                WAAXALMA_API_URL
            );

        const protocol =
            (
                url.protocol === "https:"
                ? "wss:"
                : "ws:"
            );

        return (
            protocol
            + "//"
            + url.host
            + "/api/realtime/enhanced/stream"
            + "?client_id="
            + encodeURIComponent(WAAXALMA_CLIENT_ID)
        );
    }


    // ------------------------------------------------------------
    // Backend session
    // ------------------------------------------------------------

    async function createEnhancedSession() {
        const sourceLanguage =
            sourceLanguageElement.value;

        const targetLanguage =
            targetLanguageElement.value;

        const rawTerminology =
            terminologyElement.value;

        const keywords = (
            rawTerminology
                .split(",")
                .map(
                    value =>
                        value.trim()
                )
                .filter(Boolean)
        );

        const payload = {
            target_language:
                targetLanguage,
        };

        if (
            sourceLanguage
            && sourceLanguage !== "auto"
        ) {
            payload.source_languages = [
                sourceLanguage
            ];
        }

        if (keywords.length > 0) {
            payload.keywords =
                keywords;

            payload.prompt =
                (
                    "The speaker may use the following "
                    + "names or technical terms. Preserve "
                    + "their canonical spelling when heard: "
                    + keywords.join(", ")
                    + "."
                );
        }

        debugLog(
            "[Inbound] creating STT session",
            {
                source_language:
                    sourceLanguage,

                target_language:
                    targetLanguage,

                keywords:
                    keywords,
            }
        );

        const response =
            await fetch(
                (
                    WAAXALMA_API_URL
                    + "/api/realtime/enhanced/session"
                ),
                {
                    method:
                        "POST",

                    headers: {
                        "X-Client-Id": WAAXALMA_CLIENT_ID,
                        "Content-Type":
                            "application/json",
                    },

                    body:
                        JSON.stringify(
                            payload
                        ),
                }
            );

        if (!response.ok) {
            let details = "";

            try {
                details =
                    await response.text();
            }
            catch (error) {
                debugLog(
                    error
                );
            }

            throw new Error(
                (
                    "Inbound session creation "
                    + "failed with HTTP "
                    + response.status
                    + (
                        details
                        ? ": " + details
                        : ""
                    )
                )
            );
        }

        return await response.json();
    }


    // ------------------------------------------------------------
    // Backend WebSocket
    // ------------------------------------------------------------

    async function connectBackendSocket() {
        const websocketUrl =
            buildBackendWebSocketUrl();

        backendSocket =
            new WebSocket(
                websocketUrl
            );

        await new Promise(
            (
                resolve,
                reject
            ) => {
                backendSocket.onopen =
                    resolve;

                backendSocket.onerror =
                    () => {
                        reject(
                            new Error(
                                (
                                    "Unable to connect "
                                    + "to Waaxalma "
                                    + "Inbound Enhanced WebSocket."
                                )
                            )
                        );
                    };
            }
        );

        backendSocket.onmessage =
            handleBackendEvent;

        backendSocket.onclose =
            () => {
                if (started) {
                    setStatus(
                        "error",
                        (
                            "Inbound backend "
                            + "connection closed"
                        )
                    );
                }
            };

        const terminology = (
            terminologyElement
                .value
                .split(",")
                .map(
                    item =>
                        item.trim()
                )
                .filter(Boolean)
        );

        backendSocket.send(
            JSON.stringify(
                {
                    type:
                        "session.start",

                    target_language:
                        targetLanguageElement.value,

                    terminology:
                        (
                            terminology.length > 0
                            ? terminology
                            : null
                        ),
                }
            )
        );

        await waitForBackendReady();
    }


    function waitForBackendReady() {
        return new Promise(
            (
                resolve,
                reject
            ) => {
                const timeout =
                    setTimeout(
                        () => {
                            reject(
                                new Error(
                                    (
                                        "Waaxalma Enhanced "
                                        + "session start timed out."
                                    )
                                )
                            );
                        },
                        5000
                    );

                const originalHandler =
                    backendSocket.onmessage;

                backendSocket.onmessage =
                    event => {
                        const payload =
                            JSON.parse(
                                event.data
                            );

                        if (
                            payload.type
                            === "session.ready"
                        ) {
                            clearTimeout(
                                timeout
                            );

                            backendSocket.onmessage =
                                handleBackendEvent;

                            resolve(
                                payload
                            );

                            return;
                        }

                        if (
                            payload.type
                            === "error"
                        ) {
                            clearTimeout(
                                timeout
                            );

                            reject(
                                new Error(
                                    payload.message
                                )
                            );

                            return;
                        }

                        if (originalHandler) {
                            originalHandler(
                                event
                            );
                        }
                    };
            }
        );
    }


    function handleBackendEvent(
        event
    ) {
        let payload;

        try {
            payload =
                JSON.parse(
                    event.data
                );
        }
        catch (error) {
            console.error(
                (
                    "[Inbound] Invalid "
                    + "backend event"
                ),
                error
            );

            return;
        }

        if (
            payload.type
            === "translation.delta"
        ) {
            if (payload.text) {
                const segmentSequence =
                    payload.metadata
                        ?.source_segment_sequence
                        ?? null;

                if (
                    firstTranslationAt
                    === null
                    && segmentSequence !== null
                    && segmentSequence
                        === activeMetricsSegmentSequence
                ) {
                    firstTranslationAt =
                        performance.now();

                    renderMetrics();
                }

                const displaySegmentSequence =
                    segmentSequence;


                if (
                    displaySegmentSequence !== null
                    && lastTranslationSegmentSequence
                        !== null
                    && displaySegmentSequence
                        !== lastTranslationSegmentSequence
                    && translationTranscript
                    && !translationTranscript.endsWith(
                        " "
                    )
                ) {
                    translationTranscript +=
                        " ";
                }


                translationTranscript +=
                    payload.text;


                if (
                    displaySegmentSequence !== null
                ) {
                    lastTranslationSegmentSequence =
                        displaySegmentSequence;
                }


                renderTranslationTranscript();
            }

            return;
        }

        if (
            payload.type
            === "audio.delta"
        ) {
            debugLog(
                "[Inbound] audio.delta",
                {
                    bytes_base64:
                        payload.audio
                            ? payload.audio.length
                            : 0,

                    is_final:
                        payload.is_final,

                    content_type:
                        payload.content_type,

                    sample_rate:
                        payload.sample_rate,

                    metadata:
                        payload.metadata,
                }
            );

            if (
                payload.audio
            ) {
                const audioSegmentSequence =
                    payload.metadata
                        ?.source_segment_sequence
                        ?? null;

                if (
                    firstAudioAt
                    === null
                    && audioSegmentSequence !== null
                    && audioSegmentSequence
                        === activeMetricsSegmentSequence
                ) {
                    firstAudioAt =
                        performance.now();

                    renderMetrics();
                }

                schedulePcmAudio(
                    payload.audio,
                    payload.sample_rate
                        || 24000
                );
            }

            if (
                payload.is_final
            ) {
                flushPcmAudio();

                if (
                    pcmCarryByte !== null
                ) {
                    console.warn(
                        (
                            "[Inbound] PCM stream ended "
                            + "with one unmatched byte."
                        )
                    );
                }

                pcmCarryByte =
                    null;
            }

            return;
        }


        if (
            payload.type
            === "error"
        ) {
            console.error(
                "[Inbound backend]",
                payload
            );

            setStatus(
                "error",
                (
                    payload.message
                    || "Inbound backend error"
                )
            );
        }
    }



    // ------------------------------------------------------------
    // Inbound routing safety — v0.4.4 Slice 4
    // ------------------------------------------------------------

    function validateInboundRouting() {
        const conferenceInputDeviceId =
            localStorage.getItem(
                AUDIO_INPUT_STORAGE_KEY
            ) || "";

        const physicalInputDeviceId =
            localStorage.getItem(
                PHYSICAL_INPUT_STORAGE_KEY
            ) || "";

        const localMonitorDeviceId =
            localStorage.getItem(
                AUDIO_OUTPUT_STORAGE_KEY
            ) || "";

        const primaryConferenceOutputDeviceId =
            localStorage.getItem(
                PRIMARY_CONFERENCE_OUTPUT_STORAGE_KEY
            ) || "";

        if (!conferenceInputDeviceId) {
            throw new Error(
                "Select an explicit Conference Input device first."
            );
        }

        if (!localMonitorDeviceId) {
            throw new Error(
                "Select an explicit Local Monitor device first."
            );
        }

        if (
            physicalInputDeviceId
            && conferenceInputDeviceId
                === physicalInputDeviceId
        ) {
            throw new Error(
                (
                    "Conference Input matches the physical microphone. "
                    + "Select the virtual cable carrying remote audio."
                )
            );
        }

        if (
            primaryConferenceOutputDeviceId
            && localMonitorDeviceId
                === primaryConferenceOutputDeviceId
        ) {
            throw new Error(
                (
                    "Local Monitor matches Primary / Conference Output. "
                    + "Select headphones as Local Monitor to avoid "
                    + "sending inbound translated audio back to Teams."
                )
            );
        }
    }


    // ------------------------------------------------------------
    // Explicit realtime audio input — v0.4.4 Slice 1
    // ------------------------------------------------------------

    async function ensureAudioInputManager() {
        if (
            !window.WaaxalmaConferenceInputManager
        ) {
            throw new Error(
                "WaaxalmaConferenceInputManager is not available. "
                + "Check Streamlit conference-input script injection."
            );
        }

        if (
            !audioInputManager
        ) {
            audioInputManager =
                new window
                    .WaaxalmaConferenceInputManager({
                        onDeviceUnavailable:
                            ({
                                previousDeviceId,
                            }) => {
                                localStorage
                                    .removeItem(
                                        AUDIO_INPUT_STORAGE_KEY
                                    );

                                console.warn(
                                    (
                                        "[Inbound] Conference Input "
                                        + "disappeared. Capture stopped."
                                    ),
                                    {
                                        previousDeviceId,
                                    }
                                );

                                setStatus(
                                    "error",
                                    "Conference Input disappeared"
                                );
                            },
                    });

            await audioInputManager
                .start();
        }

        await applyStoredAudioInput();

        return audioInputManager;
    }


    async function applyStoredAudioInput() {
        if (
            !audioInputManager
        ) {
            return;
        }

        const storedDeviceId =
            localStorage.getItem(
                AUDIO_INPUT_STORAGE_KEY
            ) || "";

        if (
            storedDeviceId
            === audioInputManager
                .selectedDeviceId
        ) {
            return;
        }

        await audioInputManager
            .setInputDevice(
                storedDeviceId
            );
    }


    // ------------------------------------------------------------
    // OpenAI transcription WebRTC
    // ------------------------------------------------------------

    async function connectTranscriptionWebRTC(
        clientSecret
    ) {
        peerConnection =
            new RTCPeerConnection();

        const inputManager =
            await ensureAudioInputManager();

        microphoneStream =
            await inputManager
                .startCapture();

        const audioTrack =
            microphoneStream
                .getAudioTracks()[0];

        peerConnection.addTrack(
            audioTrack,
            microphoneStream
        );

        openAIDataChannel =
            peerConnection.createDataChannel(
                "oai-events"
            );

        openAIDataChannel.onmessage =
            handleOpenAIEvent;

        openAIDataChannel.onerror =
            event => {
                console.error(
                    (
                        "[Inbound] OpenAI "
                        + "data channel error"
                    ),
                    event
                );
            };

        peerConnection.onconnectionstatechange =
            () => {
                debugLog(
                    (
                        "[Inbound] WebRTC state:"
                    ),
                    peerConnection
                        .connectionState
                );

                if (
                    peerConnection
                    .connectionState
                    === "connected"
                ) {
                    setStatus(
                        "live",
                        "Live"
                    );
                }

                if (
                    [
                        "failed",
                        "disconnected",
                    ].includes(
                        peerConnection
                            .connectionState
                    )
                    && started
                ) {
                    setStatus(
                        "error",
                        (
                            "Transcription "
                            + "connection lost"
                        )
                    );
                }
            };

        const offer =
            await peerConnection
                .createOffer();

        await peerConnection
            .setLocalDescription(
                offer
            );

        const response =
            await fetch(
                OPENAI_REALTIME_URL,
                {
                    method:
                        "POST",

                    headers: {
                        "Authorization":
                            (
                                "Bearer "
                                + clientSecret
                            ),

                        "Content-Type":
                            "application/sdp",
                    },

                    body:
                        offer.sdp,
                }
            );

        if (!response.ok) {
            throw new Error(
                (
                    "OpenAI WebRTC connection "
                    + "failed with HTTP "
                    + response.status
                )
            );
        }

        const answerSdp =
            await response.text();

        await peerConnection
            .setRemoteDescription(
                {
                    type:
                        "answer",

                    sdp:
                        answerSdp,
                }
            );

        startLocalVad(
            microphoneStream
        );
    }


    // ------------------------------------------------------------
    // OpenAI transcription events
    // ------------------------------------------------------------

    function handleOpenAIEvent(
        message
    ) {
        let event;

        try {
            event =
                JSON.parse(
                    message.data
                );
        }
        catch (error) {
            console.error(
                (
                    "[Inbound] Invalid "
                    + "OpenAI event"
                ),
                error
            );

            return;
        }

        debugLog(
            "[Enhanced OpenAI]",
            event
        );

        if (
            event.type
            === (
                "conversation.item."
                + "input_audio_transcription.delta"
            )
        ) {
            const delta =
                event.delta || "";

            if (!delta) {
                return;
            }

            if (
                firstSourceDeltaAt
                === null
            ) {
                firstSourceDeltaAt =
                    performance.now();

                renderMetrics();
            }

            sourcePartialTranscript +=
                delta;

            renderSourceTranscript();

            sendBackendEvent(
                {
                    type:
                        "transcript.delta",

                    delta:
                        delta,
                }
            );

            return;
        }

        if (
            event.type
            === (
                "conversation.item."
                + "input_audio_transcription.completed"
            )
        ) {
            const finalTranscript = (
                event.transcript
                || sourcePartialTranscript
                || ""
            ).trim();

            debugLog(
                (
                    "[Inbound] "
                    + "transcription completed"
                ),
                finalTranscript
            );

            const completedAt =
                performance.now();

            if (
                transcriptionCompletedAt
                === null
            ) {
                transcriptionCompletedAt =
                    completedAt;

                commitSentAt =
                    completedAt;

                renderMetrics();
            }

            if (finalTranscript) {
                if (
                    sourceCommittedTranscript
                    && !sourceCommittedTranscript.endsWith(
                        " "
                    )
                ) {
                    sourceCommittedTranscript +=
                        " ";
                }

                sourceCommittedTranscript +=
                    finalTranscript;
            }

            sourcePartialTranscript =
                "";

            renderSourceTranscript();

            currentUtteranceSequence +=
                1;

            activeMetricsSegmentSequence =
                currentUtteranceSequence;

            sendBackendEvent(
                {
                    type:
                        "transcript.commit",

                    text:
                        (
                            finalTranscript
                            || null
                        ),
                }
            );

            return;
        }


        if (
            event.type
            === "error"
        ) {
            console.error(
                "[Enhanced OpenAI]",
                event
            );

            setStatus(
                "error",
                (
                    event.error?.message
                    || "Realtime transcription error"
                )
            );
        }
    }


    function sendBackendEvent(
        payload
    ) {
        if (
            !backendSocket
            || backendSocket.readyState
                !== WebSocket.OPEN
        ) {
            console.warn(
                (
                    "[Inbound] Backend "
                    + "WebSocket is not open."
                )
            );

            return;
        }

        backendSocket.send(
            JSON.stringify(
                payload
            )
        );
    }


    // ------------------------------------------------------------
    // Local VAD
    // ------------------------------------------------------------

    function startLocalVad(
        stream
    ) {
        stopLocalVad();

        audioContext =
            new AudioContext();

        const source =
            audioContext
                .createMediaStreamSource(
                    stream
                );

        analyser =
            audioContext
                .createAnalyser();

        analyser.fftSize =
            1024;

        source.connect(
            analyser
        );

        const samples =
            new Float32Array(
                analyser.fftSize
            );

        vadTimer =
            window.setInterval(
                () => {
                    analyser
                        .getFloatTimeDomainData(
                            samples
                        );

                    let sumSquares = 0;

                    for (
                        let index = 0;
                        index < samples.length;
                        index += 1
                    ) {
                        const value =
                            samples[index];

                        sumSquares +=
                            value * value;
                    }

                    const rms =
                        Math.sqrt(
                            sumSquares
                            / samples.length
                        );

                    if (
                        rms
                        >= SOURCE_VAD_RMS_THRESHOLD
                    ) {
                        speechFrames += 1;
                        silenceFrames = 0;

                        if (
                            !speechActive
                            && speechFrames
                                >= VAD_REQUIRED_FRAMES
                        ) {
                            speechActive =
                                true;

                            audioTurnHasContent =
                                true;

                            speechStartedAt =
                                performance.now();

                            speechEndDetectedAt =
                                null;

                            firstSourceDeltaAt =
                                null;

                            transcriptionCompletedAt =
                                null;

                            commitSentAt =
                                null;

                            firstTranslationAt =
                                null;

                            firstAudioAt =
                                null;

                            activeMetricsSegmentSequence =
                                null;

                            renderMetrics();

                            debugLog(
                                (
                                    "[Inbound] "
                                    + "speech start"
                                ),
                                {
                                    rms:
                                        rms,
                                }
                            );
                        }
                    }
                    else {
                        speechFrames =
                            0;

                        if (speechActive) {
                            silenceFrames +=
                                1;

                            if (
                                silenceFrames
                                >= SILENCE_REQUIRED_FRAMES
                            ) {
                                speechActive =
                                    false;

                                silenceFrames =
                                    0;

                                if (
                                    speechEndDetectedAt
                                    === null
                                ) {
                                    speechEndDetectedAt =
                                        performance.now();

                                    renderMetrics();
                                }

                                commitOpenAIAudioTurn();
                            }
                        }
                    }
                },
                20
            );
    }


    function commitOpenAIAudioTurn() {
        if (!audioTurnHasContent) {
            return;
        }

        if (
            !openAIDataChannel
            || openAIDataChannel.readyState
                !== "open"
        ) {
            return;
        }

        audioTurnHasContent =
            false;

        debugLog(
            (
                "[Inbound] committing "
                + "OpenAI audio turn"
            )
        );

        openAIDataChannel.send(
            JSON.stringify(
                {
                    type:
                        "input_audio_buffer.commit",
                }
            )
        );
    }


    // ------------------------------------------------------------
    // Universal audio output — v0.4.3
    // ------------------------------------------------------------

    async function ensureAudioOutputManager() {
        if (
            !window.WaaxalmaAudioOutputManager
        ) {
            throw new Error(
                "WaaxalmaAudioOutputManager is not available. "
                + "Check Streamlit audio-output script injection."
            );
        }

        if (
            !audioOutputManager
        ) {
            audioOutputManager =
                new window
                    .WaaxalmaAudioOutputManager({
                        onFallback:
                            ({
                                previousDeviceId,
                            }) => {
                                localStorage
                                    .removeItem(
                                        AUDIO_OUTPUT_STORAGE_KEY
                                    );

                                console.warn(
                                    (
                                        "[Inbound] Selected audio "
                                        + "output disappeared. "
                                        + "Falling back to default."
                                    ),
                                    {
                                        previousDeviceId,
                                    }
                                );
                            },
                    });

            await audioOutputManager
                .start();
        }

        await applyStoredAudioOutput();

        return audioOutputManager;
    }


    async function applyStoredAudioOutput() {
        if (
            !audioOutputManager
        ) {
            return;
        }

        const storedDeviceId =
            localStorage.getItem(
                AUDIO_OUTPUT_STORAGE_KEY
            ) || "";

        if (
            storedDeviceId
            === audioOutputManager
                .selectedDeviceId
        ) {
            return;
        }

        try {
            await audioOutputManager
                .setOutputDevice(
                    storedDeviceId
                );
        }
        catch (error) {
            console.warn(
                (
                    "[Inbound] Unable to apply "
                    + "selected Local Monitor output. "
                    + "Falling back to default."
                ),
                error
            );

            localStorage.removeItem(
                AUDIO_OUTPUT_STORAGE_KEY
            );

            await audioOutputManager
                .resetToDefault();
        }
    }


    async function ensureEnhancedAudioOutput() {
        const manager =
            await ensureAudioOutputManager();

        const context =
            ensurePlaybackAudioContext();

        if (
            context.state
            === "suspended"
        ) {
            try {
                await context.resume();
            }
            catch (error) {
                console.warn(
                    (
                        "[Inbound] Could not resume "
                        + "playback AudioContext"
                    ),
                    error
                );
            }
        }

        if (
            !playbackStreamDestination
        ) {
            playbackStreamDestination =
                context
                    .createMediaStreamDestination();
        }

        if (
            !playbackAudioElement
        ) {
            playbackAudioElement =
                await manager
                    .createAudioElement({
                        autoplay:
                            true,

                        controls:
                            false,

                        muted:
                            false,
                    });

            await manager
                .attachMediaStream(
                    playbackAudioElement,
                    playbackStreamDestination
                        .stream
                );

            try {
                await playbackAudioElement
                    .play();
            }
            catch (error) {
                console.warn(
                    (
                        "[Inbound] Audio output "
                        + "playback could not start yet"
                    ),
                    error
                );
            }
        }

        await syncEnhancedLocalMonitor();

        return playbackStreamDestination;
    }


    function handleAudioOutputStorageChange(
        event
    ) {
        if (
            event.key
            !== AUDIO_OUTPUT_STORAGE_KEY
        ) {
            return;
        }

        applyStoredAudioOutput()
            .then(
                () =>
                    syncEnhancedLocalMonitor()
            )
            .catch(
                error => {
                    console.warn(
                        (
                            "[Inbound] Unable to apply "
                            + "changed audio output"
                        ),
                        error
                    );
                }
            );
    }



    // ------------------------------------------------------------
    // Independent local monitoring — v0.4.4 Slice 2
    // ------------------------------------------------------------

    function localMonitoringEnabled() {
        return (
            localStorage.getItem(
                MONITOR_ENABLED_STORAGE_KEY
            )
            === "true"
        );
    }


    function primaryOutputDeviceId() {
        return (
            localStorage.getItem(
                AUDIO_OUTPUT_STORAGE_KEY
            ) || ""
        );
    }


    function monitorOutputDeviceId() {
        return (
            localStorage.getItem(
                MONITOR_OUTPUT_STORAGE_KEY
            ) || ""
        );
    }


    function monitorConflictsWithPrimary() {
        return (
            monitorOutputDeviceId()
            === primaryOutputDeviceId()
        );
    }


    async function ensureMonitorOutputManager() {
        if (
            !window.WaaxalmaAudioOutputManager
        ) {
            throw new Error(
                "WaaxalmaAudioOutputManager is not available."
            );
        }

        if (
            !monitorOutputManager
        ) {
            monitorOutputManager =
                new window
                    .WaaxalmaAudioOutputManager({
                        onFallback:
                            ({
                                previousDeviceId,
                            }) => {
                                localStorage
                                    .removeItem(
                                        MONITOR_OUTPUT_STORAGE_KEY
                                    );

                                console.warn(
                                    (
                                        "[Inbound] Selected local "
                                        + "monitor disappeared. "
                                        + "Falling back to default."
                                    ),
                                    {
                                        previousDeviceId,
                                    }
                                );
                            },
                    });

            await monitorOutputManager
                .start();
        }

        const storedDeviceId =
            monitorOutputDeviceId();

        if (
            storedDeviceId
            !== monitorOutputManager
                .selectedDeviceId
        ) {
            await monitorOutputManager
                .setOutputDevice(
                    storedDeviceId
                );
        }

        return monitorOutputManager;
    }


    function releaseEnhancedMonitorAudio() {
        if (
            !monitorAudioElement
        ) {
            return;
        }

        try {
            if (
                monitorOutputManager
            ) {
                monitorOutputManager
                    .unregisterMediaElement(
                        monitorAudioElement
                    );
            }

            monitorAudioElement
                .pause();

            monitorAudioElement
                .srcObject =
                null;
        }
        catch (error) {
            debugLog(
                error
            );
        }

        monitorAudioElement =
            null;
    }


    async function syncEnhancedLocalMonitor() {
        /*
         * No secondary playback element is needed.
         * AUDIO_OUTPUT_STORAGE_KEY is already Local Monitor.
         */
        releaseEnhancedMonitorAudio();
    }


    function handleMonitorStorageChange(
        event
    ) {
        if (
            event.key
            !== MONITOR_OUTPUT_STORAGE_KEY
        ) {
            return;
        }

        applyStoredAudioOutput()
            .catch(
                error => {
                    console.warn(
                        "[Inbound] Unable to apply Local Monitor output",
                        error
                    );
                }
            );
    }


    // ------------------------------------------------------------
    // PCM audio playback
    // ------------------------------------------------------------

    function ensurePlaybackAudioContext() {
        if (!playbackAudioContext) {
            playbackAudioContext =
                new AudioContext();

            nextPlaybackTime =
                playbackAudioContext
                    .currentTime;
        }

        if (
            playbackAudioContext.state
            === "suspended"
        ) {
            playbackAudioContext
                .resume()
                .catch(
                    error => {
                        console.warn(
                            (
                                "[Inbound] Could not "
                                + "resume playback "
                                + "AudioContext"
                            ),
                            error
                        );
                    }
                );
        }

        return playbackAudioContext;
    }


    function decodeBase64Pcm16(
        base64Audio
    ) {
        const binary =
            atob(
                base64Audio
            );

        const incomingBytes =
            new Uint8Array(
                binary.length
            );

        for (
            let index = 0;
            index < binary.length;
            index += 1
        ) {
            incomingBytes[index] =
                binary.charCodeAt(
                    index
                );
        }

        let bytes;

        if (
            pcmCarryByte !== null
        ) {
            bytes =
                new Uint8Array(
                    incomingBytes.length + 1
                );

            bytes[0] =
                pcmCarryByte;

            bytes.set(
                incomingBytes,
                1
            );

            pcmCarryByte =
                null;
        }
        else {
            bytes =
                incomingBytes;
        }

        let usableLength =
            bytes.length;

        if (
            usableLength % 2 !== 0
        ) {
            pcmCarryByte =
                bytes[
                    usableLength - 1
                ];

            usableLength -=
                1;
        }

        if (
            usableLength === 0
        ) {
            return new Float32Array(
                0
            );
        }

        const sampleCount =
            usableLength / 2;

        const samples =
            new Float32Array(
                sampleCount
            );

        const view =
            new DataView(
                bytes.buffer,
                bytes.byteOffset,
                usableLength
            );

        for (
            let index = 0;
            index < sampleCount;
            index += 1
        ) {
            const pcmSample =
                view.getInt16(
                    index * 2,
                    true
                );

            samples[index] =
                (
                    pcmSample < 0
                    ? pcmSample / 32768
                    : pcmSample / 32767
                );
        }

        return samples;
    }


    function appendFloat32Samples(
        current,
        incoming
    ) {
        if (
            current.length === 0
        ) {
            return incoming;
        }

        const combined =
            new Float32Array(
                current.length
                + incoming.length
            );

        combined.set(
            current,
            0
        );

        combined.set(
            incoming,
            current.length
        );

        return combined;
    }


    function scheduleFloat32Audio(
        samples,
        sampleRate
    ) {
        if (
            samples.length === 0
        ) {
            return;
        }

        const context =
            ensurePlaybackAudioContext();

        const audioBuffer =
            context.createBuffer(
                1,
                samples.length,
                sampleRate
            );

        audioBuffer
            .getChannelData(0)
            .set(
                samples
            );

        const source =
            context.createBufferSource();

        source.buffer =
            audioBuffer;

        if (
            playbackStreamDestination
        ) {
            source.connect(
                playbackStreamDestination
            );
        }
        else {
            console.warn(
                (
                    "[Inbound] Local Monitor audio bridge "
                    + "is not initialized. "
                    + "Using default audio destination."
                )
            );

            source.connect(
                context.destination
            );
        }

        const minimumStartTime =
            context.currentTime
            + 0.02;

        if (
            nextPlaybackTime
            < minimumStartTime
        ) {
            nextPlaybackTime =
                minimumStartTime;
        }

        debugLog(
            "[Inbound] scheduling PCM audio",
            {
                samples:
                    samples.length,

                sample_rate:
                    sampleRate,

                duration_ms:
                    Math.round(
                        audioBuffer.duration
                        * 1000
                    ),

                start_at:
                    nextPlaybackTime,

                context_state:
                    context.state,
            }
        );

        source.start(
            nextPlaybackTime
        );

        nextPlaybackTime +=
            audioBuffer.duration;
    }


    function schedulePcmAudio(
        base64Audio,
        sampleRate
    ) {
        if (!base64Audio) {
            return;
        }

        playbackSampleRate =
            sampleRate;

        const samples =
            decodeBase64Pcm16(
                base64Audio
            );

        if (
            samples.length === 0
        ) {
            return;
        }

        pendingPlaybackSamples =
            appendFloat32Samples(
                pendingPlaybackSamples,
                samples
            );

        const minimumSamples =
            Math.ceil(
                sampleRate
                * (
                    MIN_PLAYBACK_BUFFER_MS
                    / 1000
                )
            );

        if (
            pendingPlaybackSamples.length
            < minimumSamples
        ) {
            return;
        }

        const samplesToPlay =
            pendingPlaybackSamples;

        pendingPlaybackSamples =
            new Float32Array(0);

        scheduleFloat32Audio(
            samplesToPlay,
            sampleRate
        );
    }


    function flushPcmAudio() {
        if (
            pendingPlaybackSamples.length
            === 0
        ) {
            return;
        }

        const samplesToPlay =
            pendingPlaybackSamples;

        pendingPlaybackSamples =
            new Float32Array(0);

        scheduleFloat32Audio(
            samplesToPlay,
            playbackSampleRate
        );
    }


    function resetAudioPlayback() {
        releaseEnhancedMonitorAudio();

        nextPlaybackTime =
            0;

        pcmCarryByte =
            null;

        pendingPlaybackSamples =
            new Float32Array(0);

        playbackSampleRate =
            24000;

        if (
            playbackAudioElement
        ) {
            try {
                if (
                    audioOutputManager
                ) {
                    audioOutputManager
                        .unregisterMediaElement(
                            playbackAudioElement
                        );
                }

                playbackAudioElement
                    .pause();

                playbackAudioElement
                    .srcObject =
                    null;
            }
            catch (error) {
                debugLog(
                    error
                );
            }
        }

        playbackAudioElement =
            null;

        playbackStreamDestination =
            null;

        if (
            playbackAudioContext
        ) {
            try {
                playbackAudioContext
                    .close();
            }
            catch (error) {
                debugLog(
                    error
                );
            }
        }

        playbackAudioContext =
            null;
    }


    // ------------------------------------------------------------
    // Lifecycle
    // ------------------------------------------------------------

    async function start() {
        if (started) {
            return;
        }

        try {
            validateInboundRouting();

            started =
                true;

            updateButtons();
            resetTranscripts();
            resetAudioPlayback();

            await ensureEnhancedAudioOutput();

            metricsElement.textContent =
                "";

            setStatus(
                "connecting",
                "Connecting..."
            );

            sessionStartedAt =
                performance.now();

            speechStartedAt =
                null;

            speechEndDetectedAt =
                null;

            firstSourceDeltaAt =
                null;

            transcriptionCompletedAt =
                null;

            commitSentAt =
                null;

            firstTranslationAt =
                null;

            firstAudioAt =
                null;

            lastTranslationSegmentSequence =
                null;

            const session =
                await createEnhancedSession();

            await connectBackendSocket();

            await connectTranscriptionWebRTC(
                session.client_secret
            );

            debugLog(
                (
                    "[Inbound] session started"
                ),
                {
                    provider:
                        session
                            .transcription_provider,

                    model:
                        session
                            .transcription_model,

                    target_language:
                        session
                            .target_language,
                }
            );
        }
        catch (error) {
            console.error(
                "[Inbound] Start failed",
                error
            );

            setStatus(
                "error",
                (
                    error.message
                    || "Unable to start"
                )
            );

            await stop();
        }
    }


    async function stop() {
        started =
            false;

        updateButtons();

        stopLocalVad();

        if (
            openAIDataChannel
            && openAIDataChannel.readyState
                === "open"
        ) {
            try {
                openAIDataChannel
                    .close();
            }
            catch (error) {
                debugLog(
                    error
                );
            }
        }

        openAIDataChannel =
            null;

        if (peerConnection) {
            try {
                peerConnection
                    .close();
            }
            catch (error) {
                debugLog(
                    error
                );
            }
        }

        peerConnection =
            null;

        if (microphoneStream) {
            for (
                const track
                of microphoneStream
                    .getTracks()
            ) {
                track.stop();
            }
        }

        microphoneStream =
            null;

        if (
            backendSocket
            && backendSocket.readyState
                === WebSocket.OPEN
        ) {
            try {
                backendSocket.close(
                    1000,
                    "Client stopped"
                );
            }
            catch (error) {
                debugLog(
                    error
                );
            }
        }

        backendSocket =
            null;

        resetAudioPlayback();

        if (
            audioOutputManager
        ) {
            try {
                await audioOutputManager
                    .stop();
            }
            catch (error) {
                debugLog(
                    error
                );
            }

            audioOutputManager =
                null;
        }

        if (
            audioInputManager
        ) {
            try {
                await audioInputManager
                    .stop();
            }
            catch (error) {
                debugLog(
                    error
                );
            }

            audioInputManager =
                null;
        }

        if (
            monitorOutputManager
        ) {
            try {
                await monitorOutputManager
                    .stop();
            }
            catch (error) {
                debugLog(
                    error
                );
            }

            monitorOutputManager =
                null;
        }

        setStatus(
            null,
            "Stopped"
        );
    }


    function stopLocalVad() {
        if (
            vadTimer !== null
        ) {
            clearInterval(
                vadTimer
            );

            vadTimer =
                null;
        }

        if (audioContext) {
            try {
                audioContext
                    .close();
            }
            catch (error) {
                debugLog(
                    error
                );
            }
        }

        audioContext =
            null;

        analyser =
            null;

        speechActive =
            false;

        speechFrames =
            0;

        silenceFrames =
            0;

        audioTurnHasContent =
            false;
    }




    let lastFullDuplexCommandId =
        null;


    function readFullDuplexDesired() {
        try {
            return JSON.parse(
                localStorage.getItem(
                    FULL_DUPLEX_DESIRED_KEY
                ) || "null"
            );
        }
        catch (_) {
            return null;
        }
    }


    async function applyFullDuplexCommand(
        command
    ) {
        if (
            !command
            || !command.id
            || command.id
                === lastFullDuplexCommandId
        ) {
            return;
        }

        lastFullDuplexCommandId =
            command.id;

        if (
            command.action
            === "start"
        ) {
            await start();
            return;
        }

        if (
            command.action
            === "stop"
        ) {
            await stop();
        }
    }


    function handleFullDuplexStorageEvent(
        event
    ) {
        if (
            event.key
            !== FULL_DUPLEX_COMMAND_KEY
        ) {
            return;
        }

        let command =
            null;

        try {
            command =
                JSON.parse(
                    event.newValue
                    || "null"
                );
        }
        catch (_) {
        }

        applyFullDuplexCommand(
            command
        ).catch(
            error => {
                console.error(
                    "[FullDuplex][Inbound] command failed",
                    error
                );

                publishFullDuplexStatus(
                    "error",
                    (
                        error.message
                        || "Inbound command failed"
                    )
                );
            }
        );
    }


    function applyFullDuplexDesiredState() {
        const desired =
            readFullDuplexDesired();

        if (
            !desired
            || !desired.active
        ) {
            return;
        }

        start()
            .catch(
                error => {
                    console.error(
                        "[FullDuplex][Inbound] auto-start failed",
                        error
                    );
                }
            );
    }


    // ------------------------------------------------------------
    // Events
    // ------------------------------------------------------------

    window.addEventListener(
        "storage",
        handleAudioOutputStorageChange
    );

    window.addEventListener(
        "storage",
        handleMonitorStorageChange
    );


    window.addEventListener(
        "storage",
        handleFullDuplexStorageEvent
    );


    startButton.addEventListener(
        "click",
        start
    );

    stopButton.addEventListener(
        "click",
        stop
    );

    window.addEventListener(
        "beforeunload",
        () => {
            stop();
        }
    );


    // ------------------------------------------------------------
    // Initial state
    // ------------------------------------------------------------

    resetTranscripts();
    updateButtons();

    setStatus(
        null,
        "Stopped"
    );

    window.setTimeout(
        applyFullDuplexDesiredState,
        0
    );

