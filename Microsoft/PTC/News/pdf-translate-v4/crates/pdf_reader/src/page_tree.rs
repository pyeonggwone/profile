//! Page tree traversal: walk Catalog -> /Pages -> /Kids and collect
//! every leaf `/Type /Page` with inherited attributes resolved.

use std::collections::HashSet;

use pdf_core::{
    DictExt, ObjectId, PdfDict, PdfError, PdfObject, PdfResult,
};

use crate::document::ParsedPdf;

#[derive(Debug, Clone)]
pub struct PageInfo {
    pub object_id: ObjectId,
    pub media_box: Option<[f64; 4]>,
    pub crop_box: Option<[f64; 4]>,
    pub rotate: i32,
    /// References to the page content streams (resolved order matters).
    pub content_object_ids: Vec<ObjectId>,
    pub resources: Option<PdfDict>,
}

#[derive(Debug, Clone, Default)]
pub struct PageTree {
    pub pages: Vec<PageInfo>,
}

impl PageTree {
    pub fn build(doc: &ParsedPdf) -> PdfResult<Self> {
        let root_ref = doc
            .root()
            .ok_or_else(|| PdfError::PageTree("trailer has no /Root".into()))?;
        let catalog = doc
            .lookup(root_ref.id)
            .ok_or_else(|| PdfError::PageTree("/Root not found".into()))?;
        let catalog_dict = catalog
            .as_dict()
            .ok_or_else(|| PdfError::PageTree("/Root not a dict".into()))?;
        let pages_ref = catalog_dict
            .get_reference(b"Pages".as_ref())
            .ok_or_else(|| PdfError::PageTree("Catalog missing /Pages".into()))?;

        let mut pages: Vec<PageInfo> = Vec::new();
        let mut visited: HashSet<ObjectId> = HashSet::new();
        let inherited = InheritedAttrs::default();
        Self::walk(doc, pages_ref.id, &inherited, &mut pages, &mut visited)?;
        Ok(Self { pages })
    }

    fn walk(
        doc: &ParsedPdf,
        node_id: ObjectId,
        inherited: &InheritedAttrs,
        out: &mut Vec<PageInfo>,
        visited: &mut HashSet<ObjectId>,
    ) -> PdfResult<()> {
        if !visited.insert(node_id) {
            return Err(PdfError::PageTree(format!(
                "cycle at object {node_id}"
            )));
        }
        let node = match doc.lookup(node_id) {
            Some(o) => o,
            None => return Ok(()), // tolerate missing kid
        };
        let dict = match node.as_dict() {
            Some(d) => d,
            None => return Ok(()),
        };

        let merged = inherited.inherit(dict);

        let type_name = dict
            .get(b"Type".as_ref())
            .and_then(PdfObject::as_name)
            .map(|b| b.to_vec());
        let is_pages = matches!(type_name.as_deref(), Some(b"Pages"));
        let is_page = matches!(type_name.as_deref(), Some(b"Page"))
            || (!is_pages && dict.get(b"Kids".as_ref()).is_none());

        if is_page {
            let content_object_ids = collect_contents_refs(dict);
            let resources = merged.resources.clone();
            out.push(PageInfo {
                object_id: node_id,
                media_box: merged.media_box,
                crop_box: merged.crop_box,
                rotate: merged.rotate,
                content_object_ids,
                resources,
            });
            return Ok(());
        }

        if let Some(PdfObject::Array(kids)) = dict.get(b"Kids".as_ref()) {
            for kid in kids {
                if let Some(r) = kid.as_reference() {
                    Self::walk(doc, r.id, &merged, out, visited)?;
                }
            }
        }
        Ok(())
    }
}

#[derive(Default, Clone)]
struct InheritedAttrs {
    media_box: Option<[f64; 4]>,
    crop_box: Option<[f64; 4]>,
    rotate: i32,
    resources: Option<PdfDict>,
}

impl InheritedAttrs {
    fn inherit(&self, dict: &PdfDict) -> Self {
        Self {
            media_box: read_rectangle(dict, b"MediaBox").or(self.media_box),
            crop_box: read_rectangle(dict, b"CropBox").or(self.crop_box),
            rotate: dict
                .get_integer(b"Rotate".as_ref())
                .map(|i| i as i32)
                .unwrap_or(self.rotate),
            resources: match dict.get(b"Resources".as_ref()) {
                Some(PdfObject::Dict(d)) => Some(d.clone()),
                _ => self.resources.clone(),
            },
        }
    }
}

fn read_rectangle(dict: &PdfDict, key: &[u8]) -> Option<[f64; 4]> {
    let arr = dict.get(key).and_then(PdfObject::as_array)?;
    if arr.len() != 4 {
        return None;
    }
    let mut out = [0.0; 4];
    for (i, v) in arr.iter().enumerate() {
        out[i] = v.as_number()?.as_f64();
    }
    Some(out)
}

fn collect_contents_refs(dict: &PdfDict) -> Vec<ObjectId> {
    match dict.get(b"Contents".as_ref()) {
        Some(PdfObject::Reference(r)) => vec![r.id],
        Some(PdfObject::Array(arr)) => arr
            .iter()
            .filter_map(|o| o.as_reference().map(|r| r.id))
            .collect(),
        _ => Vec::new(),
    }
}
