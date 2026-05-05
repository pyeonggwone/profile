use std::path::PathBuf;
use std::sync::{Arc, Mutex};

use serde::{Deserialize, Serialize};

pub const MAX_UPLOAD_BYTES: usize = 100 * 1024 * 1024;

#[derive(Clone)]
pub struct AppState {
    pub inner: Arc<AppInner>,
}

pub struct AppInner {
    pub workdir: PathBuf,
    /// Edits per session. Persistence is best-effort; loss only affects
    /// in-flight edits, never the original PDF.
    pub edits: Mutex<std::collections::HashMap<String, Vec<pdf_incremental::EditOperation>>>,
}

impl AppState {
    pub fn new(workdir: PathBuf) -> std::io::Result<Self> {
        std::fs::create_dir_all(&workdir)?;
        std::fs::create_dir_all(workdir.join("sessions"))?;
        Ok(Self {
            inner: Arc::new(AppInner {
                workdir,
                edits: Mutex::new(Default::default()),
            }),
        })
    }

    pub fn session_dir(&self, document_id: &str) -> PathBuf {
        self.inner.workdir.join("sessions").join(document_id)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DocumentMeta {
    pub document_id: String,
    pub original_filename: String,
    pub size_bytes: u64,
    pub uploaded_at: chrono::DateTime<chrono::Utc>,
    pub pdf_version: String,
    pub page_count: u32,
    pub encrypted: bool,
}
