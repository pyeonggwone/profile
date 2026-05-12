from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StateDb:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                source_path TEXT NOT NULL,
                source_sha256 TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS pipeline_steps (
                job_id TEXT NOT NULL,
                step TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(job_id, step)
            );
            CREATE TABLE IF NOT EXISTS artifacts (
                job_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                path TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS validation_events (
                job_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                code TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                path TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def upsert_job(self, job_id: str, source_path: str, source_sha256: str, status: str) -> None:
        now = utc_now()
        self.conn.execute(
            """
            INSERT INTO jobs(job_id, source_path, source_sha256, status, created_at, updated_at)
            VALUES(?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at
            """,
            (job_id, source_path, source_sha256, status, now, now),
        )
        self.conn.commit()

    def set_step(self, job_id: str, step: str, status: str, message: str | None = None) -> None:
        now = utc_now()
        self.conn.execute(
            """
            INSERT INTO pipeline_steps(job_id, step, status, message, updated_at)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(job_id, step) DO UPDATE SET status=excluded.status, message=excluded.message, updated_at=excluded.updated_at
            """,
            (job_id, step, status, message, now),
        )
        self.conn.commit()

    def add_artifact(self, job_id: str, kind: str, path: Path) -> None:
        self.conn.execute(
            "INSERT INTO artifacts(job_id, kind, path, created_at) VALUES(?, ?, ?, ?)",
            (job_id, kind, str(path), utc_now()),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()