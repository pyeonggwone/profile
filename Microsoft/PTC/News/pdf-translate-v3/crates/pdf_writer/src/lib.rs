//! pdf_writer
//!
//! Direct PDF serializer. Implements primitive serialization, indirect
//! object writing, stream encoding, the classic xref table writer and
//! the trailer writer. See `build/06-pdf-writer/DESIGN.md`.
//!
//! The incremental-update orchestration lives in `pdf_incremental` and
//! builds on top of these primitives.

#![forbid(unsafe_code)]

pub mod content;
pub mod font;
pub mod image;
pub mod serializer;
pub mod writer;

pub use content::ContentStreamBuilder;
pub use font::{EmbeddedFont, EmbeddedFontIds};
pub use image::{build_image, BuiltImage, ImageInput};
pub use serializer::{write_object, write_value};
pub use writer::{PdfFileBuilder, WrittenObject};
