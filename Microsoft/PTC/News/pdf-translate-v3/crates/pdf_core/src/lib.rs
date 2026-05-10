//! pdf_core
//!
//! PDF primitive object model. This crate is the lowest layer of the
//! workspace: it defines `PdfObject`, indirect references, byte ranges and
//! the shared error type. It contains no I/O, no parsing and no encoding.
//!
//! Design references:
//! - `build/05-document-model/DESIGN.md`
//! - `build/03-pdf-reader/DESIGN.md` (object grammar)
//! - `build/06-pdf-writer/DESIGN.md` (primitive serialization)

#![forbid(unsafe_code)]

pub mod error;
pub mod object;
pub mod range;
pub mod reference;

pub use error::{PdfError, PdfResult, PdfWarning};
pub use object::{DictExt, PdfDict, PdfNumber, PdfObject, PdfStream, PdfString};
pub use range::ByteRange;
pub use reference::{ObjectId, ObjectRef};
