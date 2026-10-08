/*
 * Waaxalma v1.1.1
 * Conference Audio Isolation
 *
 * Common outbound source-protection layer for Direct and Enhanced.
 * Lifecycle is deliberately independent from Full Duplex coordination.
 *
 * IMPORTANT: browser AEC alone cannot remove conference playback that is
 * already present in the microphone track. When a conference reference
 * stream is supplied, this implementation uses reference-VAD gating to
 * prevent remote-only speech from being treated as outbound user speech.
 */

class WaaxalmaConferenceAudioIsolation {
    constructor({
        enabled = true,
        referenceRmsThreshold = 0.015,
        releaseMs = 180,
        debug = false,
    } = {}) {
        this._enabled = enabled;
        this._referenceRmsThreshold = referenceRmsThreshold;
        this._releaseMs = releaseMs;
        this._debug = debug;

        this._audioContext = null;
        this._sourceNode = null;
        this._outputGain = null;
        this._destination = null;
        this._referenceNode = null;
        this._referenceAnalyser = null;
        this._referenceSilentGain = null;
        this._referenceFrameId = null;
        this._releaseTimer = null;
        this._rawStream = null;
        this._referenceStream = null;
        this._isolatedStream = null;
        this._referenceActive = false;
    }

    get enabled() {
        return this._enabled;
    }

    get referenceActive() {
        return this._referenceActive;
    }

    get hasReference() {
        return Boolean(
            this._referenceStream
            && this._referenceStream.getAudioTracks().some(
                track => track.readyState === "live"
            )
        );
    }

    async process(inputStream) {
        if (!inputStream || inputStream.getAudioTracks().length === 0) {
            throw new Error("ConferenceAudioIsolation requires an audio input stream.");
        }

        await this._ensureAudioContext();
        this._disconnectSourceGraph();

        this._rawStream = inputStream;
        this._sourceNode = this._audioContext.createMediaStreamSource(inputStream);
        this._outputGain = this._audioContext.createGain();
        this._destination = this._audioContext.createMediaStreamDestination();

        this._outputGain.gain.value = 1;
        this._sourceNode.connect(this._outputGain);
        this._outputGain.connect(this._destination);
        this._isolatedStream = this._destination.stream;

        if (this._referenceStream) {
            await this._startReferenceMonitor();
        }

        this._log("source ready", {
            enabled: this._enabled,
            hasReference: this.hasReference,
            inputTrack: inputStream.getAudioTracks()[0]?.label || "",
        });

        return this._isolatedStream;
    }

    async setReferenceStream(stream) {
        this._referenceStream = stream || null;

        if (!this._audioContext || !this._rawStream) {
            return;
        }

        this._stopReferenceMonitor();

        if (this._referenceStream) {
            await this._startReferenceMonitor();
        } else {
            this._setReferenceActive(false);
        }
    }

    clearReferenceStream() {
        this._referenceStream = null;
        this._stopReferenceMonitor();
        this._setReferenceActive(false);
    }

    async stop() {
        this.clearReferenceStream();
        this._disconnectSourceGraph();
        this._rawStream = null;
        this._isolatedStream = null;

        if (this._audioContext && this._audioContext.state !== "closed") {
            try {
                await this._audioContext.close();
            } catch (_) {
                // Best-effort cleanup.
            }
        }
        this._audioContext = null;
    }

    async _ensureAudioContext() {
        if (!this._audioContext || this._audioContext.state === "closed") {
            this._audioContext = new AudioContext();
        }
        if (this._audioContext.state === "suspended") {
            await this._audioContext.resume();
        }
    }

    async _startReferenceMonitor() {
        if (!this._referenceStream || !this._audioContext) {
            return;
        }

        const liveTrack = this._referenceStream.getAudioTracks().find(
            track => track.readyState === "live"
        );
        if (!liveTrack) {
            return;
        }

        this._stopReferenceMonitor();

        this._referenceNode = this._audioContext.createMediaStreamSource(
            new MediaStream([liveTrack])
        );
        this._referenceAnalyser = this._audioContext.createAnalyser();
        this._referenceAnalyser.fftSize = 512;
        this._referenceSilentGain = this._audioContext.createGain();
        this._referenceSilentGain.gain.value = 0;

        this._referenceNode.connect(this._referenceAnalyser);
        this._referenceAnalyser.connect(this._referenceSilentGain);
        this._referenceSilentGain.connect(this._audioContext.destination);

        const detect = () => {
            if (!this._referenceAnalyser) {
                return;
            }

            const rms = this._calculateRms(this._referenceAnalyser);
            if (rms >= this._referenceRmsThreshold) {
                this._setReferenceActive(true);
                if (this._releaseTimer !== null) {
                    clearTimeout(this._releaseTimer);
                    this._releaseTimer = null;
                }
            } else if (this._referenceActive && this._releaseTimer === null) {
                this._releaseTimer = setTimeout(() => {
                    this._releaseTimer = null;
                    this._setReferenceActive(false);
                }, this._releaseMs);
            }

            this._referenceFrameId = requestAnimationFrame(detect);
        };

        this._referenceFrameId = requestAnimationFrame(detect);
        this._log("reference monitor started", {
            label: liveTrack.label || "",
            threshold: this._referenceRmsThreshold,
        });
    }

    _setReferenceActive(active) {
        if (this._referenceActive === active) {
            return;
        }
        this._referenceActive = active;

        if (!this._outputGain || !this._audioContext) {
            return;
        }

        const targetGain = (
            this._enabled && active
                ? 0
                : 1
        );

        const now = this._audioContext.currentTime;
        this._outputGain.gain.cancelScheduledValues(now);
        this._outputGain.gain.setTargetAtTime(
            targetGain,
            now,
            active ? 0.008 : 0.025
        );

        this._log(active ? "conference return blocked" : "microphone released");
    }

    _calculateRms(analyser) {
        const data = new Uint8Array(analyser.fftSize);
        analyser.getByteTimeDomainData(data);
        let sum = 0;
        for (let i = 0; i < data.length; i += 1) {
            const sample = (data[i] - 128) / 128;
            sum += sample * sample;
        }
        return Math.sqrt(sum / data.length);
    }

    _stopReferenceMonitor() {
        if (this._referenceFrameId !== null) {
            cancelAnimationFrame(this._referenceFrameId);
            this._referenceFrameId = null;
        }
        if (this._releaseTimer !== null) {
            clearTimeout(this._releaseTimer);
            this._releaseTimer = null;
        }
        for (const node of [
            this._referenceNode,
            this._referenceAnalyser,
            this._referenceSilentGain,
        ]) {
            try {
                node?.disconnect();
            } catch (_) {
                // Best-effort cleanup.
            }
        }
        this._referenceNode = null;
        this._referenceAnalyser = null;
        this._referenceSilentGain = null;
    }

    _disconnectSourceGraph() {
        for (const node of [this._sourceNode, this._outputGain]) {
            try {
                node?.disconnect();
            } catch (_) {
                // Best-effort cleanup.
            }
        }
        this._sourceNode = null;
        this._outputGain = null;
        this._destination = null;
    }

    _log(message, details = undefined) {
        if (!this._debug) {
            return;
        }
        if (details === undefined) {
            console.debug(`[Waaxalma][AudioIsolation] ${message}`);
        } else {
            console.debug(`[Waaxalma][AudioIsolation] ${message}`, details);
        }
    }
}

window.WaaxalmaConferenceAudioIsolation =
    WaaxalmaConferenceAudioIsolation;

/*
 * Shared singleton. Conference Input can provide its capture stream without
 * depending on Full Duplex lifecycle:
 *
 *   await window.WaaxalmaConferenceAudioIsolationInstance
 *       .setReferenceStream(conferenceInputStream);
 */
window.WaaxalmaConferenceAudioIsolationInstance =
    window.WaaxalmaConferenceAudioIsolationInstance
    || new WaaxalmaConferenceAudioIsolation();
