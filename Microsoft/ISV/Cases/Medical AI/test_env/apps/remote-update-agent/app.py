import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


UPDATE_SOURCE_URL = os.getenv("UPDATE_SOURCE_URL", "https://example.invalid/medicalai/releases/current.json")
POLL_INTERVAL_SECONDS = int(os.getenv("UPDATE_POLL_INTERVAL_SECONDS", "30"))
APPLY_ENABLED = os.getenv("UPDATE_APPLY_ENABLED", "false").lower() == "true"
VOLUME_ROOT = Path(os.getenv("CONTAINER_VOLUME_ROOT", "/var/medicalai/data")) / "remote-update-agent"
EVENT_LOG = VOLUME_ROOT / "update-poll-events.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_event(record: dict) -> None:
    VOLUME_ROOT.mkdir(parents=True, exist_ok=True)
    with EVENT_LOG.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def poll_once() -> dict:
    record = {
        "checked_at": utc_now(),
        "update_source_url": UPDATE_SOURCE_URL,
        "apply_enabled": APPLY_ENABLED,
    }
    try:
        response = requests.get(UPDATE_SOURCE_URL, timeout=10)
        record["status_code"] = response.status_code
        record["success"] = response.ok
        if response.ok:
            record["release_metadata"] = response.json()
            record["action"] = "dry-run" if not APPLY_ENABLED else "apply-not-implemented-in-test-env"
        else:
            record["response_text"] = response.text[:500]
    except Exception as error:
        record["success"] = False
        record["error"] = str(error)
    append_event(record)
    return record


def main() -> None:
    print("remote-update-agent started", flush=True)
    while True:
        result = poll_once()
        print(json.dumps(result, ensure_ascii=False), flush=True)
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()