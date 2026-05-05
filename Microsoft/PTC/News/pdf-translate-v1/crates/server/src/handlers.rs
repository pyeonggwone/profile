use std::path::PathBuf;

use axum::body::Body;
use axum::extract::{Multipart, Path, State};
use axum::http::{header, HeaderMap, StatusCode};
use axum::response::{IntoResponse, Response};
use axum::Json;
use serde::Deserialize;
use sha2::{Digest, Sha256};

use crate::errors::{from_pdf_error, ApiError};
use crate::state::{AppState, DocumentMeta};

pub async fn health() -> &'static str {
    "ok"
}

pub async fn upload_document(
    State(state): State<AppState>,
    mut multipart: Multipart,
) -> Result<Response, Response> {
    let mut file_bytes: Option<Vec<u8>> = None;
    let mut original_filename = String::from("upload.pdf");

    while let Some(field) = multipart
        .next_field()
        .await
        .map_err(|e| api_err("MULTIPART_ERROR", e.to_string(), StatusCode::BAD_REQUEST))?
    {
        if field.name() == Some("file") {
            if let Some(name) = field.file_name() {
                original_filename = sanitize_filename(name);
            }
            let bytes = field
                .bytes()
                .await
                .map_err(|e| api_err("MULTIPART_ERROR", e.to_string(), StatusCode::BAD_REQUEST))?;
            file_bytes = Some(bytes.to_vec());
        }
    }

    let bytes = file_bytes.ok_or_else(|| {
        api_err(
            "FILE_FIELD_MISSING",
            "multipart 'file' field required",
            StatusCode::BAD_REQUEST,
        )
    })?;

    if !bytes.windows(5).any(|w| w == b"%PDF-") {
        return Err(api_err(
            "NOT_A_PDF",
            "PDF header signature missing",
            StatusCode::BAD_REQUEST,
        ));
    }

    // Parse on the blocking pool: PDF parsing is CPU-bound.
    let parsed_bytes = bytes.clone();
    let parsed = tokio::task::spawn_blocking(move || {
        pdf_reader::ParsedPdf::from_bytes(parsed_bytes)
    })
    .await
    .map_err(|e| api_err("JOIN_ERROR", e.to_string(), StatusCode::INTERNAL_SERVER_ERROR))?
    .map_err(|e| {
        let (status, body) = from_pdf_error(e);
        body.into_response_with(status)
    })?;

    let document_id = uuid::Uuid::new_v4().to_string();
    let session_dir = state.session_dir(&document_id);
    std::fs::create_dir_all(&session_dir)
        .map_err(|e| api_err("IO_ERROR", e.to_string(), StatusCode::INTERNAL_SERVER_ERROR))?;
    let original_path = session_dir.join("original.pdf");
    std::fs::write(&original_path, &bytes)
        .map_err(|e| api_err("IO_ERROR", e.to_string(), StatusCode::INTERNAL_SERVER_ERROR))?;

    let summary = pdf_analysis::summary::summarize(&parsed)
        .map_err(|e| {
            let (status, body) = from_pdf_error(e);
            body.into_response_with(status)
        })?;

    let meta = DocumentMeta {
        document_id: document_id.clone(),
        original_filename,
        size_bytes: bytes.len() as u64,
        uploaded_at: chrono::Utc::now(),
        pdf_version: summary.pdf_version.clone(),
        page_count: summary.page_count,
        encrypted: summary.encrypted,
    };
    let meta_path = session_dir.join("document.json");
    std::fs::write(
        &meta_path,
        serde_json::to_vec_pretty(&meta).unwrap_or_default(),
    )
    .map_err(|e| api_err("IO_ERROR", e.to_string(), StatusCode::INTERNAL_SERVER_ERROR))?;

    let _hash = Sha256::digest(&bytes); // checksums recorded separately if needed.

    Ok((
        StatusCode::CREATED,
        Json(serde_json::json!({
            "document": meta,
            "summary": summary,
        })),
    )
        .into_response())
}

pub async fn get_document(
    State(state): State<AppState>,
    Path(document_id): Path<String>,
) -> Result<Response, Response> {
    let session_dir = state.session_dir(&document_id);
    if !session_dir.exists() {
        return Err(api_err("NOT_FOUND", "document not found", StatusCode::NOT_FOUND));
    }
    let meta = load_meta(&session_dir).map_err(|e| {
        api_err("IO_ERROR", e.to_string(), StatusCode::INTERNAL_SERVER_ERROR)
    })?;
    let pdf_bytes = std::fs::read(session_dir.join("original.pdf"))
        .map_err(|e| api_err("IO_ERROR", e.to_string(), StatusCode::INTERNAL_SERVER_ERROR))?;
    let parsed = parse_blocking(pdf_bytes).await?;
    let summary = pdf_analysis::summary::summarize(&parsed).map_err(|e| {
        let (s, body) = from_pdf_error(e);
        body.into_response_with(s)
    })?;
    Ok(Json(serde_json::json!({
        "document": meta,
        "summary": summary,
    }))
    .into_response())
}

pub async fn get_page_render_plan(
    State(state): State<AppState>,
    Path((document_id, page_number)): Path<(String, u32)>,
) -> Result<Response, Response> {
    let session_dir = state.session_dir(&document_id);
    let pdf_bytes = std::fs::read(session_dir.join("original.pdf"))
        .map_err(|_| api_err("NOT_FOUND", "document not found", StatusCode::NOT_FOUND))?;
    let parsed = parse_blocking(pdf_bytes).await?;
    let plans = pdf_render_plan::build_render_plan(&parsed).map_err(|e| {
        let (s, body) = from_pdf_error(e);
        body.into_response_with(s)
    })?;
    let plan = plans
        .into_iter()
        .find(|p| p.page == page_number)
        .ok_or_else(|| api_err("PAGE_NOT_FOUND", "page out of range", StatusCode::NOT_FOUND))?;
    Ok(Json(plan).into_response())
}

#[derive(Debug, Deserialize)]
pub struct EditRequest {
    pub operations: Vec<pdf_incremental::EditOperation>,
}

pub async fn post_edit(
    State(state): State<AppState>,
    Path(document_id): Path<String>,
    Json(req): Json<EditRequest>,
) -> Result<Response, Response> {
    {
        let mut store = state.inner.edits.lock().unwrap();
        store
            .entry(document_id.clone())
            .or_default()
            .extend(req.operations.iter().cloned());
    }
    // Also persist for recovery.
    let session_dir = state.session_dir(&document_id);
    if !session_dir.exists() {
        return Err(api_err("NOT_FOUND", "document not found", StatusCode::NOT_FOUND));
    }
    let path = session_dir.join("edits.jsonl");
    use std::io::Write;
    let mut f = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
        .map_err(|e| api_err("IO_ERROR", e.to_string(), StatusCode::INTERNAL_SERVER_ERROR))?;
    for op in &req.operations {
        let line = serde_json::to_string(op).unwrap();
        let _ = writeln!(f, "{line}");
    }
    Ok(Json(serde_json::json!({ "accepted": req.operations.len() })).into_response())
}

pub async fn download_document(
    State(state): State<AppState>,
    Path(document_id): Path<String>,
) -> Result<Response, Response> {
    let session_dir = state.session_dir(&document_id);
    let pdf_bytes = std::fs::read(session_dir.join("original.pdf"))
        .map_err(|_| api_err("NOT_FOUND", "document not found", StatusCode::NOT_FOUND))?;
    let edits = {
        let store = state.inner.edits.lock().unwrap();
        store.get(&document_id).cloned().unwrap_or_default()
    };

    let final_bytes: Vec<u8> = if edits.is_empty() {
        pdf_bytes
    } else {
        // Run incremental update on the blocking pool.
        let raw = pdf_bytes.clone();
        let edits_for_blocking = edits.clone();
        tokio::task::spawn_blocking(move || -> Result<Vec<u8>, pdf_core::PdfError> {
            let parsed = pdf_reader::ParsedPdf::from_bytes(raw)?;
            let writer = pdf_incremental::IncrementalWriter::new(&parsed);
            let update = writer.build(&edits_for_blocking)?;
            Ok(update.bytes)
        })
        .await
        .map_err(|e| api_err("JOIN_ERROR", e.to_string(), StatusCode::INTERNAL_SERVER_ERROR))?
        .map_err(|e| {
            let (s, body) = from_pdf_error(e);
            body.into_response_with(s)
        })?
    };

    let mut headers = HeaderMap::new();
    headers.insert(header::CONTENT_TYPE, "application/pdf".parse().unwrap());
    headers.insert(
        header::CONTENT_DISPOSITION,
        format!("attachment; filename=\"document-{document_id}.pdf\"")
            .parse()
            .unwrap(),
    );
    Ok((StatusCode::OK, headers, Body::from(final_bytes)).into_response())
}

pub async fn delete_document(
    State(state): State<AppState>,
    Path(document_id): Path<String>,
) -> Result<Response, Response> {
    let session_dir = state.session_dir(&document_id);
    if session_dir.exists() {
        let _ = std::fs::remove_dir_all(&session_dir);
    }
    state.inner.edits.lock().unwrap().remove(&document_id);
    Ok(StatusCode::NO_CONTENT.into_response())
}

fn sanitize_filename(name: &str) -> String {
    name.chars()
        .filter(|c| c.is_alphanumeric() || matches!(c, '.' | '-' | '_' | ' '))
        .take(120)
        .collect()
}

fn load_meta(session_dir: &PathBuf) -> std::io::Result<DocumentMeta> {
    let bytes = std::fs::read(session_dir.join("document.json"))?;
    serde_json::from_slice(&bytes)
        .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))
}

async fn parse_blocking(bytes: Vec<u8>) -> Result<pdf_reader::ParsedPdf, Response> {
    tokio::task::spawn_blocking(move || pdf_reader::ParsedPdf::from_bytes(bytes))
        .await
        .map_err(|e| api_err("JOIN_ERROR", e.to_string(), StatusCode::INTERNAL_SERVER_ERROR))?
        .map_err(|e| {
            let (s, body) = from_pdf_error(e);
            body.into_response_with(s)
        })
}

fn api_err(code: &str, msg: impl Into<String>, status: StatusCode) -> Response {
    ApiError::new(code, msg).into_response_with(status)
}
