/// Half-open byte range `[start, end)` into the original PDF buffer.
///
/// Byte ranges are how the document model preserves the raw bytes of an
/// object: instead of cloning the bytes we keep `(start, end)` into the
/// original PDF file. The `pdf_incremental` writer uses this to copy
/// untouched objects byte-for-byte (see `build/07-incremental-update`).
#[derive(Debug, Clone, Copy, Eq, PartialEq, Hash)]
#[cfg_attr(
    feature = "serde",
    derive(serde::Serialize, serde::Deserialize)
)]
pub struct ByteRange {
    pub start: usize,
    pub end: usize,
}

impl ByteRange {
    pub fn new(start: usize, end: usize) -> Self {
        debug_assert!(start <= end, "ByteRange start must be <= end");
        Self { start, end }
    }

    pub fn len(&self) -> usize {
        self.end - self.start
    }

    pub fn is_empty(&self) -> bool {
        self.start == self.end
    }

    pub fn slice<'a>(&self, data: &'a [u8]) -> &'a [u8] {
        &data[self.start..self.end]
    }
}
