"""
progress_manager.py — 전체 과정 기록용 progress.json 저장/로드
work/progress/{파일명}.json 에 처리 상태를 기록한다. 재개 목적 아님 (모니터링 전용).
"""
import json
import os
from datetime import datetime, timezone
from typing import Optional


def _progress_path(work_dir: str, filename: str) -> str:
    return os.path.join(work_dir, "progress", f"{filename}.json")


def init_progress(work_dir: str, filename: str, total_slides: int) -> dict:
    """progress.json 신규 생성 후 반환."""
    data = {
        "filename": filename,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "total_slides": total_slides,
        "steps": {
            "extract": "pending",
            "font_analysis": "pending",
            "translation": "pending",
            "dict_update": "pending",
        },
        "slides_translated": [],
        "slides_total": total_slides,
    }
    _save(work_dir, filename, data)
    return data


def load_progress(work_dir: str, filename: str) -> Optional[dict]:
    path = _progress_path(work_dir, filename)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def update_step(work_dir: str, filename: str, step: str, status: str) -> None:
    """steps 키 내 특정 step 상태 업데이트."""
    data = load_progress(work_dir, filename) or {}
    data.setdefault("steps", {})[step] = status
    _save(work_dir, filename, data)


def add_translated_slide(work_dir: str, filename: str, slide_num: int) -> None:
    data = load_progress(work_dir, filename) or {}
    translated = data.setdefault("slides_translated", [])
    if slide_num not in translated:
        translated.append(slide_num)
    _save(work_dir, filename, data)


def mark_completed(work_dir: str, filename: str) -> None:
    data = load_progress(work_dir, filename) or {}
    data["completed_at"] = datetime.now(timezone.utc).isoformat()
    _save(work_dir, filename, data)


def _save(work_dir: str, filename: str, data: dict) -> None:
    path = _progress_path(work_dir, filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
