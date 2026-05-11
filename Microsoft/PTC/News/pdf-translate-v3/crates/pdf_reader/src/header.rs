use pdf_core::{PdfError, PdfResult};

/// Parsed PDF header. We tolerate up to 1024 bytes of preamble before
/// the `%PDF-` signature in line with the design's recovery policy.
#[derive(Debug, Clone)]
pub struct PdfHeader {
    pub version: String,
    pub header_offset: usize,
}

const SCAN_WINDOW: usize = 1024;

pub fn find_header(data: &[u8]) -> PdfResult<PdfHeader> {
    let limit = data.len().min(SCAN_WINDOW);
    let signature = b"%PDF-";
    let pos = data[..limit]
        .windows(signature.len())
        .position(|w| w == signature)
        .ok_or(PdfError::HeaderNotFound)?;
    let after = &data[pos + signature.len()..];
    let version_end = after
        .iter()
        .position(|&b| b == b'\r' || b == b'\n' || b == b' ' || b == b'%')
        .unwrap_or(after.len())
        .min(8);
    let version_bytes = &after[..version_end];
    let version = std::str::from_utf8(version_bytes)
        .map_err(|_| PdfError::HeaderNotFound)?
        .trim()
        .to_string();
    if version.is_empty() {
        return Err(PdfError::HeaderNotFound);
    }
    Ok(PdfHeader {
        version,
        header_offset: pos,
    })
}
