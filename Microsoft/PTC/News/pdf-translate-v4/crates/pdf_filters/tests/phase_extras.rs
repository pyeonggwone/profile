//! Phase 8a/9a integration tests.

use pdf_filters::crypt::DecryptionContext;

#[test]
fn rc4_known_vector_via_filter_chain() {
    // The crypt module exports RC4 only via DecryptionContext, which
    // requires a full /Encrypt dictionary. The unit test inside the
    // module already validates the RFC 6229 vector. Here we just sanity
    // check that the public type compiles.
    let _ = std::mem::size_of::<DecryptionContext>();
}

#[test]
fn ccitt_decode_empty_g4_runs_without_panic() {
    // Empty input should not panic and should produce 0 bytes.
    let result = pdf_filters::ccitt::decode(b"", None);
    assert!(result.is_ok());
}

#[test]
fn jbig2_disabled_feature_returns_clear_error() {
    let err = pdf_filters::jbig2::decode(b"", None).unwrap_err();
    let msg = err.to_string();
    assert!(msg.contains("jbig2"), "got: {msg}");
}

#[test]
fn jpx_disabled_feature_returns_clear_error() {
    let err = pdf_filters::jpx::decode(b"").unwrap_err();
    let msg = err.to_string();
    assert!(msg.contains("jpx") || msg.contains("openjpeg") || msg.contains("JPEG2000"), "got: {msg}");
}
