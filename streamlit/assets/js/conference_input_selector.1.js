
    const STORAGE_KEY = "waaxalma.conferenceInputDeviceId";
    const PHYSICAL_INPUT_STORAGE_KEY = "waaxalma.audioInputDeviceId";

    const deviceElement = document.getElementById("conferenceInputDevice");
    const refreshButton = document.getElementById("refreshButton");
    const permissionButton = document.getElementById("permissionButton");
    const captureButton = document.getElementById("captureButton");
    const meterFillElement = document.getElementById("meterFill");
    const dbfsElement = document.getElementById("dbfs");
    const statusElement = document.getElementById("status");
    const capabilitiesElement = document.getElementById("capabilities");

    function setStatus(message, state = "") {
        statusElement.textContent = message;
        statusElement.classList.toggle("error", state === "error");
        statusElement.classList.toggle("live", state === "live");
    }

    function renderCapabilities(capabilities) {
        capabilitiesElement.textContent =
            "enumerateDevices: " + (capabilities.enumerateDevices ? "yes" : "no")
            + " · getUserMedia: " + (capabilities.getUserMedia ? "yes" : "no")
            + " · AudioContext: " + (capabilities.audioContext ? "yes" : "no");
    }

    function labelFor(device, index) {
        if (device.deviceId === "default") {
            return device.label || "Default audio input";
        }
        return device.label || ("Audio input " + String(index + 1));
    }

    function renderDevices(devices) {
        const previousValue = deviceElement.value;
        deviceElement.innerHTML = "";

        const defaultOption = document.createElement("option");
        defaultOption.value = "";
        defaultOption.textContent = "Default audio input";
        deviceElement.appendChild(defaultOption);

        devices.forEach((device, index) => {
            if (!device.deviceId || device.deviceId === "default") return;
            const option = document.createElement("option");
            option.value = device.deviceId;
            option.textContent = labelFor(device, index);
            deviceElement.appendChild(option);
        });

        const savedDeviceId = localStorage.getItem(STORAGE_KEY) || "";
        const preferred = savedDeviceId || previousValue || "";
        const exists = preferred === "" || devices.some(
            device => device.deviceId === preferred
        );

        deviceElement.value = exists ? preferred : "";
        if (!exists) localStorage.removeItem(STORAGE_KEY);
        renderSelectionWarning();
    }

    function renderSelectionWarning() {
        const conferenceDeviceId = deviceElement.value;
        const physicalDeviceId = localStorage.getItem(PHYSICAL_INPUT_STORAGE_KEY) || "";

        if (
            conferenceDeviceId &&
            physicalDeviceId &&
            conferenceDeviceId === physicalDeviceId
        ) {
            setStatus(
                "Conference Input matches the physical Waaxalma microphone. "
                + "Select a separate virtual-cable input before bidirectional translation.",
                "error"
            );
            return true;
        }
        return false;
    }

    function updateCaptureButton(capturing) {
        captureButton.textContent = capturing ? "Stop capture" : "Start capture";
        deviceElement.disabled = capturing;
        refreshButton.disabled = capturing;
        permissionButton.disabled = capturing || !manager.capabilities.getUserMedia;
    }

    function updateLevel({ rms, dbfs }) {
        const normalizedDb = Math.min(0, Math.max(-60, dbfs));
        const percent = ((normalizedDb + 60) / 60) * 100;
        meterFillElement.style.width = (
            Number.isFinite(percent) ? percent.toFixed(1) : "0"
        ) + "%";
        dbfsElement.textContent = (
            Number.isFinite(dbfs) ? dbfs.toFixed(1) : "-120.0"
        ) + " dBFS";
        meterFillElement.style.opacity = rms > 0.003 ? "0.90" : "0.35";
    }

    const manager = new window.WaaxalmaConferenceInputManager({
        onDevicesChanged: devices => renderDevices(devices),
        onStateChanged: ({ state, capturing }) => {
            updateCaptureButton(capturing);

            if (state === "starting") {
                setStatus("Starting conference input capture...");
            } else if (state === "capturing") {
                setStatus(
                    "Conference input is live. Play remote/conference audio into "
                    + "the selected virtual cable and verify the incoming level.",
                    "live"
                );
            } else if (state === "idle" && !renderSelectionWarning()) {
                setStatus(
                    "Ready. Slice 3 captures incoming conference audio only; "
                    + "it does not run STT or translation yet."
                );
            }
        },
        onLevel: updateLevel,
        onDeviceUnavailable: () => {
            localStorage.removeItem(STORAGE_KEY);
            deviceElement.value = "";
            setStatus(
                "The selected conference input disappeared. Capture was stopped. "
                + "Select the virtual cable again.",
                "error"
            );
        },
    });

    async function applySavedSelection() {
        await manager.setInputDevice(localStorage.getItem(STORAGE_KEY) || "");
    }

    async function refreshDevices() {
        refreshButton.disabled = true;
        try {
            await applySavedSelection();
            const devices = await manager.refreshDevices();
            renderDevices(devices);

            if (!renderSelectionWarning() && !manager.isCapturing) {
                setStatus(
                    String(devices.length)
                    + (devices.length === 1 ? " audio input detected. " : " audio inputs detected. ")
                    + "Select the virtual cable carrying conference speaker audio."
                );
            }
        } catch (error) {
            console.error("[ConferenceInput] refresh failed", error);
            setStatus("Unable to enumerate conference inputs: " + error.message, "error");
        } finally {
            if (!manager.isCapturing) refreshButton.disabled = false;
        }
    }

    async function requestPermission() {
        permissionButton.disabled = true;
        try {
            await manager.requestPermission();
            await refreshDevices();
            setStatus(
                "Audio input access granted. Select the virtual cable used for conference audio."
            );
        } catch (error) {
            if (error.name === "NotAllowedError") {
                setStatus(
                    "Audio input permission was denied. Allow microphone/audio access "
                    + "in the browser site settings.",
                    "error"
                );
                return;
            }
            console.error("[ConferenceInput] permission failed", error);
            setStatus("Unable to request audio input access: " + error.message, "error");
        } finally {
            permissionButton.disabled = manager.isCapturing || !manager.capabilities.getUserMedia;
        }
    }

    async function toggleCapture() {
        if (manager.isCapturing) {
            await manager.stopCapture();
            return;
        }
        if (renderSelectionWarning()) return;

        try {
            await manager.startCapture();
        } catch (error) {
            console.error("[ConferenceInput] capture failed", error);
            setStatus("Unable to start conference capture: " + error.message, "error");
            updateCaptureButton(false);
        }
    }

    deviceElement.addEventListener("change", async () => {
        const deviceId = deviceElement.value;
        await manager.setInputDevice(deviceId);

        if (deviceId) localStorage.setItem(STORAGE_KEY, deviceId);
        else localStorage.removeItem(STORAGE_KEY);

        if (!renderSelectionWarning()) {
            const selected = deviceElement.selectedOptions[0];
            setStatus(
                "Selected conference input: "
                + (selected?.textContent || "Default audio input")
                + ". Press Start capture to verify incoming audio energy."
            );
        }
    });

    refreshButton.addEventListener("click", refreshDevices);
    permissionButton.addEventListener("click", requestPermission);
    captureButton.addEventListener("click", () => {
        toggleCapture().catch(error => {
            console.error("[ConferenceInput] capture toggle failed", error);
        });
    });

    window.addEventListener("storage", event => {
        if (event.key === PHYSICAL_INPUT_STORAGE_KEY) renderSelectionWarning();
    });

    window.addEventListener("beforeunload", () => manager.stop());

    async function initializeConferenceInput() {
        renderCapabilities(manager.capabilities);
        permissionButton.disabled = !manager.capabilities.getUserMedia;
        updateCaptureButton(false);
        updateLevel({ rms: 0, dbfs: -120 });

        try {
            await manager.start();
            await refreshDevices();
        } catch (error) {
            console.error("[ConferenceInput] initialization failed", error);
            setStatus("Conference input initialization failed: " + error.message, "error");
        }
    }

    initializeConferenceInput();
