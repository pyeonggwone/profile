//! JPXDecode (JPEG2000) adapter.
//!
//! JPEG2000 is ISO/IEC 15444. Per `build/00-requirements/DESIGN.md`,
//! JPEG2000 decoding is delegated to OpenJPEG. The adapter is feature-
//! gated so the workspace builds without a system-installed OpenJPEG.
//!
//! When the `jpx-openjpeg` feature is enabled, link `openjpeg-sys` here
//! and call `opj_decode` to produce raw pixels. The PDF-side concerns
//! (`/ColorSpace`, raw stream preservation) are handled by `pdf_writer`
//! and the chain in `lib.rs`.

use pdf_core::{PdfError, PdfResult};

#[cfg(feature = "jpx-openjpeg")]
pub fn decode(_input: &[u8]) -> PdfResult<Vec<u8>> {
    // Real implementation hook: openjpeg-sys::opj_create_decompress,
    // opj_setup_decoder, opj_read_header, opj_decode, opj_end_decompress.
    Err(PdfError::FilterDecode {
        filter: "JPXDecode".into(),
        reason: "openjpeg-sys integration not yet wired".into(),
    })
}

#[cfg(not(feature = "jpx-openjpeg"))]
pub fn decode(_input: &[u8]) -> PdfResult<Vec<u8>> {
    Err(PdfError::FilterDecode {
        filter: "JPXDecode".into(),
        reason: "enable `jpx-openjpeg` feature for JPEG2000 decode".into(),
    })
}
