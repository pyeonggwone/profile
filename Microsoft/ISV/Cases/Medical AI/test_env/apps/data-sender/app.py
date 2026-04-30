import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from fastapi import FastAPI


PII_PROCESSOR_URL = os.getenv("PII_PROCESSOR_URL", "http://pii-processor:8080/process")
INTERVAL_SECONDS = int(os.getenv("DATA_SENDER_INTERVAL_SECONDS", "10"))
VOLUME_ROOT = Path(os.getenv("CONTAINER_VOLUME_ROOT", "/var/medicalai/data")) / "data-sender"
EVENT_LOG = VOLUME_ROOT / "sent-events.jsonl"

app = FastAPI(title="Medical AI Data Sender", version="0.1.0")
stop_event = threading.Event()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_sample_payload() -> dict:
    event_id = str(uuid.uuid4())
    return {
        "event_id": event_id,
        "event_time": utc_now(),
        "source_system": "hospital-ecg-gateway-01",
        "patient": {
            "patient_id": "PT-2026-0001",
            "name": "Kim Minjun",
            "email": "minjun.kim@example-hospital.local",
            "phone": "+82-10-1234-5678",
        },
        "encounter": {
            "department": "cardiology",
            "device_id": "ECG-ROOM-03",
        },
        "ecg_summary": {
            "heart_rate": 78,
            "rhythm": "normal sinus rhythm",
            "sample_window_seconds": 10,
        },
    }


def append_event(record: dict) -> None:
    VOLUME_ROOT.mkdir(parents=True, exist_ok=True)
    with EVENT_LOG.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def send_payload() -> dict:
    payload = build_sample_payload()
    result = {
        "sent_at": utc_now(),
        "target_url": PII_PROCESSOR_URL,
        "payload": payload,
        "success": False,
    }
    try:
        response = requests.post(PII_PROCESSOR_URL, json=payload, timeout=10)
        result["status_code"] = response.status_code
        result["response"] = response.json() if response.content else {}
        result["success"] = response.ok
    except Exception as error:
        result["error"] = str(error)

    append_event(result)
    return result


def sender_loop() -> None:
    while not stop_event.is_set():
        send_payload()
        stop_event.wait(INTERVAL_SECONDS)


@app.on_event("startup")
def start_sender() -> None:
    thread = threading.Thread(target=sender_loop, daemon=True)
    thread.start()


@app.on_event("shutdown")
def stop_sender() -> None:
    stop_event.set()


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "service": "data-sender", "time": utc_now()}


@app.post("/send-once")
def send_once() -> dict:
    return send_payload()