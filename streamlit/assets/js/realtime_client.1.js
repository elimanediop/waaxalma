



    /* ==================================================== */

    /* Configuration                                        */

    /* ==================================================== */



    const WAAXALMA_CLIENT_ID = "__WAAXALMA_CLIENT_ID__";

    const WAAXALMA_API_URL =

        "__WAAXALMA_API_URL__";





    const OPENAI_REALTIME_URL =

        "https://api.openai.com/v1/realtime/translations/calls";





    const MAX_RECONNECT_ATTEMPTS =

        1;





    const SOURCE_VAD_RMS_THRESHOLD =

        0.035;





    const REMOTE_AUDIO_RMS_THRESHOLD =

        0.015;





    const VAD_REQUIRED_FRAMES =

        3;





    const CLIENT_METRICS = [

        "session_request_ms",

        "webrtc_connection_ms",

        "speech_to_first_translation_ms",

        "speech_to_first_audio_ms",

    ];


    const AUDIO_OUTPUT_STORAGE_KEY =
        "waaxalma.audioOutputDeviceId";

    const AUDIO_INPUT_STORAGE_KEY =
        "waaxalma.audioInputDeviceId";

    const MONITOR_OUTPUT_STORAGE_KEY =
        "waaxalma.monitorOutputDeviceId";

    const MONITOR_ENABLED_STORAGE_KEY =
        "waaxalma.monitorEnabled";


    const FULL_DUPLEX_COMMAND_KEY =
        "waaxalma.fullDuplex.command";

    const FULL_DUPLEX_DESIRED_KEY =
        "waaxalma.fullDuplex.desired";

    const FULL_DUPLEX_STATUS_KEY =
        "waaxalma.fullDuplex.outbound.direct.status";

    const FULL_DUPLEX_MODE =
        "direct";





    /* ==================================================== */

    /* Runtime state                                        */

    /* ==================================================== */



    let peerConnection =

        null;



    let sourceStream =

        null;



    let translatedAudio =

        null;


    let audioOutputManager =
        null;

    let audioInputManager =
        null;

    let monitorOutputManager =
        null;

    let monitorAudio =
        null;

let eventChannel =

        null;





    let sourceTranscriptReceived =

        false;



    let translationReceived =

        false;





    let reconnectAttempts =

        0;



    let stoppingManually =

        false;



    let connectionGeneration =

        0;





    /* ==================================================== */

    /* Audio monitoring state                               */

    /* ==================================================== */



    let audioContext =

        null;





    let sourceAnalyserNode =

        null;



    let sourceAnalyser =

        null;



    let sourceSilentGain =

        null;



    let sourceVadFrameId =

        null;



    let sourceVadActiveFrames =

        0;





    let remoteAnalyserNode =

        null;



    let remoteAnalyser =

        null;



    let remoteSilentGain =

        null;



    let remoteVadFrameId =

        null;



    let remoteVadActiveFrames =

        0;





    /* ==================================================== */

    /* Latency telemetry                                    */

    /* ==================================================== */



    let telemetry =

        null;





    function createTelemetry() {



        return {



            startAt:

                performance.now(),



            sessionRequestStartedAt:

                null,



            microphoneStartedAt:

                null,



            webrtcStartedAt:

                null,



            connectedAt:

                null,



            dataChannelOpenedAt:

                null,



            speechStartedAt:

                null,



            firstTranslationAt:

                null,



            remoteAudioTrackAt:

                null,



            firstAudibleTranslationAt:

                null,



            providerFirstTranslationElapsedMs:

                null,



            reportedToBackend:

                false,



            metrics: {},

        };

    }





    function roundMilliseconds(

        value

    ) {



        return (

            Math.round(

                value * 100

            )

            / 100

        );

    }





    function recordMetric(

        name,

        value,

        metadata = {}

    ) {



        if (

            !telemetry ||

            telemetry.metrics[name] !==

                undefined

        ) {

            return;

        }





        const normalizedValue =

            roundMilliseconds(

                value

            );





        telemetry.metrics[name] =

            normalizedValue;





        console.info(

            `[Waaxalma Metrics] ${name}:`,

            `${normalizedValue} ms`,

            metadata

        );

    }





    function logTelemetrySummary() {



        if (

            !telemetry

        ) {

            return;

        }





        console.group(

            "Waaxalma Realtime Latency"

        );





        console.table(

            telemetry.metrics

        );





        console.groupEnd();

    }





    async function reportTelemetryToBackend() {



        if (

            !telemetry ||

            telemetry.reportedToBackend

        ) {

            return;

        }





        const payload = {};





        for (

            const metricName

            of CLIENT_METRICS

        ) {



            const value =

                telemetry.metrics[

                    metricName

                ];





            if (

                typeof value ===

                    "number"

            ) {



                payload[

                    metricName

                ] = value;

            }

        }





        if (

            Object.keys(

                payload

            ).length === 0

        ) {

            return;

        }





        /*

         * Set before sending so Stop does not produce

         * a duplicate Prometheus observation.

         *

         * It is reset if the HTTP request fails.

         */

        telemetry.reportedToBackend =

            true;





        try {



            const response =

                await fetch(

                    `${WAAXALMA_API_URL}/api/realtime/metrics`,

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





            if (

                !response.ok

            ) {



                telemetry.reportedToBackend =

                    false;





                const responseBody =

                    await response.text();





                console.warn(

                    "Unable to report realtime metrics:",

                    response.status,

                    responseBody

                );





                return;

            }





            const result =

                await response.json();





            console.info(

                "Waaxalma realtime metrics reported",

                {

                    recorded:

                        result.recorded,



                    metrics:

                        payload,

                }

            );



        } catch (error) {



            telemetry.reportedToBackend =

                false;





            console.warn(

                "Unable to report realtime metrics:",

                error

            );

        }

    }





    /* ==================================================== */

    /* DOM                                                  */

    /* ==================================================== */



    const startButton =

        document.getElementById(

            "start"

        );





    const stopButton =

        document.getElementById(

            "stop"

        );





    const statusElement =

        document.getElementById(

            "status"

        );





    const statusText =

        document.getElementById(

            "status-text"

        );





    const languageSelect =

        document.getElementById(

            "language"

        );





    const sourceContainer =

        document.getElementById(

            "source-container"

        );





    const sourceUnavailable =

        document.getElementById(

            "source-unavailable"

        );





    const sourceTranscript =

        document.getElementById(

            "source-transcript"

        );





    const translatedTranscript =

        document.getElementById(

            "translated-transcript"

        );





    const liveBadge =

        document.getElementById(

            "live-badge"

        );
/* ==================================================== */



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


    /* UI helpers                                           */

    /* ==================================================== */



    function setStatus(

        message,

        state = "stopped"

    ) {



        statusText.textContent =

            message;


        publishFullDuplexStatus(
            state,
            message
        );





        statusElement.className =

            "status";





        if (

            state !==

            "stopped"

        ) {



            statusElement

                .classList

                .add(

                    state

                );

        }





        if (

            state ===

            "live"

        ) {



            liveBadge

                .classList

                .add(

                    "visible"

                );



        } else {



            liveBadge

                .classList

                .remove(

                    "visible"

                );

        }

    }





    function resetDisplay() {



        sourceTranscriptReceived =

            false;





        translationReceived =

            false;





        sourceTranscript.textContent =

            "";





        sourceContainer

            .classList

            .remove(

                "visible"

            );





        sourceUnavailable.style.display =

            "block";





        translatedTranscript.innerHTML =

            `

            <span class="translation-placeholder">

                Listening...

            </span>

            `;

    }





    
    /* ==================================================== */
    /* Universal audio output — v0.4.3 Slice 3             */
    /* ==================================================== */



async function ensureAudioOutputManager() {

        if (
            !window.WaaxalmaAudioOutputManager
        ) {
            throw new Error(
                "WaaxalmaAudioOutputManager is not available. "
                + "Check streamlit/audio_output_manager.js "
                + "and Streamlit client injection."
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
                                    "Selected audio output disappeared. "
                                    + "Falling back to default.",
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
            storedDeviceId ===
            audioOutputManager
                .selectedDeviceId
        ) {
            return;
        }


        try {

            await audioOutputManager
                .setOutputDevice(
                    storedDeviceId
                );
} catch (error) {

            console.warn(
                "Unable to apply selected audio output. "
                + "Falling back to default.",
                error
            );


            localStorage.removeItem(
                AUDIO_OUTPUT_STORAGE_KEY
            );


            await audioOutputManager
                .resetToDefault();
}
    }


    function handleAudioOutputStorageChange(
        event
    ) {

        if (
            event.key !==
            AUDIO_OUTPUT_STORAGE_KEY
        ) {
            return;
        }


        applyStoredAudioOutput()
            .then(
                () => {
                    const remoteStream =
                        (
                            translatedAudio
                            && translatedAudio.srcObject
                            instanceof MediaStream
                        )
                        ? translatedAudio.srcObject
                        : null;

                    return syncDirectLocalMonitor(
                        remoteStream
                    );
                }
            )
            .catch(
                error => {

                    console.warn(
                        "Unable to apply changed audio output:",
                        error
                    );
                }
            );
    }



    /* ==================================================== */
    /* Independent local monitoring — v0.4.4 Slice 2       */
    /* ==================================================== */

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
                                        "Selected local monitor "
                                        + "output disappeared. "
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


    function releaseDirectMonitorAudio() {
        if (!monitorAudio) {
            return;
        }

        try {
            if (
                monitorOutputManager
            ) {
                monitorOutputManager
                    .unregisterMediaElement(
                        monitorAudio
                    );
            }

            monitorAudio.pause();

            monitorAudio.srcObject =
                null;
        }
        catch (error) {
            console.debug(
                "Unable to release local monitor audio",
                error
            );
        }

        monitorAudio =
            null;
    }


    async function syncDirectLocalMonitor(
        remoteStream
    ) {
        if (
            !localMonitoringEnabled()
            || !remoteStream
        ) {
            releaseDirectMonitorAudio();
            return;
        }

        if (
            monitorConflictsWithPrimary()
        ) {
            releaseDirectMonitorAudio();

            console.warn(
                (
                    "Local monitor and primary output "
                    + "are the same stored device. "
                    + "Monitoring is suppressed to avoid "
                    + "duplicate playback."
                )
            );

            return;
        }

        const manager =
            await ensureMonitorOutputManager();

        if (
            !monitorAudio
        ) {
            monitorAudio =
                await manager
                    .createAudioElement({
                        autoplay:
                            true,

                        controls:
                            false,

                        muted:
                            false,
                    });
        }

        await manager
            .attachMediaStream(
                monitorAudio,
                remoteStream
            );

        try {
            await monitorAudio.play();
        }
        catch (error) {
            console.warn(
                "Unable to start local monitor playback:",
                error
            );
        }
    }


    function handleMonitorStorageChange(
        event
    ) {
        if (
            event.key
                !== MONITOR_OUTPUT_STORAGE_KEY
            && event.key
                !== MONITOR_ENABLED_STORAGE_KEY
        ) {
            return;
        }

        const remoteStream =
            (
                translatedAudio
                && translatedAudio.srcObject
                instanceof MediaStream
            )
            ? translatedAudio.srcObject
            : null;

        syncDirectLocalMonitor(
            remoteStream
        ).catch(
            error => {
                console.warn(
                    "Unable to update local monitor:",
                    error
                );
            }
        );
    }


/* ==================================================== */

    /* AudioContext                                         */

    /* ==================================================== */



    async function ensureAudioContext() {



        if (

            !audioContext ||

            audioContext.state ===

                "closed"

        ) {



            audioContext =

                new AudioContext();

        }





        if (

            audioContext.state ===

                "suspended"

        ) {



            await audioContext.resume();

        }

    }





    function calculateRms(

        analyser

    ) {



        const data =

            new Uint8Array(

                analyser.fftSize

            );





        analyser.getByteTimeDomainData(

            data

        );





        let sum =

            0;





        for (

            let index = 0;

            index < data.length;

            index += 1

        ) {



            const sample =

                (

                    data[index]

                    -

                    128

                )

                /

                128;





            sum +=

                sample * sample;

        }





        return Math.sqrt(

            sum /

            data.length

        );

    }





    /* ==================================================== */

    /* Source speech VAD                                    */

    /* ==================================================== */



    function stopSourceSpeechMonitor() {



        if (

            sourceVadFrameId !==

                null

        ) {



            cancelAnimationFrame(

                sourceVadFrameId

            );





            sourceVadFrameId =

                null;

        }





        try {



            sourceAnalyserNode

                ?.disconnect();



        } catch (_) {

        }





        try {



            sourceAnalyser

                ?.disconnect();



        } catch (_) {

        }





        try {



            sourceSilentGain

                ?.disconnect();



        } catch (_) {

        }





        sourceAnalyserNode =

            null;





        sourceAnalyser =

            null;





        sourceSilentGain =

            null;





        sourceVadActiveFrames =

            0;

    }





    async function startSourceSpeechMonitor() {



        if (

            !sourceStream ||

            !telemetry ||

            telemetry.speechStartedAt !==

                null

        ) {

            return;

        }





        await ensureAudioContext();





        stopSourceSpeechMonitor();





        sourceAnalyserNode =

            audioContext

                .createMediaStreamSource(

                    sourceStream

                );





        sourceAnalyser =

            audioContext

                .createAnalyser();





        sourceAnalyser.fftSize =

            512;





        sourceSilentGain =

            audioContext

                .createGain();





        sourceSilentGain.gain.value =

            0;





        sourceAnalyserNode.connect(

            sourceAnalyser

        );





        sourceAnalyser.connect(

            sourceSilentGain

        );





        sourceSilentGain.connect(

            audioContext.destination

        );





        const detectSpeech =

            () => {



                if (

                    !telemetry ||

                    telemetry.speechStartedAt !==

                        null

                ) {



                    stopSourceSpeechMonitor();



                    return;

                }





                if (

                    telemetry.connectedAt !==

                        null

                ) {



                    const rms =

                        calculateRms(

                            sourceAnalyser

                        );





                    if (

                        rms >=

                        SOURCE_VAD_RMS_THRESHOLD

                    ) {



                        sourceVadActiveFrames +=

                            1;



                    } else {



                        sourceVadActiveFrames =

                            0;

                    }





                    if (

                        sourceVadActiveFrames >=

                        VAD_REQUIRED_FRAMES

                    ) {



                        telemetry.speechStartedAt =

                            performance.now();





                        recordMetric(

                            "speech_start_after_connection_ms",

                            (

                                telemetry.speechStartedAt

                                -

                                telemetry.connectedAt

                            ),

                            {

                                rms:

                                    roundMilliseconds(

                                        rms

                                    ),

                            }

                        );





                        console.info(

                            "Source speech detected",

                            {

                                rms,

                                threshold:

                                    SOURCE_VAD_RMS_THRESHOLD,

                            }

                        );





                        stopSourceSpeechMonitor();





                        return;

                    }

                }





                sourceVadFrameId =

                    requestAnimationFrame(

                        detectSpeech

                    );

            };





        sourceVadFrameId =

            requestAnimationFrame(

                detectSpeech

            );

    }





    /* ==================================================== */

    /* Remote translated audio monitor                      */

    /* ==================================================== */



    function stopRemoteAudioMonitor() {



        if (

            remoteVadFrameId !==

                null

        ) {



            cancelAnimationFrame(

                remoteVadFrameId

            );





            remoteVadFrameId =

                null;

        }





        try {



            remoteAnalyserNode

                ?.disconnect();



        } catch (_) {

        }





        try {



            remoteAnalyser

                ?.disconnect();



        } catch (_) {

        }





        try {



            remoteSilentGain

                ?.disconnect();



        } catch (_) {

        }





        remoteAnalyserNode =

            null;





        remoteAnalyser =

            null;





        remoteSilentGain =

            null;





        remoteVadActiveFrames =

            0;

    }





    async function startRemoteAudioMonitor(

        stream

    ) {



        if (

            !telemetry

        ) {

            return;

        }





        await ensureAudioContext();





        stopRemoteAudioMonitor();





        remoteAnalyserNode =

            audioContext

                .createMediaStreamSource(

                    stream

                );





        remoteAnalyser =

            audioContext

                .createAnalyser();





        remoteAnalyser.fftSize =

            512;





        remoteSilentGain =

            audioContext

                .createGain();





        /*

         * Analysis path remains silent.

         * The Audio element handles actual playback.

         */

        remoteSilentGain.gain.value =

            0;





        remoteAnalyserNode.connect(

            remoteAnalyser

        );





        remoteAnalyser.connect(

            remoteSilentGain

        );





        remoteSilentGain.connect(

            audioContext.destination

        );





        const detectTranslatedAudio =

            () => {



                if (

                    !telemetry ||

                    telemetry

                        .firstAudibleTranslationAt !==

                        null

                ) {



                    stopRemoteAudioMonitor();



                    return;

                }





                if (

                    telemetry.speechStartedAt !==

                        null

                ) {



                    const rms =

                        calculateRms(

                            remoteAnalyser

                        );





                    if (

                        rms >=

                        REMOTE_AUDIO_RMS_THRESHOLD

                    ) {



                        remoteVadActiveFrames +=

                            1;



                    } else {



                        remoteVadActiveFrames =

                            0;

                    }





                    if (

                        remoteVadActiveFrames >=

                        VAD_REQUIRED_FRAMES

                    ) {



                        telemetry

                            .firstAudibleTranslationAt =

                            performance.now();
recordMetric(

                            "speech_to_first_audio_ms",

                            (

                                telemetry

                                    .firstAudibleTranslationAt

                                -

                                telemetry

                                    .speechStartedAt

                            ),

                            {

                                rms:

                                    roundMilliseconds(

                                        rms

                                    ),

                            }

                        );





                        if (

                            telemetry

                                .firstTranslationAt !==

                                null

                        ) {



                            recordMetric(

                                "translation_to_first_audio_ms",

                                (

                                    telemetry

                                        .firstAudibleTranslationAt

                                    -

                                    telemetry

                                        .firstTranslationAt

                                )

                            );

                        }





                        console.info(

                            "First translated audio detected",

                            {

                                rms,

                                threshold:

                                    REMOTE_AUDIO_RMS_THRESHOLD,

                            }

                        );





                        logTelemetrySummary();





                        reportTelemetryToBackend()

                            .catch(

                                error => {



                                    console.warn(

                                        "Telemetry reporting failed:",

                                        error

                                    );

                                }

                            );





                        stopRemoteAudioMonitor();





                        return;

                    }

                }





                remoteVadFrameId =

                    requestAnimationFrame(

                        detectTranslatedAudio

                    );

            };





        remoteVadFrameId =

            requestAnimationFrame(

                detectTranslatedAudio

            );

    }





    /* ==================================================== */

    /* Waaxalma backend                                     */

    /* ==================================================== */



    async function createWaaxalmaSession(

        targetLanguage

    ) {



        console.debug(

            "Creating Waaxalma realtime session",

            {

                targetLanguage,

            }

        );





        if (

            telemetry

        ) {



            telemetry.sessionRequestStartedAt =

                performance.now();

        }





        const response =

            await fetch(

                `${WAAXALMA_API_URL}/api/realtime/translation/session`,

                {

                    method:

                        "POST",



                    headers: {
                        "X-Client-Id": WAAXALMA_CLIENT_ID,

                        "Content-Type":

                            "application/json",

                    },



                    body:

                        JSON.stringify({

                            target_language:

                                targetLanguage,

                        }),

                }

            );





        if (

            !response.ok

        ) {



            const body =

                await response.text();





            throw new Error(

                "Unable to create realtime session: "

                + body

            );

        }





        const session =

            await response.json();





        if (

            telemetry &&

            telemetry.sessionRequestStartedAt !==

                null

        ) {



            recordMetric(

                "session_request_ms",

                (

                    performance.now()

                    -

                    telemetry

                        .sessionRequestStartedAt

                ),

                {

                    provider:

                        session.provider,



                    model:

                        session.model,

                }

            );

        }





        console.debug(

            "Waaxalma realtime session created",

            {

                provider:

                    session.provider,



                model:

                    session.model,



                target_language:

                    session.target_language,



                expires_at:

                    session.expires_at,

            }

        );





        return session;

    }





    /* ==================================================== */

    /* Realtime events                                      */

    /* ==================================================== */



    function handleRealtimeEvent(

        event

    ) {



        console.debug(

            "Realtime event:",

            event.type,

            event

        );





        /* ------------------------------------------------ */

        /* Source transcript                                */

        /* ------------------------------------------------ */



        if (

            event.type ===

            "session.input_transcript.delta"

        ) {



            if (

                !sourceTranscriptReceived

            ) {



                sourceTranscriptReceived =

                    true;





                sourceContainer

                    .classList

                    .add(

                        "visible"

                    );





                sourceUnavailable.style.display =

                    "none";





                sourceTranscript.textContent =

                    "";

            }





            sourceTranscript.textContent +=

                event.delta ?? "";





            return;

        }





        /* ------------------------------------------------ */

        /* Translation                                      */

        /* ------------------------------------------------ */



        if (

            event.type ===

            "session.output_transcript.delta"

        ) {



            if (

                telemetry &&

                telemetry.firstTranslationAt ===

                    null

            ) {



                telemetry.firstTranslationAt =

                    performance.now();





                recordMetric(

                    "start_to_first_translation_ms",

                    (

                        telemetry.firstTranslationAt

                        -

                        telemetry.startAt

                    )

                );





                if (

                    telemetry.connectedAt !==

                        null

                ) {



                    recordMetric(

                        "connection_to_first_translation_ms",

                        (

                            telemetry.firstTranslationAt

                            -

                            telemetry.connectedAt

                        )

                    );

                }





                if (

                    telemetry.speechStartedAt !==

                        null

                ) {



                    recordMetric(

                        "speech_to_first_translation_ms",

                        (

                            telemetry.firstTranslationAt

                            -

                            telemetry.speechStartedAt

                        )

                    );

                }





                if (

                    typeof event.elapsed_ms ===

                        "number"

                ) {



                    telemetry

                        .providerFirstTranslationElapsedMs =

                        event.elapsed_ms;





                    recordMetric(

                        "provider_first_translation_elapsed_ms",

                        event.elapsed_ms

                    );

                }





                console.info(

                    "First realtime translation received",

                    {

                        delta:

                            event.delta,



                        elapsed_ms:

                            event.elapsed_ms,

                    }

                );





                logTelemetrySummary();

            }





            if (

                !translationReceived

            ) {



                translationReceived =

                    true;





                translatedTranscript.textContent =

                    "";

            }





            translatedTranscript.textContent +=

                event.delta ?? "";





            return;

        }





        /* ------------------------------------------------ */

        /* Session lifecycle                                */

        /* ------------------------------------------------ */



        if (

            event.type ===

            "session.created"

        ) {



            console.debug(

                "OpenAI realtime session created",

                event.session

            );





            return;

        }





        if (

            event.type ===

            "session.closed"

        ) {



            console.debug(

                "OpenAI realtime session closed"

            );





            if (

                stoppingManually

            ) {



                setStatus(

                    "Stopped",

                    "stopped"

                );

            }





            return;

        }





        /* ------------------------------------------------ */

        /* Provider error                                   */

        /* ------------------------------------------------ */



        if (

            event.type ===

            "error"

        ) {



            console.error(

                "OpenAI realtime error:",

                event

            );





            setStatus(

                "Realtime error",

                "error"

            );





            return;

        }

    }






    /* ==================================================== */
    /* Explicit realtime audio input — v0.4.4 Slice 1      */
    /* ==================================================== */

    async function ensureAudioInputManager() {
        if (
            !window.WaaxalmaAudioInputManager
        ) {
            throw new Error(
                "WaaxalmaAudioInputManager is not available. "
                + "Check streamlit/audio_input_manager.js "
                + "and Streamlit client injection."
            );
        }

        if (
            !audioInputManager
        ) {
            audioInputManager =
                new window
                    .WaaxalmaAudioInputManager({
                        onFallback:
                            ({
                                previousDeviceId,
                            }) => {
                                localStorage
                                    .removeItem(
                                        AUDIO_INPUT_STORAGE_KEY
                                    );

                                console.warn(
                                    "Selected microphone disappeared. "
                                    + "Falling back to default.",
                                    {
                                        previousDeviceId,
                                    }
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
            storedDeviceId ===
            audioInputManager
                .selectedDeviceId
        ) {
            return;
        }

        await audioInputManager
            .setInputDevice(
                storedDeviceId
            );
    }


    /* ==================================================== */

    /* Microphone                                           */

    /* ==================================================== */



    async function ensureMicrophone() {



        if (

            sourceStream

        ) {



            const activeTrack =

                sourceStream

                    .getAudioTracks()

                    .find(

                        track =>

                            track.readyState ===

                            "live"

                    );





            if (

                activeTrack

            ) {



                console.debug(

                    "Reusing existing microphone stream"

                );





                await startSourceSpeechMonitor();





                return;

            }

        }





        setStatus(

            "Microphone...",

            "connecting"

        );





        if (

            telemetry

        ) {



            telemetry.microphoneStartedAt =

                performance.now();

        }





        const inputManager =
            await ensureAudioInputManager();


        sourceStream =
            await inputManager
                .acquireStream();





        if (

            telemetry &&

            telemetry.microphoneStartedAt !==

                null

        ) {



            recordMetric(

                "microphone_acquisition_ms",

                (

                    performance.now()

                    -

                    telemetry

                        .microphoneStartedAt

                )

            );

        }





        console.debug(

            "Microphone access granted"

        );





        await startSourceSpeechMonitor();

    }





    /* ==================================================== */

    /* Cleanup                                              */

    /* ==================================================== */



    function cleanupConnection({

        stopMicrophone = true,

    } = {}) {



        console.debug(

            "Cleaning realtime connection",

            {

                stopMicrophone,

            }

        );





        connectionGeneration +=

            1;





        stopRemoteAudioMonitor();
if (

            stopMicrophone

        ) {



            stopSourceSpeechMonitor();

        }





        if (

            eventChannel

        ) {



            try {



                eventChannel.onopen =

                    null;



                eventChannel.onmessage =

                    null;



                eventChannel.onerror =

                    null;



                eventChannel.onclose =

                    null;





                eventChannel.close();



            } catch (error) {



                console.debug(

                    "Unable to close data channel",

                    error

                );

            }

        }





        if (

            peerConnection

        ) {



            try {



                peerConnection

                    .onconnectionstatechange =

                    null;





                peerConnection.ontrack =

                    null;





                peerConnection.close();



            } catch (error) {



                console.debug(

                    "Unable to close peer connection",

                    error

                );

            }

        }





        releaseDirectMonitorAudio();


        if (
            translatedAudio
        ) {

            try {

                if (
                    audioOutputManager
                ) {
                    audioOutputManager
                        .unregisterMediaElement(
                            translatedAudio
                        );
                }

                translatedAudio.pause();

                translatedAudio.srcObject =
                    null;

            } catch (error) {

                console.debug(
                    "Unable to release translated audio",
                    error
                );
            }
        }





        if (

            stopMicrophone &&

            sourceStream

        ) {



            sourceStream

                .getTracks()

                .forEach(

                    track => {



                        try {



                            track.stop();



                        } catch (_) {

                        }

                    }

                );





            sourceStream =

                null;

        }





        peerConnection =

            null;





        eventChannel =

            null;





        translatedAudio =

            null;





        if (

            stopMicrophone &&

            audioContext

        ) {



            const contextToClose =

                audioContext;





            audioContext =

                null;





            contextToClose

                .close()

                .catch(

                    () => {

                    }

                );

        }

    }





    /* ==================================================== */

    /* WebRTC connection                                    */

    /* ==================================================== */



    async function connectRealtime({

        resetTranscript = false,

    } = {}) {



        const targetLanguage =

            languageSelect.value;





        if (

            resetTranscript

        ) {



            resetDisplay();

        }





        setStatus(

            "Creating session...",

            "connecting"

        );





        /*

         * A reconnect always creates a new ephemeral

         * session and therefore a new client secret.

         */

        const session =

            await createWaaxalmaSession(

                targetLanguage

            );





        await ensureMicrophone();





        if (

            telemetry

        ) {



            telemetry.webrtcStartedAt =

                performance.now();

        }





        peerConnection =

            new RTCPeerConnection();





        const currentGeneration =

            ++connectionGeneration;





        /* ------------------------------------------------ */

        /* Connection state                                 */

        /* ------------------------------------------------ */



        peerConnection

            .onconnectionstatechange =

            async () => {



                if (

                    currentGeneration !==

                    connectionGeneration

                ) {

                    return;

                }





                if (

                    !peerConnection

                ) {

                    return;

                }





                const state =

                    peerConnection

                        .connectionState;





                console.debug(

                    "WebRTC state:",

                    state

                );





                if (

                    state ===

                    "connected"

                ) {



                    reconnectAttempts =

                        0;





                    if (

                        telemetry

                    ) {



                        telemetry.connectedAt =

                            performance.now();





                        if (

                            telemetry.webrtcStartedAt !==

                                null

                        ) {



                            recordMetric(

                                "webrtc_connection_ms",

                                (

                                    telemetry.connectedAt

                                    -

                                    telemetry.webrtcStartedAt

                                )

                            );

                        }

                    }





                    setStatus(

                        "Live",

                        "live"

                    );





                    return;

                }





                if (

                    state ===

                        "failed" &&

                    !stoppingManually

                ) {



                    await attemptReconnect();





                    return;

                }





                if (

                    state ===

                        "disconnected" &&

                    !stoppingManually

                ) {



                    setStatus(

                        "Connection interrupted",

                        "connecting"

                    );

                }

            };





        /* ------------------------------------------------ */

        /* Microphone track                                 */

        /* ------------------------------------------------ */



        const audioTrack =

            sourceStream

                .getAudioTracks()[0];





        if (

            !audioTrack

        ) {



            throw new Error(

                "No active microphone track is available."

            );

        }





        peerConnection.addTrack(

            audioTrack,

            sourceStream

        );





        /* ------------------------------------------------ */

        /* Translated audio                                 */

        /* ------------------------------------------------ */



        const outputManager =
            await ensureAudioOutputManager();


        translatedAudio =
            await outputManager
                .createAudioElement({
                    autoplay:
                        true,

                    controls:
                        false,

                    muted:
                        false,
                });
peerConnection.ontrack =

            event => {



                if (

                    currentGeneration !==

                    connectionGeneration

                ) {

                    return;

                }





                if (

                    telemetry &&

                    telemetry.remoteAudioTrackAt ===

                        null

                ) {



                    telemetry.remoteAudioTrackAt =

                        performance.now();





                    if (

                        telemetry.webrtcStartedAt !==

                            null

                    ) {



                        recordMetric(

                            "remote_audio_track_available_ms",

                            (

                                telemetry.remoteAudioTrackAt

                                -

                                telemetry.webrtcStartedAt

                            )

                        );

                    }

                }





                if (

                    event.streams &&

                    event.streams.length >

                        0

                ) {



                    const remoteStream =

                        event.streams[0];
translatedAudio.srcObject =

                        remoteStream;


                    syncDirectLocalMonitor(
                        remoteStream
                    ).catch(
                        error => {

                            console.warn(
                                "Unable to start local monitoring:",
                                error
                            );
                        }
                    );


startRemoteAudioMonitor(

                        remoteStream

                    ).catch(

                        error => {



                            console.warn(

                                "Unable to monitor translated audio:",

                                error

                            );

                        }

                    );





                    translatedAudio
                        .play()
                        .then(
                            () => {
}
                        )
                        .catch(
                            error => {

                                directPlaybackState =
                                    (
                                        "blocked-"
                                        + (
                                            error.name
                                            || "error"
                                        )
                                    );
console.warn(
                                    "Autoplay blocked:",
                                    error
                                );
                            }
                        );

                }

            };





        /* ------------------------------------------------ */

        /* Data channel                                     */

        /* ------------------------------------------------ */



        eventChannel =

            peerConnection

                .createDataChannel(

                    "oai-events"

                );





        eventChannel.onopen =

            () => {



                if (

                    currentGeneration !==

                    connectionGeneration

                ) {

                    return;

                }





                console.debug(

                    "Realtime data channel opened"

                );





                if (

                    telemetry

                ) {



                    telemetry.dataChannelOpenedAt =

                        performance.now();





                    if (

                        telemetry.webrtcStartedAt !==

                            null

                    ) {



                        recordMetric(

                            "data_channel_open_ms",

                            (

                                telemetry

                                    .dataChannelOpenedAt

                                -

                                telemetry

                                    .webrtcStartedAt

                            )

                        );

                    }

                }





                stopButton.disabled =

                    false;





                setStatus(

                    "Live",

                    "live"

                );

            };





        eventChannel.onmessage =

            message => {



                if (

                    currentGeneration !==

                    connectionGeneration

                ) {

                    return;

                }





                try {



                    const event =

                        JSON.parse(

                            message.data

                        );





                    handleRealtimeEvent(

                        event

                    );



                } catch (error) {



                    console.error(

                        "Invalid realtime event:",

                        error,

                        message.data

                    );

                }

            };





        eventChannel.onerror =

            event => {



                if (

                    currentGeneration !==

                    connectionGeneration

                ) {

                    return;

                }





                console.error(

                    "Realtime data channel error:",

                    event

                );





                if (

                    !stoppingManually

                ) {



                    setStatus(

                        "Channel error",

                        "error"

                    );

                }

            };





        eventChannel.onclose =

            () => {



                if (

                    currentGeneration !==

                    connectionGeneration

                ) {

                    return;

                }





                console.debug(

                    "Realtime data channel closed"

                );

            };





        /* ------------------------------------------------ */

        /* SDP                                              */

        /* ------------------------------------------------ */



        const offer =

            await peerConnection

                .createOffer();





        await peerConnection

            .setLocalDescription(

                offer

            );





        setStatus(

            "Connecting...",

            "connecting"

        );





        const response =

            await fetch(

                OPENAI_REALTIME_URL,

                {

                    method:

                        "POST",



                    headers: {

                        "Authorization":

                            `Bearer ${session.client_secret}`,



                        "Content-Type":

                            "application/sdp",

                    },



                    body:

                        peerConnection

                            .localDescription

                            .sdp,

                }

            );





        if (

            !response.ok

        ) {



            const body =

                await response.text();





            throw new Error(

                "WebRTC connection failed: "

                + body

            );

        }





        const answerSdp =

            await response.text();





        await peerConnection

            .setRemoteDescription({

                type:

                    "answer",



                sdp:

                    answerSdp,

            });





        stopButton.disabled =

            false;

    }





    /* ==================================================== */

    /* Start                                                */

    /* ==================================================== */



    async function startTranslation() {



        stoppingManually =

            false;





        reconnectAttempts =

            0;





        telemetry =

            createTelemetry();





        console.info(

            "Waaxalma realtime telemetry started"

        );





        startButton.disabled =

            true;





        stopButton.disabled =

            true;





        try {



            await connectRealtime({

                resetTranscript:

                    true,

            });



        } catch (error) {



            console.error(

                "Unable to start realtime translation:",

                error

            );





            logTelemetrySummary();





            await reportTelemetryToBackend();





            cleanupConnection({

                stopMicrophone:

                    true,

            });





            startButton.disabled =

                false;





            stopButton.disabled =

                true;





            setStatus(

                "Error",

                "error"

            );





            throw error;

        }

    }





    /* ==================================================== */

    /* Reconnect                                            */

    /* ==================================================== */



    async function attemptReconnect() {



        if (

            stoppingManually

        ) {

            return;

        }





        if (

            reconnectAttempts >=

            MAX_RECONNECT_ATTEMPTS

        ) {



            console.error(

                "Maximum realtime reconnect attempts reached"

            );





            logTelemetrySummary();





            await reportTelemetryToBackend();





            cleanupConnection({

                stopMicrophone:

                    true,

            });





            startButton.disabled =

                false;





            stopButton.disabled =

                true;





            setStatus(

                "Connection lost",

                "error"

            );





            return;

        }





        reconnectAttempts +=

            1;





        console.warn(

            "Attempting realtime reconnect",

            {

                attempt:

                    reconnectAttempts,



                maxAttempts:

                    MAX_RECONNECT_ATTEMPTS,

            }

        );





        setStatus(

            "Reconnecting...",

            "connecting"

        );





        cleanupConnection({

            stopMicrophone:

                false,

        });





        try {



            await connectRealtime({

                resetTranscript:

                    false,

            });



        } catch (error) {



            console.error(

                "Realtime reconnect failed:",

                error

            );





            logTelemetrySummary();





            await reportTelemetryToBackend();





            cleanupConnection({

                stopMicrophone:

                    true,

            });





            startButton.disabled =

                false;





            stopButton.disabled =

                true;





            setStatus(

                "Reconnect failed",

                "error"

            );

        }

    }





    /* ==================================================== */

    /* Stop                                                 */

    /* ==================================================== */



    async function stopTranslation() {



        console.debug(

            "Stopping realtime translation"

        );





        stoppingManually =

            true;





        logTelemetrySummary();





        /*

         * Send any metrics that were not already

         * reported when translated audio arrived.

         */

        await reportTelemetryToBackend();





        if (

            eventChannel &&

            eventChannel.readyState ===

                "open"

        ) {



            try {



                eventChannel.send(

                    JSON.stringify({

                        type:

                            "session.close",

                    })

                );



            } catch (error) {



                console.debug(

                    "Unable to send session.close",

                    error

                );

            }

        }





        cleanupConnection({

            stopMicrophone:

                true,

        });





        reconnectAttempts =

            0;





        startButton.disabled =

            false;





        stopButton.disabled =

            true;





        setStatus(

            "Stopped",

            "stopped"

        );

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
            command.outboundMode
            !== FULL_DUPLEX_MODE
        ) {
            return;
        }

        if (
            command.action
            === "start"
        ) {
            if (
                !startButton.disabled
            ) {
                await startTranslation();
            }

            return;
        }

        if (
            command.action
            === "stop"
        ) {
            await stopTranslation();
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
                    "[FullDuplex][Direct] command failed",
                    error
                );

                publishFullDuplexStatus(
                    "error",
                    (
                        error.message
                        || "Direct command failed"
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
            || desired.outboundMode
                !== FULL_DUPLEX_MODE
        ) {
            return;
        }

        if (
            !startButton.disabled
        ) {
            startTranslation()
                .catch(
                    error => {
                        console.error(
                            "[FullDuplex][Direct] auto-start failed",
                            error
                        );
                    }
                );
        }
    }


    /* ==================================================== */

    /* Event listeners                                      */

    /* ==================================================== */



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

        async () => {



            try {



                await startTranslation();



            } catch (error) {



                alert(

                    error.message

                );

            }

        }

    );





    stopButton.addEventListener(

        "click",

        () => {



            stopTranslation()

                .catch(

                    error => {



                        console.warn(

                            "Unable to stop realtime translation cleanly:",

                            error

                        );

                    }

                );

        }

    );





    window.addEventListener(
        "beforeunload",
        () => {

            stoppingManually =
                true;


            cleanupConnection({
                stopMicrophone:
                    true,
            });


            if (
                audioOutputManager
            ) {
                audioOutputManager
                    .stop()
                    .catch(
                        () => {
                        }
                    );

                audioOutputManager =
                    null;
            }


            if (
                audioInputManager
            ) {
                audioInputManager
                    .stop()
                    .catch(
                        () => {
                        }
                    );

                audioInputManager =
                    null;
            }


            if (
                monitorOutputManager
            ) {
                monitorOutputManager
                    .stop()
                    .catch(
                        () => {
                        }
                    );

                monitorOutputManager =
                    null;
            }

            releaseDirectMonitorAudio();
        }
    );



    publishFullDuplexStatus(
        "stopped",
        "Stopped"
    );

    window.setTimeout(
        applyFullDuplexDesiredState,
        0
    );

