"""Translation Memory (SQLite)."""
from __future__ import annotations

import csv
import hashlib
import sqlite3
from pathlib import Path

from ppt_translate.config import settings


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _connect() -> sqlite3.Connection:
    settings.tm_db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.tm_db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tm (
            src_hash TEXT PRIMARY KEY,
            src TEXT NOT NULL,
            tgt TEXT NOT NULL,
            model TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    return conn


def lookup(src: str) -> str | None:
    with _connect() as conn:
        row = conn.execute("SELECT tgt FROM tm WHERE src_hash = ?", (_hash(src),)).fetchone()
        return row[0] if row else None


def store(src: str, tgt: str, model: str = "") -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO tm (src_hash, src, tgt, model) VALUES (?, ?, ?, ?)",
            (_hash(src), src, tgt, model),
        )


def import_csv(csv_path: Path) -> int:
    n = 0
    with _connect() as conn, csv_path.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 2:
                continue
            src, tgt = row[0], row[1]
            conn.execute(
                "INSERT OR IGNORE INTO tm (src_hash, src, tgt) VALUES (?, ?, ?)",
                (_hash(src), src, tgt),
            )
            n += 1
    return n
