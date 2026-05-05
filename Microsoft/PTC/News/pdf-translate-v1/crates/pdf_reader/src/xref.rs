//! Cross-reference table and trailer parser.
//!
//! Implements the classic `xref` / `trailer` form (PDF spec §7.5.4).
//! Cross-reference *streams* (PDF 1.5+) are detected here and decoded
//! once `pdf_filters` reports success; for the MVP we surface them as
//! a warning when the parser cannot identify them as a classic xref.

use std::collections::BTreeMap;

use pdf_core::{
    DictExt, ObjectId, PdfDict, PdfError, PdfObject, PdfResult, PdfWarning,
};

use crate::lexer::Cursor;
use crate::object_parser::ObjectParser;

#[derive(Debug, Clone, Copy)]
pub enum XrefEntry {
    /// In-use object: byte offset and generation.
    InUse { offset: u64, generation: u16 },
    /// Free entry on the linked list of free objects.
    Free { next_free: u64, generation: u16 },
    /// Compressed object inside an object stream (PDF 1.5+).
    Compressed {
        container_object: u32,
        index: u32,
    },
}

#[derive(Debug, Clone, Default)]
pub struct XrefTable {
    pub entries: BTreeMap<ObjectId, XrefEntry>,
    pub trailer: PdfDict,
    pub trailer_chain: Vec<XrefSection>,
    pub warnings: Vec<PdfWarning>,
}

#[derive(Debug, Clone)]
pub struct XrefSection {
    pub xref_offset: u64,
    pub trailer: PdfDict,
}

impl XrefTable {
    /// Parse the full xref + trailer chain starting at `xref_offset`.
    pub fn parse_chain(data: &[u8], xref_offset: u64) -> PdfResult<Self> {
        let mut table = Self::default();
        let mut visited: std::collections::HashSet<u64> = Default::default();
        let mut current = Some(xref_offset);

        while let Some(off) = current {
            if !visited.insert(off) {
                table.warnings.push(PdfWarning::new(
                    "XREF_CYCLE",
                    format!("xref chain visits offset {off} twice"),
                ));
                break;
            }
            let off_usize = off as usize;
            if off_usize >= data.len() {
                return Err(PdfError::XrefMalformed(format!(
                    "offset {off} beyond file length"
                )));
            }
            let mut cursor = Cursor::at(data, off_usize);
            cursor.skip_ws_and_comments();

            let trailer = if cursor.match_keyword(b"xref") {
                Self::parse_table_section(&mut cursor, &mut table)?
            } else {
                // Possibly an xref *stream*. Parse as an indirect object.
                let entry = ObjectParser::parse_indirect_object(&mut cursor)?;
                Self::parse_xref_stream(entry.value, &mut table)?
            };

            table.trailer_chain.push(XrefSection {
                xref_offset: off,
                trailer: trailer.clone(),
            });

            // Chain via /Prev
            current = trailer
                .get(b"Prev".as_ref())
                .and_then(|o| match o {
                    PdfObject::Number(n) => n.as_i64().map(|i| i as u64),
                    _ => None,
                });

            // First trailer wins as the "primary" trailer (newest)
            if table.trailer.is_empty() {
                table.trailer = trailer;
            }
        }
        Ok(table)
    }

    fn parse_table_section(
        cursor: &mut Cursor<'_>,
        table: &mut XrefTable,
    ) -> PdfResult<PdfDict> {
        cursor.skip_ws_and_comments();
        // One or more subsections: `<first> <count>` then count entries
        loop {
            cursor.skip_ws_and_comments();
            if cursor.remaining().starts_with(b"trailer") {
                cursor.match_keyword(b"trailer");
                break;
            }
            // Read subsection header: two integers
            let first = read_int(cursor)?;
            cursor.skip_ws_and_comments();
            let count = read_int(cursor)?;
            cursor.skip_ws_and_comments();
            for i in 0..count {
                let entry_bytes = cursor.remaining();
                if entry_bytes.len() < 20 {
                    return Err(PdfError::XrefMalformed(
                        "xref entry truncated".into(),
                    ));
                }
                // PDF §7.5.4: entries are 20 bytes:
                //   nnnnnnnnnn ggggg n\r\n  (or `f`)
                let line = &entry_bytes[..20];
                cursor.advance(20);
                let offset_or_next = std::str::from_utf8(&line[..10])
                    .map_err(|_| PdfError::XrefMalformed("bad offset".into()))?
                    .trim()
                    .parse::<u64>()
                    .map_err(|_| PdfError::XrefMalformed("bad offset int".into()))?;
                let generation = std::str::from_utf8(&line[11..16])
                    .map_err(|_| PdfError::XrefMalformed("bad generation".into()))?
                    .trim()
                    .parse::<u16>()
                    .map_err(|_| PdfError::XrefMalformed("bad gen int".into()))?;
                let kind = line[17];
                let id = ObjectId::new((first + i) as u32, generation);
                let entry = match kind {
                    b'n' => XrefEntry::InUse {
                        offset: offset_or_next,
                        generation,
                    },
                    b'f' => XrefEntry::Free {
                        next_free: offset_or_next,
                        generation,
                    },
                    other => {
                        return Err(PdfError::XrefMalformed(format!(
                            "unknown xref entry kind 0x{other:02x}"
                        )))
                    }
                };
                table.entries.insert(id, entry);
            }
        }
        cursor.skip_ws_and_comments();
        // Now parse the trailer dictionary.
        let trailer_obj = ObjectParser::parse_object(cursor)?;
        match trailer_obj {
            PdfObject::Dict(d) => Ok(d),
            _ => Err(PdfError::TrailerMalformed("trailer not a dictionary".into())),
        }
    }

    fn parse_xref_stream(value: PdfObject, table: &mut XrefTable) -> PdfResult<PdfDict> {
        let stream = match value {
            PdfObject::Stream(s) => s,
            _ => {
                return Err(PdfError::XrefMalformed(
                    "expected xref or xref stream".into(),
                ))
            }
        };
        let dict = stream.dict.clone();
        // /W = [t f1 f2]
        let w = dict
            .get(b"W".as_ref())
            .and_then(|o| o.as_array())
            .ok_or_else(|| PdfError::XrefMalformed("xref stream missing /W".into()))?;
        if w.len() < 3 {
            return Err(PdfError::XrefMalformed("/W must have 3 entries".into()));
        }
        let w0 = w[0].as_integer().unwrap_or(1) as usize;
        let w1 = w[1].as_integer().unwrap_or(0) as usize;
        let w2 = w[2].as_integer().unwrap_or(0) as usize;
        let entry_size = w0 + w1 + w2;

        let size = dict
            .get_integer(b"Size".as_ref())
            .ok_or_else(|| PdfError::XrefMalformed("xref stream missing /Size".into()))?
            as usize;
        let index_pairs: Vec<(usize, usize)> = match dict.get(b"Index".as_ref()) {
            Some(PdfObject::Array(arr)) => arr
                .chunks(2)
                .map(|c| {
                    let a = c[0].as_integer().unwrap_or(0) as usize;
                    let b = c.get(1).and_then(|x| x.as_integer()).unwrap_or(0) as usize;
                    (a, b)
                })
                .collect(),
            _ => vec![(0, size)],
        };

        let decoded = pdf_filters::decode_stream(&stream.dict, &stream.raw_data)?;
        let bytes = decoded.bytes;
        for w in decoded.warnings {
            table.warnings.push(w);
        }
        let mut cursor = 0usize;
        for (first, count) in index_pairs {
            for i in 0..count {
                if cursor + entry_size > bytes.len() {
                    return Err(PdfError::XrefMalformed(
                        "xref stream truncated".into(),
                    ));
                }
                let row = &bytes[cursor..cursor + entry_size];
                cursor += entry_size;
                let t = if w0 == 0 { 1 } else { read_be_uint(&row[..w0]) };
                let f1 = read_be_uint(&row[w0..w0 + w1]);
                let f2 = read_be_uint(&row[w0 + w1..]);
                let id = ObjectId::new((first + i) as u32, f2 as u16);
                let entry = match t {
                    0 => XrefEntry::Free {
                        next_free: f1,
                        generation: f2 as u16,
                    },
                    1 => XrefEntry::InUse {
                        offset: f1,
                        generation: f2 as u16,
                    },
                    2 => XrefEntry::Compressed {
                        container_object: f1 as u32,
                        index: f2 as u32,
                    },
                    other => {
                        table.warnings.push(PdfWarning::new(
                            "XREF_STREAM_UNKNOWN_TYPE",
                            format!("type {other} ignored"),
                        ));
                        continue;
                    }
                };
                table.entries.insert(id, entry);
            }
        }
        Ok(dict)
    }
}

fn read_int(cursor: &mut Cursor<'_>) -> PdfResult<u64> {
    let token = cursor.read_regular_token();
    std::str::from_utf8(token)
        .map_err(|_| PdfError::XrefMalformed("non-utf8 int".into()))?
        .parse::<u64>()
        .map_err(|_| PdfError::XrefMalformed("bad int".into()))
}

fn read_be_uint(b: &[u8]) -> u64 {
    let mut v = 0u64;
    for &x in b {
        v = (v << 8) | x as u64;
    }
    v
}
