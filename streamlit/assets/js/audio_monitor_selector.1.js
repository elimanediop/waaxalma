
    const MONITOR_DEVICE_STORAGE_KEY =
        "waaxalma.monitorOutputDeviceId";

    const MONITOR_ENABLED_STORAGE_KEY =
        "waaxalma.monitorEnabled";

    const PRIMARY_OUTPUT_STORAGE_KEY =
        "waaxalma.audioOutputDeviceId";


    const enabledElement =
        document.getElementById(
            "monitorEnabled"
        );

    const monitorDeviceElement =
        document.getElementById(
            "monitorDevice"
        );

    const refreshButton =
        document.getElementById(
            "refreshButton"
        );

    const statusElement =
        document.getElementById(
            "status"
        );

    const capabilitiesElement =
        document.getElementById(
            "capabilities"
        );


    function setStatus(
        message,
        isWarning = false
    ) {
        statusElement.textContent =
            message;

        statusElement.classList.toggle(
            "warning",
            isWarning
        );
    }


    function monitoringEnabled() {
        return (
            localStorage.getItem(
                MONITOR_ENABLED_STORAGE_KEY
            )
            === "true"
        );
    }


    function persistEnabled(
        enabled
    ) {
        localStorage.setItem(
            MONITOR_ENABLED_STORAGE_KEY,
            enabled
                ? "true"
                : "false"
        );
    }


    function renderCapabilities(
        capabilities
    ) {
        capabilitiesElement.textContent =
            (
                "enumerateDevices: "
                + (
                    capabilities.enumerateDevices
                    ? "yes"
                    : "no"
                )
                + " · setSinkId: "
                + (
                    capabilities.setSinkId
                    ? "yes"
                    : "no"
                )
            );
    }


    function normalizeDeviceLabel(
        device,
        index
    ) {
        if (
            device.deviceId
            === "default"
        ) {
            return (
                device.label
                || "Default audio output"
            );
        }

        return (
            device.label
            || (
                "Audio output "
                + String(index + 1)
            )
        );
    }


    function renderDevices(
        devices
    ) {
        const previousValue =
            monitorDeviceElement.value;

        monitorDeviceElement.innerHTML =
            "";

        const defaultOption =
            document.createElement(
                "option"
            );

        defaultOption.value =
            "";

        defaultOption.textContent =
            "Default audio output";

        monitorDeviceElement
            .appendChild(
                defaultOption
            );

        devices.forEach(
            (
                device,
                index
            ) => {
                if (
                    !device.deviceId
                    || device.deviceId
                    === "default"
                ) {
                    return;
                }

                const option =
                    document.createElement(
                        "option"
                    );

                option.value =
                    device.deviceId;

                option.textContent =
                    normalizeDeviceLabel(
                        device,
                        index
                    );

                monitorDeviceElement
                    .appendChild(
                        option
                    );
            }
        );

        const savedDeviceId =
            localStorage.getItem(
                MONITOR_DEVICE_STORAGE_KEY
            ) || "";

        const preferredValue =
            savedDeviceId
            || previousValue
            || "";

        const exists =
            preferredValue === ""
            || devices.some(
                device =>
                    device.deviceId
                    === preferredValue
            );

        monitorDeviceElement.value =
            exists
            ? preferredValue
            : "";

        if (!exists) {
            localStorage.removeItem(
                MONITOR_DEVICE_STORAGE_KEY
            );
        }
    }


    function renderState() {
        const enabled =
            monitoringEnabled();

        enabledElement.checked =
            enabled;

        monitorDeviceElement.disabled =
            !enabled;

        const monitorDeviceId =
            localStorage.getItem(
                MONITOR_DEVICE_STORAGE_KEY
            ) || "";

        const primaryDeviceId =
            localStorage.getItem(
                PRIMARY_OUTPUT_STORAGE_KEY
            ) || "";

        if (!enabled) {
            setStatus(
                (
                    "Local monitoring is disabled. "
                    + "Enable it to hear translated audio "
                    + "through a separate local device."
                )
            );

            return;
        }

        if (
            monitorDeviceId
            === primaryDeviceId
        ) {
            setStatus(
                (
                    "Monitor and primary output currently resolve "
                    + "to the same stored device. Select a headset "
                    + "for monitoring to avoid duplicate playback "
                    + "or feedback."
                ),
                true
            );

            return;
        }

        setStatus(
            (
                "Local monitoring is enabled. "
                + "Use headphones during conferencing "
                + "to avoid acoustic feedback."
            )
        );
    }


    const manager =
        new window
            .WaaxalmaAudioOutputManager({
                onDevicesChanged:
                    devices => {
                        renderDevices(
                            devices
                        );

                        renderState();
                    },

                onFallback:
                    () => {
                        localStorage.removeItem(
                            MONITOR_DEVICE_STORAGE_KEY
                        );

                        monitorDeviceElement.value =
                            "";

                        renderState();
                    },
            });


    async function refreshDevices() {
        refreshButton.disabled =
            true;

        try {
            const devices =
                await manager
                    .refreshDevices();

            renderDevices(
                devices
            );

            renderState();
        }
        catch (error) {
            console.error(
                "[LocalMonitor] refresh failed",
                error
            );

            setStatus(
                (
                    "Unable to enumerate monitor outputs: "
                    + error.message
                ),
                true
            );
        }
        finally {
            refreshButton.disabled =
                false;
        }
    }


    enabledElement.addEventListener(
        "change",
        () => {
            persistEnabled(
                enabledElement.checked
            );

            renderState();
        }
    );


    monitorDeviceElement
        .addEventListener(
            "change",
            async () => {
                const deviceId =
                    monitorDeviceElement.value;

                await manager
                    .setOutputDevice(
                        deviceId
                    );

                if (deviceId) {
                    localStorage.setItem(
                        MONITOR_DEVICE_STORAGE_KEY,
                        deviceId
                    );
                }
                else {
                    localStorage.removeItem(
                        MONITOR_DEVICE_STORAGE_KEY
                    );
                }

                renderState();
            }
        );


    refreshButton.addEventListener(
        "click",
        refreshDevices
    );


    window.addEventListener(
        "storage",
        event => {
            if (
                event.key
                === PRIMARY_OUTPUT_STORAGE_KEY
            ) {
                renderState();
            }
        }
    );


    window.addEventListener(
        "beforeunload",
        () => {
            manager.stop();
        }
    );


    async function initializeMonitorSelector() {
        renderCapabilities(
            manager.capabilities
        );

        try {
            await manager.start();

            await refreshDevices();

            renderState();
        }
        catch (error) {
            console.error(
                "[LocalMonitor] initialization failed",
                error
            );

            setStatus(
                (
                    "Local monitor discovery failed: "
                    + error.message
                ),
                true
            );
        }
    }


    initializeMonitorSelector();
