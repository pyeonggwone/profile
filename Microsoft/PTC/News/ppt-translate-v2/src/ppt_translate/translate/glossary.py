"""용어집 (CSV: term,translation,protected)."""
from __future__ import annotations

import csv
from pathlib import Path

from ppt_translate.config import settings


def load() -> dict[str, dict]:
    """{ term: {translation, protected} } 반환. 파일 없으면 빈 dict."""
    path = settings.glossary_path
    if not path.exists():
        return {}
    out: dict[str, dict] = {}
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            term = row.get("term", "").strip()
            if not term:
                continue
            out[term] = {
                "translation": row.get("translation", "").strip(),
                "protected": row.get("protected", "").strip().lower() in ("1", "true", "yes"),
            }
    return out
