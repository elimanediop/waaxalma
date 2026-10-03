
    const STORAGE_KEY =
        "waaxalma.audioInputDeviceId";

    const inputDeviceElement =
        document.getElementById(
            "inputDevice"
        );

    const refreshButton =
        document.getElementById(
            "refreshButton"
        );

    const permissionButton =
        document.getElementById(
            "permissionButton"
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
                + " · getUserMedia: "
                + (
                    capabilities.getUserMedia
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
                || "Default microphone"
            );
        }

        return (
            device.label
            || (
                "Microphone "
                + String(index + 1)
            )
        );
    }

    function renderDevices(
        devices
    ) {
        const previousValue =
            inputDeviceElement.value;

        inputDeviceElement.innerHTML =
            "";

        const defaultOption =
            document.createElement(
                "option"
            );

        defaultOption.value =
            "";

        defaultOption.textContent =
            "Default microphone";

        inputDeviceElement.appendChild(
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

                inputDeviceElement
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

        inputDeviceElement.value =
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
            .WaaxalmaAudioInputManager({
                onDevicesChanged:
                    devices => {
                        renderDevices(
                            devices
                        );
                    },

                onFallback:
                    () => {
                        localStorage.removeItem(
                            STORAGE_KEY
                        );

                        inputDeviceElement.value =
                            "";

                        setStatus(
                            (
                                "The selected microphone "
                                + "disappeared. "
                                + "Falling back to default."
                            )
                        );
                    },
            });

    async function applySavedSelection() {
        const savedDeviceId =
            localStorage.getItem(
                STORAGE_KEY
            ) || "";

        await manager
            .setInputDevice(
                savedDeviceId
            );
    }

    async function refreshDevices() {
        refreshButton.disabled =
            true;

        try {
            await applySavedSelection();

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
                        ? " microphone detected."
                        : " microphones detected."
                    )
                    + " Selection is used by Direct "
                    + "and Enhanced on the next Start."
                )
            );
        }
        catch (error) {
            console.error(
                "[AudioInput] refresh failed",
                error
            );

            setStatus(
                (
                    "Unable to enumerate microphones: "
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

    async function requestPermission() {
        permissionButton.disabled =
            true;

        try {
            await manager
                .requestPermission();

            await refreshDevices();

            setStatus(
                (
                    "Microphone access granted. "
                    + "Select the physical microphone "
                    + "used by Waaxalma."
                )
            );
        }
        catch (error) {
            if (
                error.name
                === "NotAllowedError"
            ) {
                setStatus(
                    (
                        "Microphone permission was denied. "
                        + "Allow microphone access in the "
                        + "browser site settings."
                    ),
                    true
                );

                return;
            }

            console.error(
                "[AudioInput] permission failed",
                error
            );

            setStatus(
                (
                    "Unable to request microphone access: "
                    + error.message
                ),
                true
            );
        }
        finally {
            permissionButton.disabled =
                !manager.capabilities
                    .getUserMedia;
        }
    }

    inputDeviceElement
        .addEventListener(
            "change",
            async () => {
                const deviceId =
                    inputDeviceElement.value;

                await manager
                    .setInputDevice(
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
                    inputDeviceElement
                        .selectedOptions[0];

                setStatus(
                    (
                        "Selected: "
                        + (
                            selectedOption
                                ?.textContent
                            || "Default microphone"
                        )
                        + ". Applied on the next "
                        + "Direct / Enhanced Start."
                    )
                );
            }
        );

    refreshButton
        .addEventListener(
            "click",
            refreshDevices
        );

    permissionButton
        .addEventListener(
            "click",
            requestPermission
        );

    window.addEventListener(
        "beforeunload",
        () => {
            manager.stop();
        }
    );

    async function initializeAudioInput() {
        renderCapabilities(
            manager.capabilities
        );

        permissionButton.disabled =
            !manager.capabilities
                .getUserMedia;

        try {
            await manager.start();
            await refreshDevices();
        }
        catch (error) {
            console.error(
                "[AudioInput] initialization failed",
                error
            );

            setStatus(
                (
                    "Microphone discovery failed: "
                    + error.message
                ),
                true
            );
        }
    }

    initializeAudioInput();
