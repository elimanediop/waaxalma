/*
 * Waaxalma v0.4.4 — Slice 3
 * Conference Audio Input
 *
 * Captures an inbound conferencing/virtual-audio device independently from
 * the physical microphone used by Direct/Enhanced. Slice 3 exposes only
 * device discovery, capture lifecycle, and audio-energy observation.
 */

class WaaxalmaConferenceInputManager {
    constructor({
        onDevicesChanged = null,
        onStateChanged = null,
        onLevel = null,
        onDeviceUnavailable = null,
    } = {}) {
        this._deviceId = "";
        this._onDevicesChanged = onDevicesChanged;
        this._onStateChanged = onStateChanged;
        this._onLevel = onLevel;
        this._onDeviceUnavailable = onDeviceUnavailable;

        this._stream = null;
        this._audioContext = null;
        this._sourceNode = null;
        this._analyser = null;
        this._levelBuffer = null;
        this._animationFrameId = null;
        this._started = false;

        this._boundDeviceChange = this._handleDeviceChange.bind(this);
    }

    get selectedDeviceId() {
        return this._deviceId;
    }

    get isCapturing() {
        return Boolean(this._stream);
    }

    get capabilities() {
        return {
            enumerateDevices: Boolean(
                navigator.mediaDevices && navigator.mediaDevices.enumerateDevices
            ),
            getUserMedia: Boolean(
                navigator.mediaDevices && navigator.mediaDevices.getUserMedia
            ),
            audioContext: Boolean(window.AudioContext || window.webkitAudioContext),
        };
    }

    async start() {
        if (this._started) return;
        this._started = true;

        if (navigator.mediaDevices?.addEventListener) {
            navigator.mediaDevices.addEventListener(
                "devicechange",
                this._boundDeviceChange
            );
        }

        await this.refreshDevices();
        this._emitState("idle");
    }

    async stop() {
        await this.stopCapture();

        if (!this._started) return;
        this._started = false;

        if (navigator.mediaDevices?.removeEventListener) {
            navigator.mediaDevices.removeEventListener(
                "devicechange",
                this._boundDeviceChange
            );
        }
    }

    async enumerateInputs() {
        if (!navigator.mediaDevices?.enumerateDevices) return [];

        const devices = await navigator.mediaDevices.enumerateDevices();

        return devices
            .filter(device => device.kind === "audioinput")
            .map(device => ({
                deviceId: device.deviceId,
                groupId: device.groupId,
                label: device.label || (
                    device.deviceId === "default"
                        ? "Default audio input"
                        : "Audio input"
                ),
            }));
    }

    async refreshDevices() {
        const devices = await this.enumerateInputs();

        if (
            this._deviceId &&
            !devices.some(device => device.deviceId === this._deviceId)
        ) {
            const previousDeviceId = this._deviceId;
            this._deviceId = "";

            if (this.isCapturing) {
                await this.stopCapture();
            }

            if (typeof this._onDeviceUnavailable === "function") {
                this._onDeviceUnavailable({ previousDeviceId });
            }
        }

        if (typeof this._onDevicesChanged === "function") {
            this._onDevicesChanged(devices);
        }

        return devices;
    }

    async requestPermission() {
        if (!navigator.mediaDevices?.getUserMedia) {
            throw new Error("Audio input access is not supported by this browser.");
        }

        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach(track => track.stop());
        return this.refreshDevices();
    }

    async setInputDevice(deviceId) {
        const normalized = typeof deviceId === "string" ? deviceId : "";
        if (normalized === this._deviceId) return;

        if (this.isCapturing) {
            await this.stopCapture();
        }

        this._deviceId = normalized;
        this._emitState("idle");
    }

    buildAudioConstraint() {
        const constraint = {
            echoCancellation: false,
            noiseSuppression: false,
            autoGainControl: false,
        };

        if (this._deviceId) {
            constraint.deviceId = { exact: this._deviceId };
        }

        return constraint;
    }

    async startCapture() {
        if (this.isCapturing) return this._stream;
        if (!navigator.mediaDevices?.getUserMedia) {
            throw new Error("Audio input access is not supported by this browser.");
        }

        this._emitState("starting");

        let stream;
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                audio: this.buildAudioConstraint(),
            });
        } catch (error) {
            // Fail closed. If a selected virtual input vanished, do not silently
            // fall back to the physical/default microphone.
            if (
                this._deviceId &&
                (error.name === "NotFoundError" || error.name === "OverconstrainedError")
            ) {
                const previousDeviceId = this._deviceId;
                this._deviceId = "";
                if (typeof this._onDeviceUnavailable === "function") {
                    this._onDeviceUnavailable({ previousDeviceId });
                }
            }

            this._emitState("error");
            throw error;
        }

        this._stream = stream;

        const AudioContextClass = window.AudioContext || window.webkitAudioContext;
        if (AudioContextClass) {
            this._audioContext = new AudioContextClass();
            if (this._audioContext.state === "suspended") {
                await this._audioContext.resume();
            }

            this._sourceNode = this._audioContext.createMediaStreamSource(stream);
            this._analyser = this._audioContext.createAnalyser();
            this._analyser.fftSize = 1024;
            this._analyser.smoothingTimeConstant = 0.35;
            this._levelBuffer = new Float32Array(this._analyser.fftSize);
            this._sourceNode.connect(this._analyser);
            this._scheduleLevelRead();
        }

        for (const track of stream.getAudioTracks()) {
            track.addEventListener(
                "ended",
                () => {
                    if (this._stream === stream) {
                        this.stopCapture().catch(error => {
                            console.warn("[ConferenceInput] track-end cleanup failed", error);
                        });
                    }
                },
                { once: true }
            );
        }

        this._emitState("capturing");
        return stream;
    }

    async stopCapture() {
        if (this._animationFrameId !== null) {
            cancelAnimationFrame(this._animationFrameId);
            this._animationFrameId = null;
        }

        if (this._sourceNode) {
            try { this._sourceNode.disconnect(); } catch (_) {}
            this._sourceNode = null;
        }

        if (this._analyser) {
            try { this._analyser.disconnect(); } catch (_) {}
            this._analyser = null;
        }

        this._levelBuffer = null;

        if (this._audioContext) {
            try { await this._audioContext.close(); } catch (_) {}
            this._audioContext = null;
        }

        if (this._stream) {
            this._stream.getTracks().forEach(track => track.stop());
            this._stream = null;
        }

        this._emitLevel(0, -120);
        this._emitState("idle");
    }

    _scheduleLevelRead() {
        if (!this._analyser || !this._levelBuffer) return;

        this._analyser.getFloatTimeDomainData(this._levelBuffer);
        let sumSquares = 0;

        for (const sample of this._levelBuffer) {
            sumSquares += sample * sample;
        }

        const rms = Math.sqrt(sumSquares / this._levelBuffer.length);
        const dbfs = rms > 0 ? 20 * Math.log10(rms) : -120;
        this._emitLevel(rms, Math.max(-120, dbfs));

        this._animationFrameId = requestAnimationFrame(
            () => this._scheduleLevelRead()
        );
    }

    _emitState(state) {
        if (typeof this._onStateChanged === "function") {
            this._onStateChanged({
                state,
                deviceId: this._deviceId,
                capturing: this.isCapturing,
            });
        }
    }

    _emitLevel(rms, dbfs) {
        if (typeof this._onLevel === "function") {
            this._onLevel({ rms, dbfs });
        }
    }

    async _handleDeviceChange() {
        try {
            await this.refreshDevices();
        } catch (error) {
            console.warn("[ConferenceInput] devicechange refresh failed", error);
        }
    }
}

window.WaaxalmaConferenceInputManager = WaaxalmaConferenceInputManager;
