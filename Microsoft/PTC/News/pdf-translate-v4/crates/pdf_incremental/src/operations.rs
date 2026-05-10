//! Web-side edit operations as understood by the incremental writer.
//!
//! Mirrors the UI contract documented in `build/02-web-boundary` and the
//! editable-document design in `build/05-document-model`.

#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy)]
#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
pub enum FontFamily {
    Helvetica,
    HelveticaBold,
    TimesRoman,
    Courier,
}

impl FontFamily {
    pub fn base14_name(&self) -> &'static [u8] {
        match self {
            FontFamily::Helvetica => b"Helvetica",
            FontFamily::HelveticaBold => b"Helvetica-Bold",
            FontFamily::TimesRoman => b"Times-Roman",
            FontFamily::Courier => b"Courier",
        }
    }

    pub fn resource_name(&self) -> &'static str {
        match self {
            FontFamily::Helvetica => "PdfTrHelv",
            FontFamily::HelveticaBold => "PdfTrHelvBd",
            FontFamily::TimesRoman => "PdfTrTimes",
            FontFamily::Courier => "PdfTrCour",
        }
    }
}

#[derive(Debug, Clone)]
#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
#[cfg_attr(feature = "serde", serde(tag = "type"))]
pub enum EditOperation {
    /// Paint a filled rectangle. Coordinates use the same top-left-oriented
    /// page space as extracted text runs.
    FillRect {
        page: u32,
        x: f32,
        y: f32,
        width: f32,
        height: f32,
        color: [f32; 3],
    },
    /// Add a literal text run on a page in PDF user space coordinates.
    AddText {
        page: u32,
        x: f32,
        y: f32,
        text: String,
        font: FontFamily,
        size: f32,
        color: [f32; 3],
    },
    /// Add a Unicode text run using an embedded TrueType/OpenType font.
    AddTextEmbedded {
        page: u32,
        x: f32,
        y: f32,
        text: String,
        #[cfg_attr(feature = "serde", serde(rename = "fontPath"))]
        font_path: String,
        size: f32,
        color: [f32; 3],
    },
    /// Add a free-text annotation. Visual appearance is generated.
    AddTextAnnotation {
        page: u32,
        x: f32,
        y: f32,
        contents: String,
    },
    /// Add a JPEG image to a page. `bytes_b64` is the JPEG file
    /// base64-encoded (web boundary keeps the JSON compact).
    AddImageJpeg {
        page: u32,
        x: f32,
        y: f32,
        width: f32,
        height: f32,
        #[cfg_attr(feature = "serde", serde(rename = "bytesB64"))]
        bytes_b64: String,
    },
}

impl EditOperation {
    pub fn page(&self) -> u32 {
        match self {
            EditOperation::FillRect { page, .. } => *page,
            EditOperation::AddText { page, .. } => *page,
            EditOperation::AddTextEmbedded { page, .. } => *page,
            EditOperation::AddTextAnnotation { page, .. } => *page,
            EditOperation::AddImageJpeg { page, .. } => *page,
        }
    }
}
