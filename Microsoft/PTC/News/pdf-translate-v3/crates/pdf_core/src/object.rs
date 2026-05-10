use std::collections::BTreeMap;

use crate::reference::ObjectRef;

/// PDF number primitive. PDF distinguishes integer and real but accepts the
/// same lexical form for many numbers; we keep both to round-trip cleanly.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum PdfNumber {
    Integer(i64),
    Real(f64),
}

impl PdfNumber {
    pub fn as_f64(self) -> f64 {
        match self {
            PdfNumber::Integer(i) => i as f64,
            PdfNumber::Real(r) => r,
        }
    }

    pub fn as_i64(self) -> Option<i64> {
        match self {
            PdfNumber::Integer(i) => Some(i),
            PdfNumber::Real(r) if r.fract() == 0.0 => Some(r as i64),
            _ => None,
        }
    }
}

/// PDF string primitive. PDF stores strings as either literal `(...)` or
/// hex `<...>`. Both decode to bytes; semantic decoding (PDFDocEncoding,
/// UTF-16BE, ToUnicode) lives in `pdf_analysis`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PdfString {
    Literal(Vec<u8>),
    Hex(Vec<u8>),
}

impl PdfString {
    pub fn bytes(&self) -> &[u8] {
        match self {
            PdfString::Literal(b) | PdfString::Hex(b) => b,
        }
    }
}

/// PDF dictionary. Keys are PDF Names (kept as raw bytes for fidelity).
/// Insertion order is preserved with `BTreeMap` keyed by `Vec<u8>` —
/// PDF dictionaries are unordered semantically but preserving a stable
/// canonical order makes the writer output deterministic.
pub type PdfDict = BTreeMap<Vec<u8>, PdfObject>;

/// PDF stream: a dictionary plus the raw, undecoded bytes.
///
/// We always store raw bytes. Decoding happens on demand via `pdf_filters`.
/// `raw_range` (when present) points back into the source PDF buffer so
/// the writer can emit the bytes without re-encoding.
#[derive(Debug, Clone)]
pub struct PdfStream {
    pub dict: PdfDict,
    pub raw_data: Vec<u8>,
    pub raw_range: Option<crate::range::ByteRange>,
}

/// Top-level PDF object value.
#[derive(Debug, Clone)]
pub enum PdfObject {
    Null,
    Boolean(bool),
    Number(PdfNumber),
    /// Raw name bytes (without the leading `/`).
    Name(Vec<u8>),
    String(PdfString),
    Array(Vec<PdfObject>),
    Dict(PdfDict),
    Stream(PdfStream),
    Reference(ObjectRef),
}

impl PdfObject {
    pub fn as_dict(&self) -> Option<&PdfDict> {
        match self {
            PdfObject::Dict(d) => Some(d),
            PdfObject::Stream(s) => Some(&s.dict),
            _ => None,
        }
    }

    pub fn as_array(&self) -> Option<&[PdfObject]> {
        match self {
            PdfObject::Array(a) => Some(a),
            _ => None,
        }
    }

    pub fn as_name(&self) -> Option<&[u8]> {
        match self {
            PdfObject::Name(n) => Some(n),
            _ => None,
        }
    }

    pub fn as_reference(&self) -> Option<ObjectRef> {
        match self {
            PdfObject::Reference(r) => Some(*r),
            _ => None,
        }
    }

    pub fn as_number(&self) -> Option<PdfNumber> {
        match self {
            PdfObject::Number(n) => Some(*n),
            _ => None,
        }
    }

    pub fn as_integer(&self) -> Option<i64> {
        self.as_number().and_then(PdfNumber::as_i64)
    }
}

/// Lookup helpers on dictionaries that read the value by name.
pub trait DictExt {
    fn get_name<'a>(&'a self, key: &[u8]) -> Option<&'a PdfObject>;
    fn get_reference(&self, key: &[u8]) -> Option<ObjectRef>;
    fn get_integer(&self, key: &[u8]) -> Option<i64>;
}

impl DictExt for PdfDict {
    fn get_name<'a>(&'a self, key: &[u8]) -> Option<&'a PdfObject> {
        self.get(key)
    }

    fn get_reference(&self, key: &[u8]) -> Option<ObjectRef> {
        self.get(key).and_then(PdfObject::as_reference)
    }

    fn get_integer(&self, key: &[u8]) -> Option<i64> {
        self.get(key).and_then(PdfObject::as_integer)
    }
}
