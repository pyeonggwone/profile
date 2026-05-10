use thiserror::Error;

/// Result alias used across the workspace.
pub type PdfResult<T> = Result<T, PdfError>;

/// Errors raised by the PDF core, reader, writer and filter chains.
///
/// Each variant maps to a stable diagnostic code that the web boundary
/// surfaces to clients (see `build/02-web-boundary/DESIGN.md`).
#[derive(Debug, Error)]
pub enum PdfError {
    #[error("PDF header signature not found")]
    HeaderNotFound,

    #[error("PDF EOF marker not found")]
    EofMarkerNotFound,

    #[error("startxref offset not found")]
    StartXrefNotFound,

    #[error("xref table is malformed: {0}")]
    XrefMalformed(String),

    #[error("trailer dictionary missing or malformed: {0}")]
    TrailerMalformed(String),

    #[error("indirect object {obj} {gen} could not be parsed: {reason}")]
    ObjectParse {
        obj: u32,
        gen: u16,
        reason: String,
    },

    #[error("dictionary parse error: {0}")]
    DictParse(String),

    #[error("array parse error: {0}")]
    ArrayParse(String),

    #[error("stream length mismatch: declared {declared}, scanned {scanned}")]
    StreamLengthMismatch { declared: usize, scanned: usize },

    #[error("filter `{0}` is not supported")]
    UnsupportedFilter(String),

    #[error("filter `{filter}` decode failed: {reason}")]
    FilterDecode { filter: String, reason: String },

    #[error("filter `{filter}` encode failed: {reason}")]
    FilterEncode { filter: String, reason: String },

    #[error("page tree traversal failed: {0}")]
    PageTree(String),

    #[error("encrypted PDFs are not yet supported for write operations")]
    EncryptedNotSupported,

    #[error("encrypted PDF requires a password")]
    PasswordRequired,

    #[error("encrypted PDF: wrong password")]
    WrongPassword,

    #[error("unexpected end of input at offset {0}")]
    UnexpectedEof(usize),

    #[error("invalid number literal: {0}")]
    InvalidNumber(String),

    #[error("invalid name literal: {0}")]
    InvalidName(String),

    #[error("invalid string literal: {0}")]
    InvalidString(String),

    #[error("write error: {0}")]
    Write(String),

    #[error("io error: {0}")]
    Io(String),

    #[error("internal invariant violated: {0}")]
    Invariant(String),
}

impl From<std::io::Error> for PdfError {
    fn from(value: std::io::Error) -> Self {
        PdfError::Io(value.to_string())
    }
}

/// Non-fatal warning emitted by the parser. The reader keeps going,
/// records a warning and exposes it on the parsed document.
#[derive(Debug, Clone)]
#[cfg_attr(feature = "serde", derive(serde::Serialize, serde::Deserialize))]
pub struct PdfWarning {
    pub code: String,
    pub detail: String,
    pub byte_offset: Option<usize>,
}

impl PdfWarning {
    pub fn new(code: impl Into<String>, detail: impl Into<String>) -> Self {
        Self {
            code: code.into(),
            detail: detail.into(),
            byte_offset: None,
        }
    }

    pub fn at(mut self, offset: usize) -> Self {
        self.byte_offset = Some(offset);
        self
    }
}
