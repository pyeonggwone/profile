from __future__ import annotations

import csv
import re
from pathlib import Path

from .models import JobTerm, ReadableTextState


PROPER_NOUN = re.compile(r"\b[A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*)*\b")


def load_glossary(path: Path) -> list[JobTerm]:
    if not path.exists():
        return []
    terms: list[JobTerm] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            term = (row.get("term") or "").strip()
            if not term:
                continue
            translation = (row.get("translation") or "").strip() or None
            mode = (row.get("mode") or "fixed").strip() or "fixed"
            terms.append(JobTerm(term, translation, mode))
    return terms


def extract_candidates(readable: ReadableTextState) -> list[str]:
    candidates: set[str] = set()
    for item in readable.items:
        for match in PROPER_NOUN.finditer(item.source):
            value = match.group(0).strip()
            if len(value) > 1:
                candidates.add(value)
    return sorted(candidates)