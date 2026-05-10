//! End-to-end test: build a tiny PDF with `pdf_writer`, parse it back
//! with `pdf_reader`, then run an incremental update with
//! `pdf_incremental` and verify (a) the original prefix is preserved
//! byte-for-byte and (b) the result is still parseable.

use pdf_core::{ObjectId, ObjectRef, PdfDict, PdfNumber, PdfObject, PdfStream};
use pdf_incremental::{EditOperation, FontFamily, IncrementalWriter};
use pdf_reader::ParsedPdf;
use pdf_writer::{ContentStreamBuilder, PdfFileBuilder};

fn build_tiny_pdf() -> Vec<u8> {
    let mut b = PdfFileBuilder::new();
    b.write_header("1.4").unwrap();

    // Object 1: Catalog -> /Pages 2 0 R
    let catalog_id = ObjectId::new(1, 0);
    let pages_id = ObjectId::new(2, 0);
    let page_id = ObjectId::new(3, 0);
    let content_id = ObjectId::new(4, 0);
    let font_id = ObjectId::new(5, 0);

    let mut catalog = PdfDict::new();
    catalog.insert(b"Type".to_vec(), PdfObject::Name(b"Catalog".to_vec()));
    catalog.insert(
        b"Pages".to_vec(),
        PdfObject::Reference(ObjectRef { id: pages_id }),
    );
    b.write_object(catalog_id, &PdfObject::Dict(catalog)).unwrap();

    // Object 2: Pages
    let mut pages = PdfDict::new();
    pages.insert(b"Type".to_vec(), PdfObject::Name(b"Pages".to_vec()));
    pages.insert(b"Count".to_vec(), PdfObject::Number(PdfNumber::Integer(1)));
    pages.insert(
        b"Kids".to_vec(),
        PdfObject::Array(vec![PdfObject::Reference(ObjectRef { id: page_id })]),
    );
    b.write_object(pages_id, &PdfObject::Dict(pages)).unwrap();

    // Object 5: Font (Helvetica)
    let mut font = PdfDict::new();
    font.insert(b"Type".to_vec(), PdfObject::Name(b"Font".to_vec()));
    font.insert(b"Subtype".to_vec(), PdfObject::Name(b"Type1".to_vec()));
    font.insert(b"BaseFont".to_vec(), PdfObject::Name(b"Helvetica".to_vec()));
    b.write_object(font_id, &PdfObject::Dict(font)).unwrap();

    // Object 4: content stream
    let content_bytes = ContentStreamBuilder::new()
        .save_state()
        .add_text("F1", 18.0, 72.0, 720.0, "Hello PDF")
        .restore_state()
        .finish();
    let stream = b
        .make_encoded_stream(
            PdfDict::new(),
            &[b"FlateDecode".as_ref()],
            &content_bytes,
        )
        .unwrap();
    b.write_object(content_id, &PdfObject::Stream(stream)).unwrap();

    // Object 3: Page
    let mut page = PdfDict::new();
    page.insert(b"Type".to_vec(), PdfObject::Name(b"Page".to_vec()));
    page.insert(
        b"Parent".to_vec(),
        PdfObject::Reference(ObjectRef { id: pages_id }),
    );
    page.insert(
        b"MediaBox".to_vec(),
        PdfObject::Array(vec![
            PdfObject::Number(PdfNumber::Integer(0)),
            PdfObject::Number(PdfNumber::Integer(0)),
            PdfObject::Number(PdfNumber::Integer(612)),
            PdfObject::Number(PdfNumber::Integer(792)),
        ]),
    );
    page.insert(
        b"Contents".to_vec(),
        PdfObject::Reference(ObjectRef { id: content_id }),
    );
    let mut resources = PdfDict::new();
    let mut font_dict = PdfDict::new();
    font_dict.insert(
        b"F1".to_vec(),
        PdfObject::Reference(ObjectRef { id: font_id }),
    );
    resources.insert(b"Font".to_vec(), PdfObject::Dict(font_dict));
    page.insert(b"Resources".to_vec(), PdfObject::Dict(resources));
    b.write_object(page_id, &PdfObject::Dict(page)).unwrap();

    b.finalize_xref_and_trailer(6, catalog_id, None, PdfDict::new())
        .unwrap();

    b.buffer
}

#[test]
fn roundtrip_synthetic_pdf() {
    let pdf = build_tiny_pdf();
    let parsed = ParsedPdf::from_bytes(pdf.clone()).expect("parse synthetic pdf");
    assert_eq!(parsed.page_count().unwrap(), 1);
    assert_eq!(parsed.pdf_version(), "1.4");
    assert!(parsed.warnings.is_empty(), "warnings: {:?}", parsed.warnings);
}

#[test]
fn incremental_preserves_original_prefix() {
    let pdf = build_tiny_pdf();
    let parsed = ParsedPdf::from_bytes(pdf.clone()).expect("parse synthetic pdf");

    let edits = vec![EditOperation::AddText {
        page: 1,
        x: 100.0,
        y: 100.0,
        text: "Edited!".into(),
        font: FontFamily::Helvetica,
        size: 14.0,
        color: [1.0, 0.0, 0.0],
    }];

    let writer = IncrementalWriter::new(&parsed);
    let update = writer.build(&edits).expect("incremental update");

    assert!(
        update.bytes.len() >= pdf.len(),
        "incremental output should not shrink"
    );
    assert_eq!(
        &update.bytes[..pdf.len()],
        pdf.as_slice(),
        "original prefix must be byte-for-byte preserved"
    );

    let reparsed = ParsedPdf::from_bytes(update.bytes).expect("re-parse update");
    assert_eq!(reparsed.page_count().unwrap(), 1);
    assert!(reparsed.warnings.is_empty(), "warnings: {:?}", reparsed.warnings);
}

#[test]
fn extracted_text_finds_synthetic_string() {
    let pdf = build_tiny_pdf();
    let parsed = ParsedPdf::from_bytes(pdf).unwrap();
    let pages = pdf_analysis::extract_text(&parsed).unwrap();
    let joined: String = pages
        .into_iter()
        .flat_map(|p| p.runs.into_iter().map(|r| r.text))
        .collect::<Vec<_>>()
        .join(" ");
    assert!(joined.contains("Hello PDF"), "got: {joined}");
}

#[test]
fn render_plan_has_text_command() {
    let pdf = build_tiny_pdf();
    let parsed = ParsedPdf::from_bytes(pdf).unwrap();
    let plans = pdf_render_plan::build_render_plan(&parsed).unwrap();
    assert_eq!(plans.len(), 1);
    let has_text = plans[0].commands.iter().any(|c| match c {
        pdf_render_plan::RenderCommand::Text { text, .. } => text.contains("Hello"),
    });
    assert!(has_text, "plan: {:?}", plans[0].commands);
}
