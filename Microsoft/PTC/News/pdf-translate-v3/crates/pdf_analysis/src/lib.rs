//! pdf_analysis
//!
//! Text, image and metadata extraction. The MVP scope follows
//! `build/08-analysis-extraction/DESIGN.md`:
//!
//! - per-page text positions via a content-stream operator tokenizer
//! - simple font encoding fallback (WinAnsi / standard Type1)
//! - `DocumentSummary` for the web boundary

#![forbid(unsafe_code)]

pub mod cmap;
pub mod color;
pub mod content_tokens;
pub mod extract;
pub mod shaping;
pub mod summary;

pub use cmap::ToUnicodeCMap;
pub use extract::{extract_text, PageText, TextRun};
pub use summary::{DocumentSummary, PageSummary};
