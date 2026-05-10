//! Locate the trailing `startxref` byte offset.
//!
//! PDF files end with a small block:
//!
//! ```text
//! ...
//! startxref
//! 12345
//! %%EOF
//! ```
//!
//! Per `build/03-pdf-reader/DESIGN.md`, we scan from the end backward,
//! prefer the *last* `%%EOF`, and fall back to a wider window if needed.

use pdf_core::{PdfError, PdfResult};

const SCAN_TAIL: usize = 4096;

pub fn find_startxref(data: &[u8]) -> PdfResult<usize> {
    let len = data.len();
    let start = len.saturating_sub(SCAN_TAIL);
    let tail = &data[start..];
    let needle = b"startxref";
    // Find the *last* occurrence of "startxref" in the tail window.
    let mut last_pos: Option<usize> = None;
    for (i, w) in tail.windows(needle.len()).enumerate() {
        if w == needle {
            last_pos = Some(i);
        }
    }
    let pos = last_pos.ok_or(PdfError::StartXrefNotFound)?;
    let after = &tail[pos + needle.len()..];

    // Skip whitespace then read decimal digits.
    let mut i = 0;
    while i < after.len() && matches!(after[i], b' ' | b'\t' | b'\r' | b'\n' | 0x0C) {
        i += 1;
    }
    let mut number: usize = 0;
    let mut any = false;
    while i < after.len() && after[i].is_ascii_digit() {
        number = number
            .checked_mul(10)
            .and_then(|n| n.checked_add((after[i] - b'0') as usize))
            .ok_or(PdfError::StartXrefNotFound)?;
        i += 1;
        any = true;
    }
    if !any {
        return Err(PdfError::StartXrefNotFound);
    }
    Ok(number)
}
