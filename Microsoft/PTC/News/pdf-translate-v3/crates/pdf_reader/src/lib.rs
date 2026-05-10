//! pdf_reader
//!
//! Direct (recursive-descent + byte scanner) parser for PDF files.
//! Implements the order described in `build/03-pdf-reader/DESIGN.md`:
//!
//! 1. Locate `%PDF-` header and version
//! 2. Find `%%EOF` and `startxref`
//! 3. Parse cross-reference table (xref table or xref stream)
//! 4. Parse trailer dictionary
//! 5. Build the indirect-object index
//! 6. Expose page tree traversal
//!
//! No external PDF library is used. The parser only depends on
//! `pdf_core` (model) and `pdf_filters` (stream decode).

#![forbid(unsafe_code)]

pub mod document;
pub mod header;
pub mod lexer;
pub mod object_parser;
pub mod page_tree;
pub mod startxref;
pub mod xref;

pub use document::{ParsedPdf, RawPdf};
pub use header::PdfHeader;
pub use object_parser::{ObjectEntry, ObjectParser};
pub use page_tree::{PageInfo, PageTree};
pub use xref::{XrefEntry, XrefTable};
