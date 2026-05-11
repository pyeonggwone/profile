//! Filter-level round-trip tests.

#[test]
fn ascii_hex_roundtrip() {
    let original = b"Hello, ASCII Hex!";
    let encoded = pdf_filters::ascii_hex::encode(original);
    let decoded = pdf_filters::ascii_hex::decode(&encoded).unwrap();
    assert_eq!(decoded, original);
}

#[test]
fn ascii85_roundtrip() {
    let original = b"Round-trip through ASCII85.";
    let encoded = pdf_filters::ascii85::encode(original);
    let decoded = pdf_filters::ascii85::decode(&encoded).unwrap();
    assert_eq!(decoded, original);
}

#[test]
fn run_length_roundtrip() {
    let original = b"AAAAAABCDEEFGGGGGGGGG";
    let encoded = pdf_filters::run_length::encode(original);
    let decoded = pdf_filters::run_length::decode(&encoded).unwrap();
    assert_eq!(decoded, original);
}

#[test]
fn flate_chain_with_decode_stream() {
    use pdf_core::{PdfDict, PdfObject};
    let original = b"BT /F1 12 Tf (Hello flate) Tj ET";
    let encoded = pdf_filters::flate::encode(original).unwrap();
    let mut dict = PdfDict::new();
    dict.insert(b"Filter".to_vec(), PdfObject::Name(b"FlateDecode".to_vec()));
    let result = pdf_filters::decode_stream(&dict, &encoded).unwrap();
    assert_eq!(result.bytes, original);
}

#[test]
fn unsupported_filter_returns_unsupported_error() {
    use pdf_core::{PdfDict, PdfObject};
    let mut dict = PdfDict::new();
    dict.insert(
        b"Filter".to_vec(),
        PdfObject::Name(b"NotARealFilter".to_vec()),
    );
    let err = pdf_filters::decode_stream(&dict, b"data").unwrap_err();
    assert!(
        matches!(err, pdf_core::PdfError::UnsupportedFilter(_)),
        "got: {err:?}"
    );
}

#[test]
fn known_unimplemented_filter_falls_back_to_raw() {
    use pdf_core::{PdfDict, PdfObject};
    // JBIG2 without the feature must be raw-preserved with a warning.
    let mut dict = PdfDict::new();
    dict.insert(
        b"Filter".to_vec(),
        PdfObject::Name(b"JBIG2Decode".to_vec()),
    );
    let result = pdf_filters::decode_stream(&dict, b"raw bytes").unwrap();
    assert_eq!(result.bytes, b"raw bytes");
    assert!(matches!(
        result.status,
        pdf_filters::FilterStatus::PreservedRaw
    ));
    assert!(!result.warnings.is_empty());
}
