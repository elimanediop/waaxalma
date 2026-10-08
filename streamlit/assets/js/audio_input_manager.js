/*
 * Waaxalma v0.4.4
 * Bidirectional Conferencing Audio & Device Control
 *
 * Slice 1 — explicit realtime input-device selection.
 *
 * Direct / Enhanced
 *     -> AudioInputManager
 *     -> selected physical microphone
 *
 * The manager owns device discovery and microphone acquisition policy.
 * The returned MediaStream remains owned by the realtime client and must
 * be stopped by that client during session cleanup.
 */

class WaaxalmaAudioInputManager {
    constructor({
        onDevicesChanged = null,
        onFallback = null,
    } = {}) {
        this._deviceId = "";
        this._onDevicesChanged =
            onDevicesChanged;
        this._onFallback =
            onFallback;

        this._boundDeviceChange =
            this._handleDeviceChange.bind(
                this
            );

        this._started = false;
    }

    get selectedDeviceId() {
        return this._deviceId;
    }

    get capabilities() {
        return {
            enumerateDevices:
                Boolean(
                    navigator.mediaDevices
                    && navigator.mediaDevices
                        .enumerateDevices
                ),

            getUserMedia:
                Boolean(
                    navigator.mediaDevices
                    && navigator.mediaDevices
                        .getUserMedia
                ),
        };
    }

    async start() {
        if (this._started) {
            return;
        }

        this._started = true;

        if (
            navigator.mediaDevices
            && navigator.mediaDevices
                .addEventListener
        ) {
            navigator.mediaDevices
                .addEventListener(
                    "devicechange",
                    this._boundDeviceChange
                );
        }

        await this.refreshDevices();
    }

    async stop() {
        if (!this._started) {
            return;
        }

        this._started = false;

        if (
            navigator.mediaDevices
            && navigator.mediaDevices
                .removeEventListener
        ) {
            navigator.mediaDevices
                .removeEventListener(
                    "devicechange",
                    this._boundDeviceChange
                );
        }
    }

    async enumerateInputs() {
        if (
            !navigator.mediaDevices
            || !navigator.mediaDevices
                .enumerateDevices
        ) {
            return [];
        }

        const devices =
            await navigator.mediaDevices
                .enumerateDevices();

        return devices
            .filter(
                device =>
                    device.kind
                    === "audioinput"
            )
            .map(
                device => ({
                    deviceId:
                        device.deviceId,

                    groupId:
                        device.groupId,

                    label:
                        (
                            device.label
                            || (
                                device.deviceId
                                === "default"
                                ? "Default microphone"
                                : "Microphone"
                            )
                        ),
                })
            );
    }

    async refreshDevices() {
        const devices =
            await this.enumerateInputs();

        if (
            this._deviceId
            && !this._deviceStillExists(
                devices,
                this._deviceId
            )
        ) {
            const previousDeviceId =
                this._deviceId;

            this._deviceId =
                "";

            if (
                typeof this._onFallback
                === "function"
            ) {
                this._onFallback({
                    previousDeviceId,
                    fallbackDeviceId: "",
                    reason:
                        "selected-device-unavailable",
                });
            }
        }

        if (
            typeof this._onDevicesChanged
            === "function"
        ) {
            this._onDevicesChanged(
                devices
            );
        }

        return devices;
    }

    async requestPermission() {
        if (
            !navigator.mediaDevices
            || !navigator.mediaDevices
                .getUserMedia
        ) {
            throw new Error(
                "Microphone access is not supported "
                + "by this browser."
            );
        }

        /*
         * Permission is requested from a user gesture.
         * Stop this temporary stream immediately. Realtime clients
         * acquire their own stream when Start is pressed.
         */
        const stream =
            await navigator.mediaDevices
                .getUserMedia({
                    audio:
                        true,
                });

        for (
            const track
            of stream.getTracks()
        ) {
            track.stop();
        }

        return this.refreshDevices();
    }

    async setInputDevice(
        deviceId
    ) {
        this._deviceId =
            (
                typeof deviceId
                === "string"
                ? deviceId
                : ""
            );
    }

    buildAudioConstraint() {
        if (!this._deviceId) {
            return true;
        }

        return {
            deviceId: {
                exact:
                    this._deviceId,
            },

            /*
             * Conferencing hotfix diagnostics:
             * explicitly request browser-side acoustic echo cancellation
             * and speech cleanup for the selected physical microphone.
             */
            echoCancellation:
                true,

            noiseSuppression:
                true,

            autoGainControl:
                true,
        };
    }

    async acquireStream() {
        if (
            !navigator.mediaDevices
            || !navigator.mediaDevices
                .getUserMedia
        ) {
            throw new Error(
                "Microphone access is not supported "
                + "by this browser."
            );
        }

        try {
            return await navigator
                .mediaDevices
                .getUserMedia({
                    audio:
                        this.buildAudioConstraint(),
                });
        }
        catch (error) {
            /*
             * If an explicitly selected device vanished between
             * enumeration and acquisition, fall back once to the
             * browser default instead of failing the session.
             */
            if (
                this._deviceId
                && (
                    error.name
                    === "NotFoundError"
                    || error.name
                    === "OverconstrainedError"
                )
            ) {
                const previousDeviceId =
                    this._deviceId;

                this._deviceId =
                    "";

                if (
                    typeof this._onFallback
                    === "function"
                ) {
                    this._onFallback({
                        previousDeviceId,
                        fallbackDeviceId: "",
                        reason:
                            "selected-device-unavailable",
                    });
                }

                return navigator
                    .mediaDevices
                    .getUserMedia({
                        audio:
                            true,
                    });
            }

            throw error;
        }
    }

    _deviceStillExists(
        devices,
        deviceId
    ) {
        return devices.some(
            device =>
                device.deviceId
                === deviceId
        );
    }

    async _handleDeviceChange() {
        try {
            await this.refreshDevices();
        }
        catch (error) {
            console.warn(
                "[AudioInput] devicechange refresh failed",
                error
            );
        }
    }
}

window.WaaxalmaAudioInputManager =
    WaaxalmaAudioInputManager;
