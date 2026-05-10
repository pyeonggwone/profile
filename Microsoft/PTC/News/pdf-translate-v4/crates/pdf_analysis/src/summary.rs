//! High-level document summary used by the web boundary.

use pdf_core::{PdfObject, PdfResult, PdfString};
use pdf_reader::ParsedPdf;

#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Default)]
#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
pub struct DocumentSummary {
    pub pdf_version: String,
    pub page_count: u32,
    pub title: Option<String>,
    pub author: Option<String>,
    pub subject: Option<String>,
    pub creator: Option<String>,
    pub producer: Option<String>,
    pub encrypted: bool,
    pub pages: Vec<PageSummary>,
    pub warnings: Vec<String>,
}

#[derive(Debug, Clone, Default)]
#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
pub struct PageSummary {
    pub page: u32,
    pub width: f32,
    pub height: f32,
    pub rotate: i32,
}

pub fn summarize(doc: &ParsedPdf) -> PdfResult<DocumentSummary> {
    let pdf_version = doc.pdf_version().to_string();
    let pages = doc.page_tree()?;
    let mut page_summaries = Vec::with_capacity(pages.pages.len());
    for (i, p) in pages.pages.iter().enumerate() {
        let (w, h) = p
            .media_box
            .map(|mb| ((mb[2] - mb[0]) as f32, (mb[3] - mb[1]) as f32))
            .unwrap_or((612.0, 792.0));
        page_summaries.push(PageSummary {
            page: i as u32 + 1,
            width: w,
            height: h,
            rotate: p.rotate,
        });
    }
    let mut summary = DocumentSummary {
        pdf_version,
        page_count: pages.pages.len() as u32,
        encrypted: doc.xref.trailer.contains_key(b"Encrypt".as_ref()),
        pages: page_summaries,
        warnings: doc.warnings.iter().map(|w| format!("{}: {}", w.code, w.detail)).collect(),
        ..Default::default()
    };
    // Read /Info dictionary if present.
    if let Some(info_ref) = doc.info() {
        if let Some(PdfObject::Dict(info_dict)) = doc.lookup(info_ref.id) {
            summary.title = info_dict.get(b"Title".as_ref()).and_then(text_field);
            summary.author = info_dict.get(b"Author".as_ref()).and_then(text_field);
            summary.subject = info_dict.get(b"Subject".as_ref()).and_then(text_field);
            summary.creator = info_dict.get(b"Creator".as_ref()).and_then(text_field);
            summary.producer = info_dict.get(b"Producer".as_ref()).and_then(text_field);
        }
    }
    Ok(summary)
}

fn text_field(v: &PdfObject) -> Option<String> {
    match v {
        PdfObject::String(s) => Some(decode_text_string(s)),
        _ => None,
    }
}

fn decode_text_string(s: &PdfString) -> String {
    let bytes = s.bytes();
    if bytes.len() >= 2 && bytes[0] == 0xFE && bytes[1] == 0xFF {
        let mut out = String::new();
        let mut i = 2;
        while i + 1 < bytes.len() {
            let code = ((bytes[i] as u16) << 8) | bytes[i + 1] as u16;
            if let Some(c) = char::from_u32(code as u32) {
                out.push(c);
            }
            i += 2;
        }
        return out;
    }
    bytes.iter().map(|&b| b as char).collect()
}
