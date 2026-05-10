//! CCITTFaxDecode (PDF spec 7.4.9, ITU T.4 / T.6).
//!
//! Delegated to the `fax` crate (pure-Rust, MIT, used by `pdf-rs`).
//! This module interprets the PDF-side `/DecodeParms` and converts the
//! position-list line callback exposed by the codec into an 8-bits-per-
//! pixel byte buffer suitable for image preview generation.

use fax::{decoder, Color};
use pdf_core::{DictExt, PdfDict, PdfResult};

#[derive(Debug, Clone, Copy)]
struct Params {
    k: i64,
    columns: u32,
    rows: u32,
    black_is_1: bool,
    encoded_byte_align: bool,
    end_of_line: bool,
    end_of_block: bool,
}

fn read_params(p: Option<&PdfDict>) -> Params {
    let read_i = |k: &[u8], default: i64| -> i64 {
        p.and_then(|d| d.get_integer(k)).unwrap_or(default)
    };
    let read_b = |k: &[u8], default: bool| -> bool {
        match p.and_then(|d| d.get(k)) {
            Some(pdf_core::PdfObject::Boolean(b)) => *b,
            _ => default,
        }
    };
    Params {
        k: read_i(b"K", 0),
        columns: read_i(b"Columns", 1728) as u32,
        rows: read_i(b"Rows", 0) as u32,
        black_is_1: read_b(b"BlackIs1", false),
        encoded_byte_align: read_b(b"EncodedByteAlign", false),
        end_of_line: read_b(b"EndOfLine", false),
        end_of_block: read_b(b"EndOfBlock", true),
    }
}

/// Decode a CCITT Fax stream to one byte per pixel (0x00 = white,
/// 0xFF = black, polarity adjusted per `/BlackIs1`).
pub fn decode(input: &[u8], params: Option<&PdfDict>) -> PdfResult<Vec<u8>> {
    let p = read_params(params);
    let _ = (p.encoded_byte_align, p.end_of_line, p.end_of_block);
    let initial = (p.columns as usize) * (p.rows as usize).max(1);
    let mut out = Vec::with_capacity(initial);
    let height = if p.rows == 0 { None } else { Some(p.rows as u16) };

    let mut cb = |line: &[u16]| {
        for color in decoder::pels(line, p.columns as u16) {
            let pixel = match (color, p.black_is_1) {
                (Color::Black, false) => 0xFF,
                (Color::White, false) => 0x00,
                (Color::Black, true) => 0x00,
                (Color::White, true) => 0xFF,
            };
            out.push(pixel);
        }
    };

    if p.k < 0 {
        // Group 4
        decoder::decode_g4(input.iter().copied(), p.columns as u16, height, &mut cb);
    } else {
        // Group 3 (1D and 2D both flow through this entry point)
        decoder::decode_g3(input.iter().copied(), &mut cb);
    }

    Ok(out)
}
