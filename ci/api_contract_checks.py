"""Compare HTTP and WebSocket schemas with reviewed versioned snapshots."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Annotated, Union

ROOT = Path(__file__).resolve().parents[1]


def schemas():
    sys.path.insert(0, str(ROOT / "backend"))
    from app.main import app
    from pydantic import Field, TypeAdapter
    from app.core.realtime_enhanced_events import (
        RealtimeEnhancedStartEvent, RealtimeEnhancedResetEvent,
        RealtimeEnhancedTranscriptDeltaEvent, RealtimeEnhancedTranscriptCommitEvent,
        RealtimeEnhancedSessionReadyEvent, RealtimeEnhancedTranslationDeltaEvent,
        RealtimeEnhancedAudioDeltaEvent, RealtimeEnhancedErrorEvent,
    )
    incoming = Annotated[Union[
        RealtimeEnhancedStartEvent, RealtimeEnhancedResetEvent,
        RealtimeEnhancedTranscriptDeltaEvent, RealtimeEnhancedTranscriptCommitEvent,
    ], Field(discriminator="type")]
    outgoing = Annotated[Union[
        RealtimeEnhancedSessionReadyEvent, RealtimeEnhancedTranslationDeltaEvent,
        RealtimeEnhancedAudioDeltaEvent, RealtimeEnhancedErrorEvent,
    ], Field(discriminator="type")]
    http = app.openapi()
    # Version changes alone do not alter the wire contract.
    http["info"]["version"] = "release-version"
    return {
        "openapi.json": http,
        "enhanced-websocket.json": {
            "incoming": TypeAdapter(incoming).json_schema(),
            "outgoing": TypeAdapter(outgoing).json_schema(),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Regenerate snapshots for explicit review")
    arguments = parser.parse_args()
    # Isolate import-time persistence/config from deployment data.
    with tempfile.TemporaryDirectory(prefix="waaxalma-contracts-") as directory:
        os.environ["APP_ENV"] = "test"
        os.environ["SESSION_CLEANUP_ENABLED"] = "false"
        for key, child in (("DATA_DIR", "data"), ("STATIC_DIR", "static"), ("UPLOAD_DIR", "uploads")):
            os.environ[key] = str(Path(directory) / child)
        for name, schema in schemas().items():
            path = ROOT / "docs/contracts" / name
            if arguments.write:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(schema, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            else:
                if not path.exists() or json.loads(path.read_text(encoding="utf-8")) != schema:
                    raise SystemExit(f"Contract changed: {name}. Review changes before regenerating snapshots with --write.")
    print("HTTP and WebSocket schema snapshots: OK")


if __name__ == "__main__":
    main()
