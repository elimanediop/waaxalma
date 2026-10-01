/*
 * Waaxalma v0.4.3
 * Universal Audio Output & Conferencing Bridge
 *
 * Shared browser-side output-device abstraction.
 *
 * Design:
 *   Standard  -> HTMLAudioElement -> AudioOutputManager
 *   Direct    -> HTMLAudioElement.srcObject -> AudioOutputManager
 *   Enhanced  -> WebAudio MediaStreamDestination -> HTMLAudioElement
 *               -> AudioOutputManager
 *
 * The selected sink is applied through HTMLMediaElement.setSinkId()
 * when supported by the browser.
 */

class WaaxalmaAudioOutputManager {
    constructor({
        onDevicesChanged = null,
        onFallback = null,
    } = {}) {
        this._deviceId = "";
        this._managedElements = new Set();

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
            enumerateDevices: Boolean(
                navigator.mediaDevices
                && navigator.mediaDevices
                    .enumerateDevices
            ),

            selectAudioOutput: Boolean(
                navigator.mediaDevices
                && navigator.mediaDevices
                    .selectAudioOutput
            ),

            setSinkId: Boolean(
                typeof HTMLMediaElement
                    !== "undefined"
                && "setSinkId"
                    in HTMLMediaElement.prototype
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

        this._managedElements.clear();
    }

    async enumerateOutputs() {
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
                    === "audiooutput"
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
                                ? "Default audio output"
                                : "Audio output"
                            )
                        ),
                })
            );
    }

    async refreshDevices() {
        const devices =
            await this.enumerateOutputs();

        if (
            this._deviceId
            && !this._deviceStillExists(
                devices,
                this._deviceId
            )
        ) {
            const previousDeviceId =
                this._deviceId;

            await this.setOutputDevice(
                ""
            );

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

    async requestOutputSelection() {
        if (
            !navigator.mediaDevices
            || !navigator.mediaDevices
                .selectAudioOutput
        ) {
            throw new Error(
                "Audio output selection prompt "
                + "is not supported by this browser."
            );
        }

        /*
         * Must be called from a user gesture
         * (button click, etc.).
         */
        const device =
            await navigator.mediaDevices
                .selectAudioOutput();

        await this.setOutputDevice(
            device.deviceId
        );

        await this.refreshDevices();

        return {
            deviceId:
                device.deviceId,

            groupId:
                device.groupId,

            label:
                (
                    device.label
                    || "Selected audio output"
                ),
        };
    }

    async setOutputDevice(
        deviceId
    ) {
        const normalizedDeviceId =
            (
                typeof deviceId === "string"
                ? deviceId
                : ""
            );

        if (
            normalizedDeviceId
            && !this.capabilities.setSinkId
        ) {
            throw new Error(
                "This browser cannot route audio "
                + "to a selected output device."
            );
        }

        /*
         * Apply first. Only update manager state
         * when all currently managed elements
         * accepted the new sink.
         */
        for (
            const mediaElement
            of this._managedElements
        ) {
            await this._applySink(
                mediaElement,
                normalizedDeviceId
            );
        }

        this._deviceId =
            normalizedDeviceId;
    }

    async registerMediaElement(
        mediaElement
    ) {
        if (
            !mediaElement
            || !(
                mediaElement
                instanceof HTMLMediaElement
            )
        ) {
            throw new TypeError(
                "Expected an HTMLMediaElement."
            );
        }

        this._managedElements.add(
            mediaElement
        );

        await this._applySink(
            mediaElement,
            this._deviceId
        );

        return mediaElement;
    }

    unregisterMediaElement(
        mediaElement
    ) {
        this._managedElements.delete(
            mediaElement
        );
    }

    async createAudioElement({
        autoplay = true,
        controls = false,
        muted = false,
    } = {}) {
        const audio =
            document.createElement(
                "audio"
            );

        audio.autoplay =
            autoplay;

        audio.controls =
            controls;

        audio.muted =
            muted;

        audio.playsInline =
            true;

        await this.registerMediaElement(
            audio
        );

        return audio;
    }

    async attachMediaStream(
        mediaElement,
        mediaStream
    ) {
        await this.registerMediaElement(
            mediaElement
        );

        mediaElement.src =
            "";

        mediaElement.srcObject =
            mediaStream;

        return mediaElement;
    }

    async attachUrl(
        mediaElement,
        url
    ) {
        await this.registerMediaElement(
            mediaElement
        );

        mediaElement.srcObject =
            null;

        mediaElement.src =
            url;

        return mediaElement;
    }

    async resetToDefault() {
        await this.setOutputDevice(
            ""
        );
    }

    async _applySink(
        mediaElement,
        deviceId
    ) {
        if (
            !deviceId
        ) {
            if (
                typeof mediaElement.setSinkId
                === "function"
            ) {
                await mediaElement.setSinkId(
                    ""
                );
            }

            return;
        }

        if (
            typeof mediaElement.setSinkId
            !== "function"
        ) {
            throw new Error(
                "HTMLMediaElement.setSinkId() "
                + "is not supported."
            );
        }

        await mediaElement.setSinkId(
            deviceId
        );
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
                "[AudioOutput] device refresh failed",
                error
            );
        }
    }
}


window.WaaxalmaAudioOutputManager =
    WaaxalmaAudioOutputManager;
