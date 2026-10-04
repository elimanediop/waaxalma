
    const AUDIO_OUTPUT_STORAGE_KEY =
        "waaxalma.audioOutputDeviceId";

    const MONITOR_OUTPUT_STORAGE_KEY =
        "waaxalma.monitorOutputDeviceId";

    const MONITOR_ENABLED_STORAGE_KEY =
        "waaxalma.monitorEnabled";

    const AUDIO_URL =
        __STANDARD_AUDIO_URL_JSON__;


    let audioOutputManager =
        null;

    let monitorOutputManager =
        null;

    let audioElement =
        null;

    let monitorAudioElement =
        null;


    const playerElement =
        document.getElementById(
            "player"
        );

    const errorElement =
        document.getElementById(
            "error"
        );


    function showError(
        message
    ) {
        errorElement.textContent =
            message;

        errorElement.classList.add(
            "visible"
        );
    }


    function clearError() {
        errorElement.textContent =
            "";

        errorElement.classList.remove(
            "visible"
        );
    }


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


    async function applyStoredAudioOutput() {
        if (
            !audioOutputManager
        ) {
            return;
        }

        const storedDeviceId =
            primaryOutputDeviceId();

        try {
            await audioOutputManager
                .setOutputDevice(
                    storedDeviceId
                );

            clearError();
        }
        catch (error) {
            console.warn(
                (
                    "[Standard] Unable to apply "
                    + "selected audio output. "
                    + "Falling back to default."
                ),
                error
            );

            localStorage.removeItem(
                AUDIO_OUTPUT_STORAGE_KEY
            );

            try {
                await audioOutputManager
                    .resetToDefault();

                clearError();
            }
            catch (fallbackError) {
                showError(
                    (
                        "Unable to configure audio output: "
                        + fallbackError.message
                    )
                );
            }
        }
    }


    async function ensureMonitorOutputManager() {
        if (
            !monitorOutputManager
        ) {
            monitorOutputManager =
                new window
                    .WaaxalmaAudioOutputManager({
                        onFallback:
                            () => {
                                localStorage
                                    .removeItem(
                                        MONITOR_OUTPUT_STORAGE_KEY
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


    function releaseMonitorAudio() {
        if (
            !monitorAudioElement
        ) {
            return;
        }

        try {
            monitorAudioElement.pause();

            monitorAudioElement.src =
                "";

            if (
                monitorOutputManager
            ) {
                monitorOutputManager
                    .unregisterMediaElement(
                        monitorAudioElement
                    );
            }
        }
        catch (_) {
        }

        monitorAudioElement =
            null;
    }


    async function ensureMonitorAudio() {
        if (
            !localMonitoringEnabled()
            || monitorConflictsWithPrimary()
        ) {
            releaseMonitorAudio();
            return null;
        }

        const manager =
            await ensureMonitorOutputManager();

        if (
            !monitorAudioElement
        ) {
            monitorAudioElement =
                await manager
                    .createAudioElement({
                        autoplay:
                            false,

                        controls:
                            false,

                        muted:
                            false,
                    });

            monitorAudioElement.preload =
                "auto";

            await manager
                .attachUrl(
                    monitorAudioElement,
                    AUDIO_URL
                );
        }

        return monitorAudioElement;
    }


    async function syncMonitorPlayback() {
        const monitor =
            await ensureMonitorAudio();

        if (
            !monitor
            || !audioElement
        ) {
            return;
        }

        monitor.volume =
            audioElement.volume;

        monitor.muted =
            audioElement.muted;

        monitor.playbackRate =
            audioElement.playbackRate;

        if (
            Math.abs(
                monitor.currentTime
                - audioElement.currentTime
            )
            > 0.15
        ) {
            monitor.currentTime =
                audioElement.currentTime;
        }

        if (
            audioElement.paused
        ) {
            monitor.pause();
            return;
        }

        try {
            await monitor.play();
        }
        catch (error) {
            console.warn(
                (
                    "[Standard] Unable to start "
                    + "local monitor playback"
                ),
                error
            );
        }
    }


    async function initializePlayer() {
        if (
            !window.WaaxalmaAudioOutputManager
        ) {
            throw new Error(
                "WaaxalmaAudioOutputManager is not available."
            );
        }

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
                                    "[Standard] Selected audio "
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

        await applyStoredAudioOutput();

        audioElement =
            await audioOutputManager
                .createAudioElement({
                    autoplay:
                        false,

                    controls:
                        true,

                    muted:
                        false,
                });

        audioElement.preload =
            "metadata";

        await audioOutputManager
            .attachUrl(
                audioElement,
                AUDIO_URL
            );

        audioElement.addEventListener(
            "error",
            () => {
                showError(
                    "Unable to load interpreted audio."
                );
            }
        );

        audioElement.addEventListener(
            "play",
            () => {
                syncMonitorPlayback()
                    .catch(
                        error => {
                            console.warn(
                                "[Standard] Monitor sync failed",
                                error
                            );
                        }
                    );
            }
        );

        audioElement.addEventListener(
            "pause",
            () => {
                if (
                    monitorAudioElement
                ) {
                    monitorAudioElement
                        .pause();
                }
            }
        );

        audioElement.addEventListener(
            "seeking",
            () => {
                if (
                    monitorAudioElement
                ) {
                    monitorAudioElement
                        .currentTime =
                        audioElement.currentTime;
                }
            }
        );

        audioElement.addEventListener(
            "ratechange",
            () => {
                if (
                    monitorAudioElement
                ) {
                    monitorAudioElement
                        .playbackRate =
                        audioElement.playbackRate;
                }
            }
        );

        audioElement.addEventListener(
            "volumechange",
            () => {
                if (
                    monitorAudioElement
                ) {
                    monitorAudioElement.volume =
                        audioElement.volume;

                    monitorAudioElement.muted =
                        audioElement.muted;
                }
            }
        );

        audioElement.addEventListener(
            "ended",
            () => {
                if (
                    monitorAudioElement
                ) {
                    monitorAudioElement
                        .pause();
                }
            }
        );

        playerElement.appendChild(
            audioElement
        );
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
                    syncMonitorPlayback()
            )
            .catch(
                error => {
                    console.warn(
                        (
                            "[Standard] Unable to apply "
                            + "changed audio output"
                        ),
                        error
                    );
                }
            );
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

        syncMonitorPlayback()
            .catch(
                error => {
                    console.warn(
                        (
                            "[Standard] Unable to update "
                            + "local monitoring"
                        ),
                        error
                    );
                }
            );
    }


    window.addEventListener(
        "storage",
        handleAudioOutputStorageChange
    );

    window.addEventListener(
        "storage",
        handleMonitorStorageChange
    );


    window.addEventListener(
        "beforeunload",
        () => {
            releaseMonitorAudio();

            if (
                audioElement
            ) {
                try {
                    audioElement.pause();

                    audioElement.src =
                        "";

                    if (
                        audioOutputManager
                    ) {
                        audioOutputManager
                            .unregisterMediaElement(
                                audioElement
                            );
                    }
                }
                catch (_) {
                }
            }

            if (
                audioOutputManager
            ) {
                audioOutputManager
                    .stop()
                    .catch(
                        () => {
                        }
                    );
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
            }

            audioElement =
                null;

            audioOutputManager =
                null;

            monitorOutputManager =
                null;
        }
    );


    initializePlayer()
        .catch(
            error => {
                console.error(
                    "[Standard] Audio player failed",
                    error
                );

                showError(
                    (
                        "Unable to initialize interpreted audio: "
                        + error.message
                    )
                );
            }
        );
