//! JBIG2Decode adapter.
//!
//! JBIG2 is ISO/IEC 14492. Per `build/00-requirements/DESIGN.md`, JBIG2
//! decoding is delegated to `jbig2dec` via `jbig2dec-sys`. The adapter
//! is feature-gated.
//!
//! Security note: JBIG2 decoders have a long history of exploitable
//! bugs (CVE-2021-30860 et al.). When enabling this feature, run the
//! decoder in a process sandbox if possible. The design discusses this
//! in `build/04-stream-filters/DESIGN.md`.

use pdf_core::{PdfDict, PdfError, PdfResult};

#[cfg(feature = "jbig2-jbig2dec")]
pub fn decode(_input: &[u8], _params: Option<&PdfDict>) -> PdfResult<Vec<u8>> {
    // Real implementation hook: jbig2dec-sys context, decode segments,
    // honour /JBIG2Globals stream.
    Err(PdfError::FilterDecode {
        filter: "JBIG2Decode".into(),
        reason: "jbig2dec-sys integration not yet wired".into(),
    })
}

#[cfg(not(feature = "jbig2-jbig2dec"))]
pub fn decode(_input: &[u8], _params: Option<&PdfDict>) -> PdfResult<Vec<u8>> {
    Err(PdfError::FilterDecode {
        filter: "JBIG2Decode".into(),
        reason: "enable `jbig2-jbig2dec` feature for JBIG2 decode".into(),
    })
}
