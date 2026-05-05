use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use serde::Serialize;

#[derive(Debug, Serialize)]
pub struct ApiError {
    pub code: String,
    pub message: String,
    pub recoverable: bool,
}

impl ApiError {
    pub fn new(code: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            code: code.into(),
            message: message.into(),
            recoverable: false,
        }
    }

    pub fn into_response_with(self, status: StatusCode) -> Response {
        (status, axum::Json(self)).into_response()
    }
}

pub fn from_pdf_error(err: pdf_core::PdfError) -> (StatusCode, ApiError) {
    use pdf_core::PdfError as E;
    let (status, code, recoverable) = match &err {
        E::HeaderNotFound => (StatusCode::BAD_REQUEST, "PDF_HEADER_NOT_FOUND", false),
        E::EofMarkerNotFound => (StatusCode::BAD_REQUEST, "PDF_EOF_NOT_FOUND", false),
        E::StartXrefNotFound => (StatusCode::BAD_REQUEST, "PDF_XREF_NOT_FOUND", false),
        E::XrefMalformed(_) => (StatusCode::UNPROCESSABLE_ENTITY, "PDF_XREF_MALFORMED", false),
        E::TrailerMalformed(_) => (StatusCode::UNPROCESSABLE_ENTITY, "PDF_TRAILER_MALFORMED", false),
        E::EncryptedNotSupported => (StatusCode::UNPROCESSABLE_ENTITY, "PDF_ENCRYPTED_WRITE", false),
        E::PasswordRequired => (StatusCode::UNAUTHORIZED, "PDF_PASSWORD_REQUIRED", true),
        E::WrongPassword => (StatusCode::UNAUTHORIZED, "PDF_WRONG_PASSWORD", true),
        E::PageTree(_) => (StatusCode::UNPROCESSABLE_ENTITY, "PDF_PAGE_TREE_BROKEN", false),
        E::UnsupportedFilter(_) => (StatusCode::UNPROCESSABLE_ENTITY, "PDF_FILTER_UNSUPPORTED", false),
        E::Io(_) => (StatusCode::INTERNAL_SERVER_ERROR, "IO_ERROR", true),
        _ => (StatusCode::INTERNAL_SERVER_ERROR, "PDF_ERROR", false),
    };
    (
        status,
        ApiError {
            code: code.into(),
            message: err.to_string(),
            recoverable,
        },
    )
}
