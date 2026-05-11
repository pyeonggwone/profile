use anyhow::{Context, Result};
use chrono::Utc;
use rusqlite::{params, Connection};
use sha2::{Digest, Sha256};
use std::path::Path;

pub struct StateDb {
    conn: Connection,
}

impl StateDb {
    pub fn open(path: &Path) -> Result<Self> {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).with_context(|| format!("create {}", parent.display()))?;
        }
        let conn = Connection::open(path).with_context(|| format!("open {}", path.display()))?;
        conn.execute_batch(
            r#"
            PRAGMA journal_mode = WAL;
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
            CREATE TABLE IF NOT EXISTS translation_memory (
                src_hash TEXT PRIMARY KEY,
                source_text TEXT NOT NULL,
                translated_text TEXT NOT NULL,
                source_lang TEXT NOT NULL,
                target_lang TEXT NOT NULL,
                model TEXT,
                created_at TEXT NOT NULL
            );
            "#,
        )?;
        Ok(Self { conn })
    }

    pub fn upsert_job(&self, job_id: &str, source_path: &str, sha256: &str, status: &str) -> Result<()> {
        let now = Utc::now().to_rfc3339();
        self.conn.execute(
            "INSERT INTO jobs(job_id, source_path, source_sha256, status, created_at, updated_at)
             VALUES (?1, ?2, ?3, ?4, ?5, ?5)
             ON CONFLICT(job_id) DO UPDATE SET status = excluded.status, updated_at = excluded.updated_at",
            params![job_id, source_path, sha256, status, now],
        )?;
        Ok(())
    }

    pub fn set_step(&self, job_id: &str, step: &str, status: &str, message: Option<&str>) -> Result<()> {
        let now = Utc::now().to_rfc3339();
        self.conn.execute(
            "INSERT INTO pipeline_steps(job_id, step, status, message, updated_at)
             VALUES (?1, ?2, ?3, ?4, ?5)
             ON CONFLICT(job_id, step) DO UPDATE SET status = excluded.status, message = excluded.message, updated_at = excluded.updated_at",
            params![job_id, step, status, message, now],
        )?;
        Ok(())
    }

    pub fn add_artifact(&self, job_id: &str, kind: &str, path: &str) -> Result<()> {
        self.conn.execute(
            "INSERT INTO artifacts(job_id, kind, path, created_at) VALUES (?1, ?2, ?3, ?4)",
            params![job_id, kind, path, Utc::now().to_rfc3339()],
        )?;
        Ok(())
    }

    pub fn tm_get(&self, source_text: &str, source_lang: &str, target_lang: &str) -> Result<Option<String>> {
        let hash = tm_hash(source_text, source_lang, target_lang);
        let mut stmt = self.conn.prepare("SELECT translated_text FROM translation_memory WHERE src_hash = ?1")?;
        let mut rows = stmt.query(params![hash])?;
        Ok(rows.next()?.map(|row| row.get(0)).transpose()?)
    }

    pub fn tm_put(
        &self,
        source_text: &str,
        translated_text: &str,
        source_lang: &str,
        target_lang: &str,
        model: &str,
    ) -> Result<()> {
        let hash = tm_hash(source_text, source_lang, target_lang);
        self.conn.execute(
            "INSERT OR REPLACE INTO translation_memory(src_hash, source_text, translated_text, source_lang, target_lang, model, created_at)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
            params![hash, source_text, translated_text, source_lang, target_lang, model, Utc::now().to_rfc3339()],
        )?;
        Ok(())
    }
}

fn tm_hash(source_text: &str, source_lang: &str, target_lang: &str) -> String {
    hex::encode(Sha256::digest(format!("{source_lang}\n{target_lang}\n{source_text}").as_bytes()))
}
