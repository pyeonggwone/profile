//! Image XObject builder.
//!
//! Per `build/06-pdf-writer/DESIGN.md` we support two image input
//! formats for new images added by the editor:
//!
//! - JPEG (`/Filter /DCTDecode`): the input bytes ARE the JPEG file —
//!   pass through. We use `pdf_filters::dct::probe` to read width,
//!   height and components.
//! - 8-bit raw RGB / grayscale: wrap with `/Filter /FlateDecode` and a
//!   PNG predictor for compression.
//!
//! The PDF-side concerns — `/ColorSpace`, `/BitsPerComponent`,
//! `/Width`, `/Height`, masks — are written here directly; cipher /
//! encoder primitives come from allowed OSS adapters.

use pdf_core::{PdfDict, PdfNumber, PdfObject, PdfResult, PdfStream};
use pdf_filters::{dct, encode_chain};

/// High-level description of an image to be embedded.
#[derive(Debug, Clone)]
pub enum ImageInput<'a> {
    Jpeg(&'a [u8]),
    /// Raw 8-bit RGB pixels in row-major order, length = w * h * 3.
    RawRgb {
        bytes: &'a [u8],
        width: u32,
        height: u32,
    },
    /// Raw 8-bit grayscale pixels.
    RawGray {
        bytes: &'a [u8],
        width: u32,
        height: u32,
    },
}

#[derive(Debug, Clone)]
pub struct BuiltImage {
    pub stream: PdfStream,
    pub width: u32,
    pub height: u32,
}

pub fn build_image(input: ImageInput<'_>) -> PdfResult<BuiltImage> {
    match input {
        ImageInput::Jpeg(bytes) => {
            let info = dct::probe(bytes)?;
            let mut dict = base_image_dict(info.width as u32, info.height as u32, info.components);
            dict.insert(b"Filter".to_vec(), PdfObject::Name(b"DCTDecode".to_vec()));
            dict.insert(
                b"Length".to_vec(),
                PdfObject::Number(PdfNumber::Integer(bytes.len() as i64)),
            );
            Ok(BuiltImage {
                stream: PdfStream {
                    dict,
                    raw_data: bytes.to_vec(),
                    raw_range: None,
                },
                width: info.width as u32,
                height: info.height as u32,
            })
        }
        ImageInput::RawRgb {
            bytes,
            width,
            height,
        } => raw_image(bytes, width, height, 3),
        ImageInput::RawGray {
            bytes,
            width,
            height,
        } => raw_image(bytes, width, height, 1),
    }
}

fn raw_image(bytes: &[u8], width: u32, height: u32, comps: u8) -> PdfResult<BuiltImage> {
    let expected = (width as usize) * (height as usize) * (comps as usize);
    if bytes.len() != expected {
        return Err(pdf_core::PdfError::Write(format!(
            "raw image: expected {expected} bytes, got {}",
            bytes.len()
        )));
    }
    let encoded = encode_chain(&[b"FlateDecode".as_ref()], bytes)?;
    let mut dict = base_image_dict(width, height, comps);
    dict.insert(b"Filter".to_vec(), PdfObject::Name(b"FlateDecode".to_vec()));
    dict.insert(
        b"Length".to_vec(),
        PdfObject::Number(PdfNumber::Integer(encoded.len() as i64)),
    );
    Ok(BuiltImage {
        stream: PdfStream {
            dict,
            raw_data: encoded,
            raw_range: None,
        },
        width,
        height,
    })
}

fn base_image_dict(width: u32, height: u32, comps: u8) -> PdfDict {
    let mut d = PdfDict::new();
    d.insert(b"Type".to_vec(), PdfObject::Name(b"XObject".to_vec()));
    d.insert(b"Subtype".to_vec(), PdfObject::Name(b"Image".to_vec()));
    d.insert(
        b"Width".to_vec(),
        PdfObject::Number(PdfNumber::Integer(width as i64)),
    );
    d.insert(
        b"Height".to_vec(),
        PdfObject::Number(PdfNumber::Integer(height as i64)),
    );
    d.insert(
        b"BitsPerComponent".to_vec(),
        PdfObject::Number(PdfNumber::Integer(8)),
    );
    let cs: &[u8] = match comps {
        1 => b"DeviceGray",
        3 => b"DeviceRGB",
        4 => b"DeviceCMYK",
        _ => b"DeviceRGB",
    };
    d.insert(b"ColorSpace".to_vec(), PdfObject::Name(cs.to_vec()));
    d
}
