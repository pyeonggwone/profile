//! FlateDecode adapter.
//!
//! Wraps `flate2` (which uses the source-open `miniz_oxide` pure-Rust
//! Deflate implementation by default). The PDF-side concerns — predictor
//! handling, `/DecodeParms`, length recovery — live in the parent module.
//!
//! Production builds may swap the backend for the system `zlib 1.3.1`
//! by enabling the `flate2/zlib-ng` or `flate2/zlib` feature without
//! changing the function signatures below.

use flate2::read::ZlibDecoder;
use flate2::write::ZlibEncoder;
use flate2::Compression;
use pdf_core::{PdfError, PdfResult};
use std::io::{Read, Write};

pub fn decode(input: &[u8]) -> PdfResult<Vec<u8>> {
    let mut decoder = ZlibDecoder::new(input);
    let mut out = Vec::with_capacity(input.len() * 2);
    decoder
        .read_to_end(&mut out)
        .map_err(|e| PdfError::FilterDecode {
            filter: "FlateDecode".into(),
            reason: e.to_string(),
        })?;
    Ok(out)
}

pub fn encode(input: &[u8]) -> PdfResult<Vec<u8>> {
    let mut encoder = ZlibEncoder::new(Vec::new(), Compression::default());
    encoder.write_all(input).map_err(|e| PdfError::FilterEncode {
        filter: "FlateDecode".into(),
        reason: e.to_string(),
    })?;
    encoder.finish().map_err(|e| PdfError::FilterEncode {
        filter: "FlateDecode".into(),
        reason: e.to_string(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip() {
        let input = b"BT /F1 12 Tf 100 700 Td (Hello) Tj ET";
        let encoded = encode(input).unwrap();
        let decoded = decode(&encoded).unwrap();
        assert_eq!(decoded, input);
    }
}
