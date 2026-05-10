//! Complex-script font shaping for new text written by the editor.
//!
//! Most PDFs in the wild already contain pre-shaped glyph runs in their
//! content streams, so reading text rarely needs shaping. We DO need
//! shaping when the editor adds new text in scripts where the cmap-based
//! one-codepoint-to-one-glyph assumption breaks (Arabic, Devanagari,
//! Khmer, complex Latin ligatures, vertical writing).
//!
//! This module wraps `rustybuzz`, the pure-Rust port of HarfBuzz. The
//! caller supplies the embedded font bytes and a UTF-8 string; we
//! return the GID + advance + offset stream that the writer can emit
//! as PDF content operators.

use rustybuzz::{Face, UnicodeBuffer};

#[derive(Debug, Clone, Copy)]
pub struct ShapedGlyph {
    pub gid: u32,
    pub cluster: u32,
    pub x_advance: i32,
    pub y_advance: i32,
    pub x_offset: i32,
    pub y_offset: i32,
}

/// Shape `text` using the supplied font bytes. Returns one entry per
/// output glyph (which may be more or fewer than the number of input
/// characters).
///
/// The resulting `gid` values are font glyph IDs and can be written
/// directly into a hex string under an `Identity-H` Type0 font.
pub fn shape(font_bytes: &[u8], face_index: u32, text: &str) -> Option<Vec<ShapedGlyph>> {
    let face = Face::from_slice(font_bytes, face_index)?;
    let mut buffer = UnicodeBuffer::new();
    buffer.push_str(text);
    buffer.guess_segment_properties();
    let glyph_buffer = rustybuzz::shape(&face, &[], buffer);
    let positions = glyph_buffer.glyph_positions();
    let infos = glyph_buffer.glyph_infos();
    Some(
        infos
            .iter()
            .zip(positions.iter())
            .map(|(info, pos)| ShapedGlyph {
                gid: info.glyph_id,
                cluster: info.cluster,
                x_advance: pos.x_advance,
                y_advance: pos.y_advance,
                x_offset: pos.x_offset,
                y_offset: pos.y_offset,
            })
            .collect(),
    )
}
