//! pdf_filters
//!
//! PDF stream filter chain. PDF stream dictionaries declare a `/Filter`
//! that may be a single name or an array of names; this crate decodes
//! those chains. Filter chain orchestration is implemented directly here
//! (PDF-specific). Compression / image primitives delegate to allowed
//! source-open OSS adapters as documented in
//! `build/04-stream-filters/DESIGN.md`.
//!
//! Currently implemented:
//! - `FlateDecode`            (zlib/Deflate adapter via `flate2`)
//! - `ASCIIHexDecode`         (direct)
//! - `ASCII85Decode`          (direct)
//! - `RunLengthDecode`        (direct)
//! - `LZWDecode`              (direct)
//! - PNG/TIFF predictor       (post-decode for FlateDecode/LZWDecode)
//!
//! Not yet implemented (raw-preserved with warning):
//! - `DCTDecode`, `JPXDecode`, `CCITTFaxDecode`, `JBIG2Decode`, `Crypt`

#![forbid(unsafe_code)]

use pdf_core::{DictExt, PdfDict, PdfError, PdfObject, PdfResult, PdfWarning};

pub mod ascii85;
pub mod ascii_hex;
pub mod ccitt;
pub mod crypt;
pub mod dct;
pub mod flate;
pub mod jbig2;
pub mod jpx;
pub mod lzw;
pub mod predictor;
pub mod run_length;

/// Outcome of a single filter step.
#[derive(Debug, Clone)]
pub enum FilterStatus {
    Decoded,
    PreservedRaw,
    FailedRecoverable,
}

#[derive(Debug, Clone)]
pub struct FilterResult {
    pub status: FilterStatus,
    pub bytes: Vec<u8>,
    pub warnings: Vec<PdfWarning>,
}

impl FilterResult {
    pub fn decoded(bytes: Vec<u8>) -> Self {
        Self {
            status: FilterStatus::Decoded,
            bytes,
            warnings: Vec::new(),
        }
    }

    pub fn preserved(bytes: Vec<u8>, warning: PdfWarning) -> Self {
        Self {
            status: FilterStatus::PreservedRaw,
            bytes,
            warnings: vec![warning],
        }
    }
}

/// Names of all filters that, when encountered, should preserve the raw
/// bytes rather than fail the document.
pub fn is_known_but_unimplemented(name: &[u8]) -> bool {
    // JPX and JBIG2 stay raw-preserved unless their feature is enabled.
    let jpx_enabled = cfg!(feature = "jpx-openjpeg");
    let jbig2_enabled = cfg!(feature = "jbig2-jbig2dec");
    match name {
        b"JPXDecode" | b"JPX" => !jpx_enabled,
        b"JBIG2Decode" => !jbig2_enabled,
        b"Crypt" => false, // Crypt is dispatched separately by the reader
        _ => false,
    }
}

fn collect_filter_names(dict: &PdfDict) -> Vec<Vec<u8>> {
    match dict.get(b"Filter".as_ref()) {
        Some(PdfObject::Name(n)) => vec![n.clone()],
        Some(PdfObject::Array(arr)) => arr
            .iter()
            .filter_map(|o| o.as_name().map(|n| n.to_vec()))
            .collect(),
        _ => Vec::new(),
    }
}

fn collect_decode_params(dict: &PdfDict, count: usize) -> Vec<Option<PdfDict>> {
    match dict.get(b"DecodeParms".as_ref()) {
        Some(PdfObject::Dict(d)) => {
            let mut v = Vec::with_capacity(count);
            v.push(Some(d.clone()));
            for _ in 1..count {
                v.push(None);
            }
            v
        }
        Some(PdfObject::Array(arr)) => arr
            .iter()
            .map(|o| match o {
                PdfObject::Dict(d) => Some(d.clone()),
                _ => None,
            })
            .collect(),
        _ => vec![None; count],
    }
}

/// Apply the full `/Filter` + `/DecodeParms` chain declared in `dict`
/// to `raw`. On success returns the fully-decoded bytes; on a
/// recoverable failure (unknown / unimplemented filter) returns the raw
/// bytes plus warnings.
pub fn decode_stream(dict: &PdfDict, raw: &[u8]) -> PdfResult<FilterResult> {
    let names = collect_filter_names(dict);
    if names.is_empty() {
        return Ok(FilterResult::decoded(raw.to_vec()));
    }
    let params = collect_decode_params(dict, names.len());
    let mut buffer = raw.to_vec();
    let mut warnings = Vec::new();
    let mut status = FilterStatus::Decoded;

    for (idx, name) in names.iter().enumerate() {
        let p = params.get(idx).and_then(|o| o.as_ref());
        match decode_one(name, &buffer, p) {
            Ok(mut step) => {
                buffer = std::mem::take(&mut step.bytes);
                warnings.append(&mut step.warnings);
                if matches!(step.status, FilterStatus::PreservedRaw) {
                    status = FilterStatus::PreservedRaw;
                    break;
                }
            }
            Err(err) => {
                if is_known_but_unimplemented(name) {
                    warnings.push(PdfWarning::new(
                        "FILTER_NOT_IMPLEMENTED",
                        format!("filter `{}` not implemented yet", String::from_utf8_lossy(name)),
                    ));
                    status = FilterStatus::PreservedRaw;
                    break;
                }
                return Err(err);
            }
        }
    }

    Ok(FilterResult {
        status,
        bytes: buffer,
        warnings,
    })
}

fn decode_one(
    name: &[u8],
    input: &[u8],
    params: Option<&PdfDict>,
) -> PdfResult<FilterResult> {
    match name {
        b"FlateDecode" | b"Fl" => {
            let mut decoded = flate::decode(input)?;
            if let Some(p) = params {
                decoded = predictor::apply_predictor_decode(&decoded, p)?;
            }
            Ok(FilterResult::decoded(decoded))
        }
        b"ASCIIHexDecode" | b"AHx" => Ok(FilterResult::decoded(ascii_hex::decode(input)?)),
        b"ASCII85Decode" | b"A85" => Ok(FilterResult::decoded(ascii85::decode(input)?)),
        b"RunLengthDecode" | b"RL" => Ok(FilterResult::decoded(run_length::decode(input)?)),
        b"LZWDecode" | b"LZW" => {
            let early_change = params
                .and_then(|p| p.get_integer(b"EarlyChange".as_ref()))
                .unwrap_or(1) as i32;
            let mut decoded = lzw::decode(input, early_change == 1)?;
            if let Some(p) = params {
                decoded = predictor::apply_predictor_decode(&decoded, p)?;
            }
            Ok(FilterResult::decoded(decoded))
        }
        // PDF JPEG stream IS a JPEG file. We don't decompress to pixels
        // server-side because the browser decodes it natively. We mark
        // it Decoded so the chain considers this filter handled.
        b"DCTDecode" | b"DCT" => Ok(FilterResult::decoded(input.to_vec())),
        b"CCITTFaxDecode" | b"CCF" => Ok(FilterResult::decoded(ccitt::decode(input, params)?)),
        b"JPXDecode" | b"JPX" => match jpx::decode(input) {
            Ok(bytes) => Ok(FilterResult::decoded(bytes)),
            Err(_) => Ok(FilterResult::preserved(
                input.to_vec(),
                PdfWarning::new(
                    "FILTER_NOT_IMPLEMENTED",
                    "JPXDecode requires `jpx-openjpeg` feature".to_string(),
                ),
            )),
        },
        b"JBIG2Decode" => match jbig2::decode(input, params) {
            Ok(bytes) => Ok(FilterResult::decoded(bytes)),
            Err(_) => Ok(FilterResult::preserved(
                input.to_vec(),
                PdfWarning::new(
                    "FILTER_NOT_IMPLEMENTED",
                    "JBIG2Decode requires `jbig2-jbig2dec` feature".to_string(),
                ),
            )),
        },
        b"Crypt" => {
            // Crypt filter is applied at the reader level (per-object key).
            // If we see it here it means the reader already decrypted, so
            // pass through.
            Ok(FilterResult::decoded(input.to_vec()))
        }
        other => Err(PdfError::UnsupportedFilter(
            String::from_utf8_lossy(other).into_owned(),
        )),
    }
}

/// Encode `data` with the given filter list using default settings.
/// Used by the writer for newly-generated streams.
pub fn encode_chain(filters: &[&[u8]], data: &[u8]) -> PdfResult<Vec<u8>> {
    let mut buffer = data.to_vec();
    for f in filters {
        buffer = encode_one(f, &buffer)?;
    }
    Ok(buffer)
}

fn encode_one(name: &[u8], input: &[u8]) -> PdfResult<Vec<u8>> {
    match name {
        b"FlateDecode" => Ok(flate::encode(input)?),
        b"ASCIIHexDecode" => Ok(ascii_hex::encode(input)),
        b"ASCII85Decode" => Ok(ascii85::encode(input)),
        b"RunLengthDecode" => Ok(run_length::encode(input)),
        other => Err(PdfError::FilterEncode {
            filter: String::from_utf8_lossy(other).into_owned(),
            reason: "encode not implemented".into(),
        }),
    }
}
