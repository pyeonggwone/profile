//! High-level document orchestration: combine header, startxref,
//! xref/trailer and indirect-object loading into `RawPdf` and `ParsedPdf`.

use std::collections::BTreeMap;

use pdf_core::{
    DictExt, ObjectId, ObjectRef, PdfDict, PdfError, PdfObject, PdfResult, PdfWarning,
};
use pdf_filters::crypt::{decrypt_object_in_place, AuthResult, DecryptionContext};

use crate::header::{find_header, PdfHeader};
use crate::lexer::Cursor;
use crate::object_parser::{ObjectEntry, ObjectParser};
use crate::page_tree::PageTree;
use crate::startxref::find_startxref;
use crate::xref::{XrefEntry, XrefTable};

/// Original PDF bytes plus the raw byte ranges that locate every object.
pub struct RawPdf {
    pub bytes: Vec<u8>,
    pub header: PdfHeader,
    pub startxref: u64,
}

/// Parsed object graph. Object stream decoding is deferred until
/// `resolve_compressed`.
pub struct ParsedPdf {
    pub raw: RawPdf,
    pub xref: XrefTable,
    pub objects: BTreeMap<ObjectId, ObjectEntry>,
    pub warnings: Vec<PdfWarning>,
    /// Set if the document was encrypted and successfully decrypted.
    pub decryption: Option<DecryptionContext>,
    pub auth_result: Option<AuthResult>,
}

impl ParsedPdf {
    /// Parse with the empty (default) password. Sufficient for documents
    /// that have only an owner password and a non-zero permissions
    /// bitmask, or documents without encryption.
    pub fn from_bytes(bytes: Vec<u8>) -> PdfResult<Self> {
        Self::from_bytes_with_password(bytes, "")
    }

    pub fn from_bytes_with_password(bytes: Vec<u8>, password: &str) -> PdfResult<Self> {
        let header = find_header(&bytes)?;
        let startxref = find_startxref(&bytes)? as u64;
        let xref = XrefTable::parse_chain(&bytes, startxref)?;

        let raw = RawPdf {
            bytes,
            header,
            startxref,
        };

        let mut objects: BTreeMap<ObjectId, ObjectEntry> = BTreeMap::new();
        let mut warnings: Vec<PdfWarning> = Vec::new();
        warnings.extend(xref.warnings.iter().cloned());

        // Pass 1: load all in-use objects whose offset points into the file.
        for (id, entry) in &xref.entries {
            if let XrefEntry::InUse { offset, .. } = entry {
                let off = *offset as usize;
                if off >= raw.bytes.len() {
                    warnings.push(PdfWarning::new(
                        "OBJECT_OFFSET_OOB",
                        format!("object {id} offset {off} out of range"),
                    ));
                    continue;
                }
                let mut cursor = Cursor::at(&raw.bytes, off);
                match ObjectParser::parse_indirect_object(&mut cursor) {
                    Ok(obj) => {
                        objects.insert(obj.id, obj);
                    }
                    Err(e) => {
                        warnings.push(PdfWarning::new(
                            "OBJECT_PARSE_FAILED",
                            format!("object {id}: {e}"),
                        ).at(off));
                    }
                }
            }
        }

        let mut parsed = Self {
            raw,
            xref,
            objects,
            warnings,
            decryption: None,
            auth_result: None,
        };

        // Decryption pass: if /Encrypt is present, derive the file key
        // from the supplied password and decrypt every loaded object's
        // strings + stream raw_data, except the /Encrypt object itself.
        let encrypt_ref = parsed.xref.trailer.get_reference(b"Encrypt".as_ref());
        if let Some(eref) = encrypt_ref {
            let encrypt_dict = parsed
                .lookup(eref.id)
                .and_then(PdfObject::as_dict)
                .ok_or_else(|| PdfError::TrailerMalformed("/Encrypt object missing".into()))?
                .clone();
            match DecryptionContext::from_trailer(&parsed.xref.trailer, &encrypt_dict, password) {
                Ok((ctx, auth)) => {
                    let encrypt_id = eref.id;
                    for (id, entry) in parsed.objects.iter_mut() {
                        if *id == encrypt_id {
                            continue;
                        }
                        if let Err(e) = decrypt_object_in_place(&ctx, *id, &mut entry.value) {
                            parsed.warnings.push(PdfWarning::new(
                                "DECRYPT_FAILED",
                                format!("object {id}: {e}"),
                            ));
                        }
                    }
                    parsed.decryption = Some(ctx);
                    parsed.auth_result = Some(auth);
                }
                Err(PdfError::FilterDecode { reason, .. }) if reason == "wrong password" => {
                    return Err(if password.is_empty() {
                        PdfError::PasswordRequired
                    } else {
                        PdfError::WrongPassword
                    });
                }
                Err(e) => return Err(e),
            }
        }

        // Pass 2: expand /ObjStm compressed objects.
        parsed.resolve_compressed()?;
        Ok(parsed)
    }

    fn resolve_compressed(&mut self) -> PdfResult<()> {
        let compressed: Vec<(ObjectId, u32, u32)> = self
            .xref
            .entries
            .iter()
            .filter_map(|(id, e)| match e {
                XrefEntry::Compressed {
                    container_object,
                    index,
                } => Some((*id, *container_object, *index)),
                _ => None,
            })
            .collect();
        if compressed.is_empty() {
            return Ok(());
        }

        for (id, container, index) in compressed {
            let container_id = ObjectId::new(container, 0);
            let container_obj = match self.objects.get(&container_id) {
                Some(o) => o.clone(),
                None => {
                    self.warnings.push(PdfWarning::new(
                        "OBJSTM_MISSING",
                        format!("container {container} not loaded for compressed {id}"),
                    ));
                    continue;
                }
            };
            let stream = match container_obj.value {
                PdfObject::Stream(s) => s,
                _ => continue,
            };
            let n = stream
                .dict
                .get_integer(b"N".as_ref())
                .ok_or_else(|| PdfError::Invariant("ObjStm missing /N".into()))?;
            let first = stream
                .dict
                .get_integer(b"First".as_ref())
                .ok_or_else(|| PdfError::Invariant("ObjStm missing /First".into()))?;
            let decoded = pdf_filters::decode_stream(&stream.dict, &stream.raw_data)?;
            for w in decoded.warnings {
                self.warnings.push(w);
            }
            let buf = decoded.bytes;
            // Header: N pairs of "objnum offset" before the object data.
            let mut cur = Cursor::at(&buf, 0);
            let mut header_offsets: Vec<(u32, usize)> = Vec::with_capacity(n as usize);
            for _ in 0..n {
                cur.skip_ws_and_comments();
                let onum = read_uint(&mut cur)? as u32;
                cur.skip_ws_and_comments();
                let offset = read_uint(&mut cur)? as usize;
                header_offsets.push((onum, offset));
            }
            let want_index = index as usize;
            if want_index >= header_offsets.len() {
                self.warnings.push(PdfWarning::new(
                    "OBJSTM_INDEX_OOB",
                    format!("index {want_index} >= N {}", header_offsets.len()),
                ));
                continue;
            }
            let (onum, off) = header_offsets[want_index];
            if onum != id.number {
                self.warnings.push(PdfWarning::new(
                    "OBJSTM_NUMBER_MISMATCH",
                    format!("expected {} got {}", id.number, onum),
                ));
            }
            let body_start = first as usize + off;
            if body_start >= buf.len() {
                self.warnings.push(PdfWarning::new(
                    "OBJSTM_BODY_OOB",
                    format!("object body offset {body_start} >= len {}", buf.len()),
                ));
                continue;
            }
            let mut sub_cursor = Cursor::at(&buf, body_start);
            match ObjectParser::parse_object(&mut sub_cursor) {
                Ok(value) => {
                    let entry = ObjectEntry {
                        id: ObjectId::new(id.number, 0),
                        value,
                        byte_range: container_obj.byte_range,
                    };
                    self.objects.insert(entry.id, entry);
                }
                Err(e) => {
                    self.warnings.push(PdfWarning::new(
                        "OBJSTM_PARSE_FAILED",
                        format!("object {}: {e}", id.number),
                    ));
                }
            }
        }
        Ok(())
    }

    pub fn root(&self) -> Option<ObjectRef> {
        self.xref.trailer.get_reference(b"Root".as_ref())
    }

    pub fn info(&self) -> Option<ObjectRef> {
        self.xref.trailer.get_reference(b"Info".as_ref())
    }

    pub fn lookup(&self, id: ObjectId) -> Option<&PdfObject> {
        self.objects.get(&id).map(|e| &e.value)
    }

    pub fn resolve(&self, obj: &PdfObject) -> Option<&PdfObject> {
        match obj {
            PdfObject::Reference(r) => self.lookup(r.id),
            other => Some(other),
        }
    }

    pub fn page_count(&self) -> PdfResult<u32> {
        let pt = PageTree::build(self)?;
        Ok(pt.pages.len() as u32)
    }

    pub fn page_tree(&self) -> PdfResult<PageTree> {
        PageTree::build(self)
    }

    pub fn pdf_version(&self) -> &str {
        &self.raw.header.version
    }
}

fn read_uint(cursor: &mut Cursor<'_>) -> PdfResult<u64> {
    let token = cursor.read_regular_token();
    std::str::from_utf8(token)
        .map_err(|_| PdfError::Invariant("non-utf8 int".into()))?
        .parse::<u64>()
        .map_err(|_| PdfError::Invariant("bad int".into()))
}

#[allow(dead_code)]
fn _trailer_dict(_: &PdfDict) {}
