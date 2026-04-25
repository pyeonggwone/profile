import copy
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from fastapi import FastAPI


VOLUME_ROOT = Path(os.getenv("CONTAINER_VOLUME_ROOT", "/var/medicalai/data")) / "pii-processor"
EVENT_LOG = VOLUME_ROOT / "processed-events.jsonl"
FORWARD_ENABLED = os.getenv("PII_PROCESSOR_FORWARD_ENABLED", "false").lower() == "true"
FORWARD_URL = os.getenv("PII_PROCESSOR_FORWARD_URL", "")

app = FastAPI(title="Medical AI PII Processor", version="0.1.0")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def mask_text(value: str) -> str:
    value = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", "***@***", value)
    value = re.sub(r"\+?\d[\d\- ]{7,}\d", "***-****-****", value)
    value = re.sub(r"PT-\d{4}-\d{4}", "PT-****-****", value)
    return value


def mask_patient(patient: dict[str, Any]) -> dict[str, Any]:
    masked = copy.deepcopy(patient)
    if "name" in masked:
        masked["name"] = "***"
    if "email" in masked:
        masked["email"] = mask_text(str(masked["email"]))
    if "phone" in masked:
        masked["phone"] = mask_text(str(masked["phone"]))
    if "patient_id" in masked:
        masked["patient_id"] = mask_text(str(masked["patient_id"]))
    return masked


def mask_payload(payload: dict[str, Any]) -> dict[str, Any]:
    masked = copy.deepcopy(payload)
    if isinstance(masked.get("patient"), dict):
        masked["patient"] = mask_patient(masked["patient"])
    return masked


def append_event(record: dict[str, Any]) -> None:
    VOLUME_ROOT.mkdir(parents=True, exist_ok=True)
    with EVENT_LOG.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def forward_result(record: dict[str, Any]) -> dict[str, Any]:
    if not FORWARD_ENABLED:
        return {"enabled": False}
    if not FORWARD_URL:
        return {"enabled": True, "success": False, "error": "PII_PROCESSOR_FORWARD_URL is empty"}
    try:
        response = requests.post(FORWARD_URL, json=record["masked"], timeout=10)
        return {"enabled": True, "success": response.ok, "status_code": response.status_code}
    except Exception as error:
        return {"enabled": True, "success": False, "error": str(error)}


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "pii-processor", "time": utc_now()}


@app.post("/process")
def process(payload: dict[str, Any]) -> dict[str, Any]:
    masked = mask_payload(payload)
    record = {
        "processed_at": utc_now(),
        "original": payload,
        "masked": masked,
    }
    record["forward"] = forward_result(record)
    append_event(record)
    return {"status": "processed", "masked": masked, "forward": record["forward"]}