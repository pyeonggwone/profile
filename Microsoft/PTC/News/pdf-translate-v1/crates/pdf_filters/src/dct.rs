//! DCTDecode (JPEG) adapter.
//!
//! PDF stores JPEG-compressed image content as the *raw JPEG file*
//! inside a stream with `/Filter /DCTDecode`. There is no extra wrapping;
//! decompressing the stream means handing those bytes to a JPEG decoder.
//!
//! This module exposes:
//!
//! - `probe`: read JPEG SOF metadata (dimensions, bits, components)
//!   without fully decoding the pixels. Backed by `jpeg-decoder`
//!   (pure-Rust). Used by `pdf_analysis` for image listings.
//! - `encode_baseline`: write a baseline JPEG from raw RGB/grayscale
//!   pixels. Behind the `mozjpeg-encode` feature; otherwise returns
//!   an `unimplemented` error and the writer should choose another
//!   filter for new images.
//!
//! The PDF-specific work — `/ColorSpace`, `/BitsPerComponent`, image
//! mask, soft mask, raw stream preservation — is done by `pdf_writer`
//! and `pdf_analysis`.

use jpeg_decoder::Decoder;
use pdf_core::{PdfError, PdfResult};

#[derive(Debug, Clone)]
pub struct JpegInfo {
    pub width: u16,
    pub height: u16,
    pub components: u8,
    pub bits_per_component: u8,
}

pub fn probe(bytes: &[u8]) -> PdfResult<JpegInfo> {
    let mut decoder = Decoder::new(bytes);
    decoder
        .read_info()
        .map_err(|e| PdfError::FilterDecode {
            filter: "DCTDecode".into(),
            reason: e.to_string(),
        })?;
    let info = decoder.info().ok_or_else(|| PdfError::FilterDecode {
        filter: "DCTDecode".into(),
        reason: "no SOF info".into(),
    })?;
    Ok(JpegInfo {
        width: info.width,
        height: info.height,
        components: match info.pixel_format {
            jpeg_decoder::PixelFormat::L8 | jpeg_decoder::PixelFormat::L16 => 1,
            jpeg_decoder::PixelFormat::RGB24 => 3,
            jpeg_decoder::PixelFormat::CMYK32 => 4,
        },
        bits_per_component: 8,
    })
}

#[cfg(feature = "mozjpeg-encode")]
pub fn encode_baseline(_pixels: &[u8], _w: u32, _h: u32, _components: u8) -> PdfResult<Vec<u8>> {
    Err(PdfError::FilterEncode {
        filter: "DCTDecode".into(),
        reason: "mozjpeg-encode feature stub: link mozjpeg-sys here".into(),
    })
}

#[cfg(not(feature = "mozjpeg-encode"))]
pub fn encode_baseline(_pixels: &[u8], _w: u32, _h: u32, _components: u8) -> PdfResult<Vec<u8>> {
    Err(PdfError::FilterEncode {
        filter: "DCTDecode".into(),
        reason: "enable `mozjpeg-encode` feature to encode JPEG".into(),
    })
}
