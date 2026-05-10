//! Incremental update planner.
//!
//! Given a parsed PDF and a list of `EditOperation`, produces a new
//! byte buffer that is `[original bytes][new objects][new xref][trailer
//! /Prev=...][startxref][%%EOF]`.

use std::collections::{BTreeMap, BTreeSet};
use std::fs;

use base64::Engine;
use pdf_core::{
    DictExt, ObjectId, ObjectRef, PdfDict, PdfError, PdfNumber, PdfObject, PdfResult,
};
use pdf_reader::ParsedPdf;
use pdf_writer::{build_image, ContentStreamBuilder, EmbeddedFont, ImageInput, PdfFileBuilder};

use crate::operations::{EditOperation, FontFamily};

/// Result of running [`IncrementalWriter::build`].
pub struct IncrementalUpdate {
    pub bytes: Vec<u8>,
    pub new_objects: Vec<ObjectId>,
    pub new_size: u32,
}

pub struct IncrementalWriter<'a> {
    doc: &'a ParsedPdf,
}

impl<'a> IncrementalWriter<'a> {
    pub fn new(doc: &'a ParsedPdf) -> Self {
        Self { doc }
    }

    pub fn build(&self, operations: &[EditOperation]) -> PdfResult<IncrementalUpdate> {
        // Refuse encrypted PDFs at write time. Read-only flow is fine.
        if self.doc.xref.trailer.contains_key(b"Encrypt".as_ref()) {
            return Err(PdfError::EncryptedNotSupported);
        }

        // 1. Determine the next free object number.
        // /Size is "highest object number + 1"; if missing, fall back to scanning.
        let max_existing = self
            .doc
            .xref
            .entries
            .keys()
            .map(|id| id.number)
            .max()
            .unwrap_or(0);
        let trailer_size = self
            .doc
            .xref
            .trailer
            .get_integer(b"Size".as_ref())
            .map(|s| s as u32)
            .unwrap_or(0);
        let mut alloc = ObjectAlloc {
            next: trailer_size.max(max_existing + 1),
        };

        // 2. Group operations by 1-based page index.
        let mut by_page: BTreeMap<u32, Vec<&EditOperation>> = BTreeMap::new();
        for op in operations {
            by_page.entry(op.page()).or_default().push(op);
        }

        // 3. Resolve page tree once.
        let page_tree = self.doc.page_tree()?;

        // 4. Pre-compute fonts we will need.
        let mut needed_fonts: BTreeSet<FontFamily> = BTreeSet::new();
        let mut embedded_fonts: BTreeMap<String, EmbeddedFont> = BTreeMap::new();
        for op in operations {
            match op {
                EditOperation::AddText { font, .. } => {
                    needed_fonts.insert(*font);
                }
                EditOperation::AddTextEmbedded { font_path, text, .. } => {
                    if !embedded_fonts.contains_key(font_path) {
                        let bytes = fs::read(font_path).map_err(|e| {
                            PdfError::Write(format!("read embedded font {font_path:?}: {e}"))
                        })?;
                        let font = EmbeddedFont::parse(bytes).map_err(|e| {
                            PdfError::Write(format!("parse embedded font {font_path:?}: {e}"))
                        })?;
                        embedded_fonts.insert(font_path.clone(), font);
                    }
                    let entry = embedded_fonts.get_mut(font_path).ok_or_else(|| {
                        PdfError::Write(format!("embedded font missing after parse: {font_path}"))
                    })?;
                    entry.note_string(text);
                }
                _ => {}
            }
        }

        // 5. Initialize the builder seeded with the original PDF bytes.
        let mut builder = PdfFileBuilder::from_existing(self.doc.raw.bytes.clone());
        if !builder.buffer.ends_with(b"\n") {
            builder.buffer.push(b'\n');
        }
        let mut new_object_ids: Vec<ObjectId> = Vec::new();

        // Emit Base14 font objects.
        let mut font_objects: BTreeMap<FontFamily, ObjectId> = BTreeMap::new();
        for f in &needed_fonts {
            let id = alloc.next_id();
            font_objects.insert(*f, id);
            let mut dict = PdfDict::new();
            dict.insert(b"Type".to_vec(), PdfObject::Name(b"Font".to_vec()));
            dict.insert(b"Subtype".to_vec(), PdfObject::Name(b"Type1".to_vec()));
            dict.insert(
                b"BaseFont".to_vec(),
                PdfObject::Name(f.base14_name().to_vec()),
            );
            dict.insert(
                b"Encoding".to_vec(),
                PdfObject::Name(b"WinAnsiEncoding".to_vec()),
            );
            builder.write_object(id, &PdfObject::Dict(dict))?;
            new_object_ids.push(id);
        }

        let mut embedded_font_objects: BTreeMap<String, (String, ObjectId)> = BTreeMap::new();
        for (idx, (font_path, font)) in embedded_fonts.iter().enumerate() {
            let ids = font.clone().write(&mut builder, || alloc.next_id())?;
            new_object_ids.extend([
                ids.type0_id,
                ids.cid_font_id,
                ids.descriptor_id,
                ids.font_file_id,
                ids.tounicode_id,
            ]);
            embedded_font_objects.insert(font_path.clone(), (format!("PdfTrEmb{idx}"), ids.type0_id));
        }

        // 6. For each modified page, emit a new content stream + annots,
        //    then a fresh revision of the page dictionary.
        for (page_index_1, ops) in &by_page {
            let pi = (*page_index_1 as usize)
                .checked_sub(1)
                .ok_or_else(|| PdfError::PageTree("page index is 1-based".into()))?;
            let page = page_tree
                .pages
                .get(pi)
                .ok_or_else(|| PdfError::PageTree(format!("page {page_index_1} not found")))?;

            let page_height = page.media_box.map(|mb| mb[3] - mb[1]).unwrap_or(792.0);

            // 6a. Build image XObjects (need their object ids before the
            //     content stream so we can reference resource names).
            let mut image_ids: Vec<(String, ObjectId)> = Vec::new();
            for (img_idx, op) in ops.iter().enumerate() {
                if let EditOperation::AddImageJpeg { bytes_b64, .. } = op {
                    let bytes = base64::engine::general_purpose::STANDARD
                        .decode(bytes_b64.as_bytes())
                        .map_err(|e| {
                            PdfError::Write(format!("base64 decode for image: {e}"))
                        })?;
                    let built = build_image(ImageInput::Jpeg(&bytes))?;
                    let img_id = alloc.next_id();
                    builder.write_object(img_id, &PdfObject::Stream(built.stream))?;
                    new_object_ids.push(img_id);
                    image_ids.push((format!("PdfTrIm{}p{}", img_idx, page_index_1), img_id));
                }
            }

            // 6b. Build the combined content stream (text + image draws).
            let has_drawing = ops.iter().any(|op| {
                matches!(
                    op,
                    EditOperation::FillRect { .. }
                        | EditOperation::AddText { .. }
                        | EditOperation::AddTextEmbedded { .. }
                        | EditOperation::AddImageJpeg { .. }
                )
            });
            let new_content_id = if has_drawing {
                let mut content = ContentStreamBuilder::new().save_state();
                let mut img_iter = image_ids.iter();
                for op in ops {
                    match op {
                        EditOperation::FillRect {
                            x,
                            y,
                            width,
                            height,
                            color,
                            ..
                        } => {
                            let pdf_y = (page_height as f32) - *y - *height;
                            content = content
                                .set_rgb_fill(color[0], color[1], color[2])
                                .fill_rect(*x, pdf_y, *width, *height);
                        }
                        EditOperation::AddText {
                            x,
                            y,
                            text,
                            font,
                            size,
                            color,
                            ..
                        } => {
                            let pdf_y = (page_height as f32) - *y;
                            content = content
                                .set_rgb_fill(color[0], color[1], color[2])
                                .add_text(font.resource_name(), *size, *x, pdf_y, text);
                        }
                        EditOperation::AddTextEmbedded {
                            x,
                            y,
                            text,
                            font_path,
                            size,
                            color,
                            ..
                        } => {
                            let pdf_y = (page_height as f32) - *y;
                            let font = embedded_fonts.get(font_path).ok_or_else(|| {
                                PdfError::Write(format!("embedded font not prepared: {font_path}"))
                            })?;
                            let (resource_name, _) = embedded_font_objects.get(font_path).ok_or_else(|| {
                                PdfError::Write(format!("embedded font resource missing: {font_path}"))
                            })?;
                            let hex = font.encode_to_hex(text);
                            content = content
                                .set_rgb_fill(color[0], color[1], color[2])
                                .add_text_unicode(resource_name, *size, *x, pdf_y, &hex);
                        }
                        EditOperation::AddImageJpeg {
                            x,
                            y,
                            width,
                            height,
                            ..
                        } => {
                            let (resource_name, _) = img_iter.next().expect("image id parity");
                            let pdf_y = (page_height as f32) - *y - *height;
                            content = content.draw_image(
                                resource_name,
                                *x,
                                pdf_y,
                                *width,
                                *height,
                            );
                        }
                        _ => {}
                    }
                }
                content = content.restore_state();
                let bytes = content.finish();

                let stream = builder.make_encoded_stream(
                    PdfDict::new(),
                    &[b"FlateDecode".as_ref()],
                    &bytes,
                )?;
                let id = alloc.next_id();
                builder.write_object(id, &PdfObject::Stream(stream))?;
                new_object_ids.push(id);
                Some(id)
            } else {
                None
            };

            // 6c. Annotations
            let annot_ops: Vec<&EditOperation> = ops
                .iter()
                .copied()
                .filter(|op| matches!(op, EditOperation::AddTextAnnotation { .. }))
                .collect();
            let mut annot_ids: Vec<ObjectId> = Vec::new();
            for op in annot_ops {
                if let EditOperation::AddTextAnnotation {
                    x, y, contents, ..
                } = op
                {
                    let pdf_y = (page_height as f32) - *y;
                    let mut a = PdfDict::new();
                    a.insert(b"Type".to_vec(), PdfObject::Name(b"Annot".to_vec()));
                    a.insert(b"Subtype".to_vec(), PdfObject::Name(b"Text".to_vec()));
                    a.insert(
                        b"Rect".to_vec(),
                        PdfObject::Array(vec![
                            PdfObject::Number(PdfNumber::Real(*x as f64)),
                            PdfObject::Number(PdfNumber::Real(pdf_y as f64 - 16.0)),
                            PdfObject::Number(PdfNumber::Real(*x as f64 + 16.0)),
                            PdfObject::Number(PdfNumber::Real(pdf_y as f64)),
                        ]),
                    );
                    a.insert(
                        b"Contents".to_vec(),
                        PdfObject::String(pdf_core::PdfString::Literal(
                            contents.as_bytes().to_vec(),
                        )),
                    );
                    let id = alloc.next_id();
                    builder.write_object(id, &PdfObject::Dict(a))?;
                    annot_ids.push(id);
                    new_object_ids.push(id);
                }
            }

            // 6d. Build a new page dictionary revision in one pass.
            let original_page = self
                .doc
                .lookup(page.object_id)
                .and_then(PdfObject::as_dict)
                .ok_or_else(|| {
                    PdfError::PageTree(format!("page object {} not found", page.object_id))
                })?;
            let mut new_page = original_page.clone();

            if let Some(content_id) = new_content_id {
                new_page.insert(
                    b"Contents".to_vec(),
                    make_appended_contents(original_page, content_id),
                );
                new_page.insert(
                    b"Resources".to_vec(),
                    PdfObject::Dict(merge_resources(
                        original_page,
                        &font_objects,
                        &embedded_font_objects,
                        &image_ids,
                    )),
                );
            }
            if !annot_ids.is_empty() {
                new_page.insert(
                    b"Annots".to_vec(),
                    PdfObject::Array(merge_annots(original_page, &annot_ids)),
                );
            }
            builder.write_object(page.object_id, &PdfObject::Dict(new_page))?;
            new_object_ids.push(page.object_id);
        }

        // 7. Emit new xref + trailer with /Prev linkage.
        let prev_xref = self.doc.raw.startxref;
        let mut extra = PdfDict::new();
        extra.insert(
            b"Prev".to_vec(),
            PdfObject::Number(PdfNumber::Integer(prev_xref as i64)),
        );
        if let Some(id_obj) = self.doc.xref.trailer.get(b"ID".as_ref()).cloned() {
            extra.insert(b"ID".to_vec(), id_obj);
        }

        let root_id = self
            .doc
            .root()
            .ok_or_else(|| PdfError::TrailerMalformed("missing /Root".into()))?
            .id;
        let info_id = self.doc.info().map(|r| r.id);

        let new_size = alloc.next;
        builder.finalize_xref_and_trailer(new_size, root_id, info_id, extra)?;

        Ok(IncrementalUpdate {
            bytes: builder.buffer,
            new_objects: new_object_ids,
            new_size,
        })
    }
}

fn make_appended_contents(original_page: &PdfDict, new_content_id: ObjectId) -> PdfObject {
    let new_ref = PdfObject::Reference(ObjectRef { id: new_content_id });
    match original_page.get(b"Contents".as_ref()) {
        Some(PdfObject::Reference(r)) => {
            PdfObject::Array(vec![PdfObject::Reference(*r), new_ref])
        }
        Some(PdfObject::Array(arr)) => {
            let mut v = arr.clone();
            v.push(new_ref);
            PdfObject::Array(v)
        }
        _ => PdfObject::Array(vec![new_ref]),
    }
}

fn merge_resources(
    original_page: &PdfDict,
    fonts: &BTreeMap<FontFamily, ObjectId>,
    embedded_fonts: &BTreeMap<String, (String, ObjectId)>,
    images: &[(String, ObjectId)],
) -> PdfDict {
    let mut resources = match original_page.get(b"Resources".as_ref()) {
        Some(PdfObject::Dict(d)) => d.clone(),
        _ => PdfDict::new(),
    };
    let mut font_dict = match resources.get(b"Font".as_ref()) {
        Some(PdfObject::Dict(d)) => d.clone(),
        _ => PdfDict::new(),
    };
    for (family, id) in fonts {
        font_dict.insert(
            family.resource_name().as_bytes().to_vec(),
            PdfObject::Reference(ObjectRef { id: *id }),
        );
    }
    for (name, id) in embedded_fonts.values() {
        font_dict.insert(
            name.as_bytes().to_vec(),
            PdfObject::Reference(ObjectRef { id: *id }),
        );
    }
    resources.insert(b"Font".to_vec(), PdfObject::Dict(font_dict));

    if !images.is_empty() {
        let mut xobject = match resources.get(b"XObject".as_ref()) {
            Some(PdfObject::Dict(d)) => d.clone(),
            _ => PdfDict::new(),
        };
        for (name, id) in images {
            xobject.insert(
                name.as_bytes().to_vec(),
                PdfObject::Reference(ObjectRef { id: *id }),
            );
        }
        resources.insert(b"XObject".to_vec(), PdfObject::Dict(xobject));
    }
    resources
}

fn merge_annots(original_page: &PdfDict, new_ids: &[ObjectId]) -> Vec<PdfObject> {
    let mut out: Vec<PdfObject> = match original_page.get(b"Annots".as_ref()) {
        Some(PdfObject::Array(arr)) => arr.clone(),
        Some(PdfObject::Reference(r)) => vec![PdfObject::Reference(*r)],
        _ => Vec::new(),
    };
    for id in new_ids {
        out.push(PdfObject::Reference(ObjectRef { id: *id }));
    }
    out
}

struct ObjectAlloc {
    next: u32,
}

impl ObjectAlloc {
    fn next_id(&mut self) -> ObjectId {
        let id = ObjectId::new(self.next, 0);
        self.next += 1;
        id
    }
}

// FontFamily ordering for the BTreeMap key.
impl PartialOrd for FontFamily {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for FontFamily {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        (*self as i32).cmp(&(*other as i32))
    }
}

impl PartialEq for FontFamily {
    fn eq(&self, other: &Self) -> bool {
        (*self as i32) == (*other as i32)
    }
}

impl Eq for FontFamily {}
