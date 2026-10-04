
    const STORAGE_KEY =
        "waaxalma.audioOutputDeviceId";

    const outputDeviceElement =
        document.getElementById(
            "outputDevice"
        );

    const refreshButton =
        document.getElementById(
            "refreshButton"
        );

    const chooseButton =
        document.getElementById(
            "chooseButton"
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
        isError = false
    ) {
        statusElement.textContent =
            message;

        statusElement.classList.toggle(
            "error",
            isError
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
                + " · selectAudioOutput: "
                + (
                    capabilities.selectAudioOutput
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
            device.deviceId === "default"
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
            outputDeviceElement.value;

        outputDeviceElement.innerHTML =
            "";

        const defaultOption =
            document.createElement(
                "option"
            );

        defaultOption.value =
            "";

        defaultOption.textContent =
            "Default audio output";

        outputDeviceElement.appendChild(
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

                outputDeviceElement
                    .appendChild(
                        option
                    );
            }
        );

        const savedDeviceId =
            localStorage.getItem(
                STORAGE_KEY
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

        outputDeviceElement.value =
            exists
            ? preferredValue
            : "";

        if (!exists) {
            localStorage.removeItem(
                STORAGE_KEY
            );
        }
    }

    const manager =
        new window
            .WaaxalmaAudioOutputManager({
                onDevicesChanged:
                    devices => {
                        renderDevices(
                            devices
                        );

                        setStatus(
                            (
                                devices.length
                                + (
                                    devices.length === 1
                                    ? " audio output detected."
                                    : " audio outputs detected."
                                )
                            )
                        );
                    },

                onFallback:
                    () => {
                        localStorage.removeItem(
                            STORAGE_KEY
                        );

                        outputDeviceElement.value =
                            "";

                        setStatus(
                            (
                                "The selected output "
                                + "disappeared. "
                                + "Falling back to default."
                            )
                        );
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

            setStatus(
                (
                    devices.length
                    + (
                        devices.length === 1
                        ? " audio output detected."
                        : " audio outputs detected."
                    )
                )
            );
        }
        catch (error) {
            console.error(
                "[AudioOutput] refresh failed",
                error
            );

            setStatus(
                (
                    "Unable to enumerate audio outputs: "
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

    async function chooseOutputDevice() {
        chooseButton.disabled =
            true;

        try {
            const device =
                await manager
                    .requestOutputSelection();

            localStorage.setItem(
                STORAGE_KEY,
                device.deviceId
            );

            await refreshDevices();

            outputDeviceElement.value =
                device.deviceId;

            setStatus(
                (
                    "Selected: "
                    + (
                        device.label
                        || "audio output"
                    )
                )
            );
        }
        catch (error) {
            if (
                error.name
                === "NotAllowedError"
            ) {
                setStatus(
                    "Audio output selection was cancelled."
                );

                return;
            }

            console.error(
                "[AudioOutput] selection failed",
                error
            );

            setStatus(
                (
                    "Unable to choose audio output: "
                    + error.message
                ),
                true
            );
        }
        finally {
            chooseButton.disabled =
                !manager.capabilities
                    .selectAudioOutput;
        }
    }

    outputDeviceElement
        .addEventListener(
            "change",
            async () => {
                const deviceId =
                    outputDeviceElement
                        .value;

                try {
                    await manager
                        .setOutputDevice(
                            deviceId
                        );

                    if (deviceId) {
                        localStorage.setItem(
                            STORAGE_KEY,
                            deviceId
                        );
                    }
                    else {
                        localStorage.removeItem(
                            STORAGE_KEY
                        );
                    }

                    const selectedOption =
                        outputDeviceElement
                            .selectedOptions[0];

                    setStatus(
                        (
                            "Selected: "
                            + (
                                selectedOption
                                    ?.textContent
                                || "Default audio output"
                            )
                        )
                    );
                }
                catch (error) {
                    console.error(
                        (
                            "[AudioOutput] "
                            + "setOutputDevice failed"
                        ),
                        error
                    );

                    setStatus(
                        (
                            "Unable to select this output: "
                            + error.message
                        ),
                        true
                    );
                }
            }
        );

    refreshButton
        .addEventListener(
            "click",
            refreshDevices
        );

    chooseButton
        .addEventListener(
            "click",
            chooseOutputDevice
        );

    window.addEventListener(
        "beforeunload",
        () => {
            manager.stop();
        }
    );

    async function initializeAudioOutput() {
        renderCapabilities(
            manager.capabilities
        );

        chooseButton.disabled =
            !manager.capabilities
                .selectAudioOutput;

        try {
            await manager.start();
            await refreshDevices();
        }
        catch (error) {
            console.error(
                "[AudioOutput] initialization failed",
                error
            );

            setStatus(
                (
                    "Audio output discovery failed: "
                    + error.message
                ),
                true
            );
        }
    }

    initializeAudioOutput();
