//! High-level PDF builder: track object offsets, emit xref + trailer.

use std::collections::BTreeMap;
use std::io::Write;

use pdf_core::{ObjectId, PdfDict, PdfError, PdfObject, PdfResult, PdfStream};

use crate::serializer;

/// Records where an emitted object lives in the output buffer.
#[derive(Debug, Clone, Copy)]
pub struct WrittenObject {
    pub id: ObjectId,
    pub offset: u64,
}

/// Append-mode PDF writer. Holds an output `Vec<u8>` and a map of
/// `(object id -> offset)`. `finalize_xref_and_trailer` emits the xref,
/// trailer and `startxref` block.
pub struct PdfFileBuilder {
    pub buffer: Vec<u8>,
    pub written: BTreeMap<ObjectId, u64>,
}

impl PdfFileBuilder {
    pub fn new() -> Self {
        Self {
            buffer: Vec::new(),
            written: BTreeMap::new(),
        }
    }

    pub fn from_existing(bytes: Vec<u8>) -> Self {
        Self {
            buffer: bytes,
            written: BTreeMap::new(),
        }
    }

    /// Write a PDF file header. Use this only for fresh PDFs.
    pub fn write_header(&mut self, version: &str) -> PdfResult<()> {
        write!(&mut self.buffer, "%PDF-{version}\n").map_err(io)?;
        // Per PDF spec: a comment with 4 high-bit bytes hints binary content.
        self.buffer.write_all(b"%\xE2\xE3\xCF\xD3\n").map_err(io)?;
        Ok(())
    }

    pub fn write_object(&mut self, id: ObjectId, value: &PdfObject) -> PdfResult<()> {
        let offset = self.buffer.len() as u64;
        self.written.insert(id, offset);
        serializer::write_object(&mut self.buffer, id, value)?;
        Ok(())
    }

    /// Build a stream object whose body is the encoded form of `data`
    /// using `filters` (e.g. `&[b"FlateDecode"]`).
    pub fn make_encoded_stream(
        &self,
        mut dict: PdfDict,
        filters: &[&[u8]],
        data: &[u8],
    ) -> PdfResult<PdfStream> {
        let encoded = pdf_filters::encode_chain(filters, data)?;
        if !filters.is_empty() {
            let filter_obj = if filters.len() == 1 {
                PdfObject::Name(filters[0].to_vec())
            } else {
                PdfObject::Array(
                    filters
                        .iter()
                        .map(|f| PdfObject::Name(f.to_vec()))
                        .collect(),
                )
            };
            dict.insert(b"Filter".to_vec(), filter_obj);
        }
        dict.insert(
            b"Length".to_vec(),
            PdfObject::Number(pdf_core::PdfNumber::Integer(encoded.len() as i64)),
        );
        Ok(PdfStream {
            dict,
            raw_data: encoded,
            raw_range: None,
        })
    }

    /// Emit the xref table, trailer dictionary, `startxref` and `%%EOF`.
    /// `extra_trailer_entries` lets the caller add `/Prev`, `/Encrypt` etc.
    pub fn finalize_xref_and_trailer(
        &mut self,
        size: u32,
        root: ObjectId,
        info: Option<ObjectId>,
        extra_trailer_entries: PdfDict,
    ) -> PdfResult<u64> {
        let xref_offset = self.buffer.len() as u64;

        // Build a dense [first..first+count) layout. For the MVP we emit a
        // single subsection covering 0..size with whatever entries we have
        // and free placeholders elsewhere.
        self.buffer.write_all(b"xref\n").map_err(io)?;
        write!(&mut self.buffer, "0 {size}\n").map_err(io)?;
        // Object 0 is always free, generation 65535 (head of free list).
        self.buffer
            .write_all(b"0000000000 65535 f \n")
            .map_err(io)?;
        for n in 1..size {
            let id_candidates: Vec<ObjectId> = self
                .written
                .keys()
                .filter(|i| i.number == n)
                .copied()
                .collect();
            if let Some(id) = id_candidates.first() {
                let offset = self.written[id];
                write!(
                    &mut self.buffer,
                    "{:010} {:05} n \n",
                    offset, id.generation
                )
                .map_err(io)?;
            } else {
                self.buffer
                    .write_all(b"0000000000 00000 f \n")
                    .map_err(io)?;
            }
        }

        // Trailer dictionary
        let mut trailer = extra_trailer_entries;
        trailer.insert(
            b"Size".to_vec(),
            PdfObject::Number(pdf_core::PdfNumber::Integer(size as i64)),
        );
        trailer.insert(
            b"Root".to_vec(),
            PdfObject::Reference(pdf_core::ObjectRef { id: root }),
        );
        if let Some(info_id) = info {
            trailer.insert(
                b"Info".to_vec(),
                PdfObject::Reference(pdf_core::ObjectRef { id: info_id }),
            );
        }
        self.buffer.write_all(b"trailer\n").map_err(io)?;
        serializer::write_dict(&mut self.buffer, &trailer)?;
        self.buffer.write_all(b"\n").map_err(io)?;

        write!(&mut self.buffer, "startxref\n{xref_offset}\n%%EOF\n").map_err(io)?;
        Ok(xref_offset)
    }
}

impl Default for PdfFileBuilder {
    fn default() -> Self {
        Self::new()
    }
}

fn io(e: std::io::Error) -> PdfError {
    PdfError::Write(e.to_string())
}
