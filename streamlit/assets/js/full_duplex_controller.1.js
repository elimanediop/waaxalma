
    const OUTBOUND_MODE =
        "__OUTBOUND_MODE_VALUE__";

    const COMMAND_KEY =
        "waaxalma.fullDuplex.command";

    const DESIRED_KEY =
        "waaxalma.fullDuplex.desired";

    const DIRECT_STATUS_KEY =
        "waaxalma.fullDuplex.outbound.direct.status";

    const ENHANCED_STATUS_KEY =
        "waaxalma.fullDuplex.outbound.enhanced.status";

    const INBOUND_STATUS_KEY =
        "waaxalma.fullDuplex.inbound.status";


    const startButton =
        document.getElementById(
            "startButton"
        );

    const stopButton =
        document.getElementById(
            "stopButton"
        );

    const outboundDot =
        document.getElementById(
            "outboundDot"
        );

    const inboundDot =
        document.getElementById(
            "inboundDot"
        );

    const outboundStatusElement =
        document.getElementById(
            "outboundStatus"
        );

    const inboundStatusElement =
        document.getElementById(
            "inboundStatus"
        );

    const summaryElement =
        document.getElementById(
            "summary"
        );


    let commandSequence =
        0;

    let failSafePending =
        false;


    function safeParse(
        value
    ) {
        if (!value) {
            return null;
        }

        try {
            return JSON.parse(
                value
            );
        }
        catch (_) {
            return null;
        }
    }


    function outboundStatusKey() {
        return (
            OUTBOUND_MODE === "enhanced"
            ? ENHANCED_STATUS_KEY
            : DIRECT_STATUS_KEY
        );
    }


    function readStatus(
        key
    ) {
        return (
            safeParse(
                localStorage.getItem(
                    key
                )
            )
            || {
                state:
                    "stopped",

                message:
                    "Stopped",
            }
        );
    }


    function readDesired() {
        return (
            safeParse(
                localStorage.getItem(
                    DESIRED_KEY
                )
            )
            || {
                active:
                    false,

                outboundMode:
                    OUTBOUND_MODE,
            }
        );
    }


    function normalizeState(
        state
    ) {
        if (state === "live") {
            return "live";
        }

        if (
            state === "connecting"
            || state === "starting"
            || state === "reconnecting"
        ) {
            return "connecting";
        }

        if (state === "error") {
            return "error";
        }

        return "stopped";
    }


    function setSummary(
        message,
        isError = false
    ) {
        summaryElement.textContent =
            message;

        summaryElement.classList.toggle(
            "error",
            isError
        );
    }


    function renderDirection(
        dot,
        text,
        status
    ) {
        const state =
            normalizeState(
                status.state
            );

        dot.className =
            "dot " + state;

        text.textContent =
            (
                status.message
                || (
                    state === "live"
                    ? "Live"
                    : state === "connecting"
                    ? "Connecting"
                    : state === "error"
                    ? "Error"
                    : "Stopped"
                )
            );
    }


    function issueCommand(
        action,
        reason
    ) {
        commandSequence +=
            1;

        const command = {
            id:
                (
                    Date.now().toString()
                    + "-"
                    + commandSequence.toString()
                ),

            action:
                action,

            outboundMode:
                OUTBOUND_MODE,

            reason:
                reason,

            issuedAt:
                Date.now(),
        };

        localStorage.setItem(
            COMMAND_KEY,
            JSON.stringify(
                command
            )
        );

        return command;
    }


    function startFullDuplex() {
        const desired = {
            active:
                true,

            outboundMode:
                OUTBOUND_MODE,

            sessionId:
                (
                    "fd-"
                    + Date.now().toString()
                ),

            startedAt:
                Date.now(),
        };

        localStorage.setItem(
            DESIRED_KEY,
            JSON.stringify(
                desired
            )
        );

        issueCommand(
            "start",
            "full-duplex-start"
        );

        failSafePending =
            false;

        setSummary(
            (
                "Starting outbound "
                + OUTBOUND_MODE
                + " and inbound translation..."
            )
        );

        render();
    }


    function stopFullDuplex(
        reason = "user-stop"
    ) {
        const desired =
            readDesired();

        desired.active =
            false;

        desired.stoppedAt =
            Date.now();

        desired.stopReason =
            reason;

        localStorage.setItem(
            DESIRED_KEY,
            JSON.stringify(
                desired
            )
        );

        issueCommand(
            "stop",
            reason
        );

        setSummary(
            (
                reason === "direction-error"
                ? (
                    "A direction failed. Stop All was issued "
                    + "to avoid leaving an orphaned session."
                )
                : "Stopping outbound and inbound..."
            ),
            reason === "direction-error"
        );

        render();
    }


    function maybeFailSafeStop(
        outboundStatus,
        inboundStatus,
        desired
    ) {
        if (
            !desired.active
            || failSafePending
        ) {
            return;
        }

        const outboundState =
            normalizeState(
                outboundStatus.state
            );

        const inboundState =
            normalizeState(
                inboundStatus.state
            );

        if (
            outboundState === "error"
            || inboundState === "error"
        ) {
            failSafePending =
                true;

            window.setTimeout(
                () => {
                    stopFullDuplex(
                        "direction-error"
                    );
                },
                150
            );
        }
    }


    function render() {
        const desired =
            readDesired();

        const outboundStatus =
            readStatus(
                outboundStatusKey()
            );

        const inboundStatus =
            readStatus(
                INBOUND_STATUS_KEY
            );

        renderDirection(
            outboundDot,
            outboundStatusElement,
            outboundStatus
        );

        renderDirection(
            inboundDot,
            inboundStatusElement,
            inboundStatus
        );

        const activeForThisMode =
            Boolean(
                desired.active
                && desired.outboundMode
                    === OUTBOUND_MODE
            );

        startButton.disabled =
            activeForThisMode;

        stopButton.disabled =
            !desired.active;

        if (
            activeForThisMode
        ) {
            const outboundState =
                normalizeState(
                    outboundStatus.state
                );

            const inboundState =
                normalizeState(
                    inboundStatus.state
                );

            if (
                outboundState === "live"
                && inboundState === "live"
            ) {
                setSummary(
                    (
                        "Full Duplex live. "
                        + "Outbound audio goes to the conference; "
                        + "inbound translated audio goes only to Local Monitor."
                    )
                );
            }
            else if (
                outboundState === "error"
                || inboundState === "error"
            ) {
                setSummary(
                    (
                        "A direction reported an error. "
                        + "Fail-safe Stop All is being issued."
                    ),
                    true
                );
            }
            else {
                setSummary(
                    (
                        "Full Duplex is starting. "
                        + "Waiting for both directions to become live."
                    )
                );
            }
        }
        else if (
            desired.active
        ) {
            setSummary(
                (
                    "A Full Duplex session is active with outbound mode "
                    + desired.outboundMode
                    + ". Stop it before switching modes."
                ),
                true
            );

            startButton.disabled =
                true;
        }

        maybeFailSafeStop(
            outboundStatus,
            inboundStatus,
            desired
        );
    }


    startButton.addEventListener(
        "click",
        startFullDuplex
    );


    stopButton.addEventListener(
        "click",
        () => {
            stopFullDuplex(
                "user-stop"
            );
        }
    );


    window.addEventListener(
        "storage",
        event => {
            if (
                [
                    DESIRED_KEY,
                    DIRECT_STATUS_KEY,
                    ENHANCED_STATUS_KEY,
                    INBOUND_STATUS_KEY,
                ].includes(
                    event.key
                )
            ) {
                render();
            }
        }
    );


    render();
