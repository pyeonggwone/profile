//! pdf_incremental
//!
//! Append-only update writer. Implements the design in
//! `build/07-incremental-update/DESIGN.md`:
//!
//! 1. Take the original PDF bytes verbatim as the prefix.
//! 2. Allocate object numbers above the existing `/Size`.
//! 3. Emit modified page dictionaries as new revisions.
//! 4. Emit added content streams / annotations as new objects.
//! 5. Append a new xref table whose `/Prev` points at the previous one.
//! 6. Verify by re-opening with `pdf_reader`.

#![forbid(unsafe_code)]

pub mod operations;
pub mod plan;

pub use operations::{EditOperation, FontFamily};
pub use plan::{IncrementalUpdate, IncrementalWriter};
