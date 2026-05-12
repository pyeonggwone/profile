use anyhow::{anyhow, Context, Result};
use lopdf::{Dictionary, Document, Object, ObjectId, Stream};
use std::collections::BTreeMap;
use std::path::Path;

pub struct LoadedPdf {
    pub document: Document,
}

#[derive(Debug, Clone)]
pub struct ContentStreamData {
    pub page: u32,
    pub object_id: ObjectId,
    pub decoded: Vec<u8>,
    pub resources: Option<Dictionary>,
    pub font_resources: BTreeMap<String, FontResourceInfo>,
}

#[derive(Debug, Clone, Default)]
pub struct FontResourceInfo {
    pub object_ref: Option<String>,
    pub subtype: Option<String>,
    pub base_font: Option<String>,
    pub encoding: Option<String>,
    pub to_unicode_ref: Option<String>,
    pub to_unicode_cmap: Option<Vec<u8>>,
}

impl LoadedPdf {
    pub fn open(path: &Path) -> Result<Self> {
        let document = Document::load(path).with_context(|| format!("open PDF {}", path.display()))?;
        Ok(Self { document })
    }

    pub fn content_streams(&self) -> Result<Vec<ContentStreamData>> {
        let mut result = Vec::new();
        for (page_num, page_id) in self.document.get_pages() {
            let page_obj = self.document.get_object(page_id)?;
            let page_dict = page_obj.as_dict()?;
            let resources = page_dict.get(b"Resources").ok().and_then(|obj| resolve_dict(&self.document, obj).ok());
            let font_resources = resources.as_ref().map(|dict| extract_font_resources(&self.document, dict)).unwrap_or_default();
            let contents = page_dict.get(b"Contents").context("page has no /Contents")?;
            for object_id in content_refs(contents) {
                let stream = self.document.get_object(object_id)?.as_stream()?;
                let decoded = stream.decompressed_content()?;
                result.push(ContentStreamData {
                    page: page_num,
                    object_id,
                    decoded,
                    resources: resources.clone(),
                    font_resources: font_resources.clone(),
                });
            }
        }
        Ok(result)
    }

    pub fn page_count(&self) -> usize {
        self.document.get_pages().len()
    }

    pub fn replace_stream_content(&mut self, object_id: ObjectId, decoded: Vec<u8>) -> Result<()> {
        let object = self.document.get_object_mut(object_id)?;
        let stream = object.as_stream_mut()?;
        stream.content = decoded;
        stream.dict.remove(b"Filter");
        stream.dict.remove(b"DecodeParms");
        stream.dict.set("Length", stream.content.len() as i64);
        Ok(())
    }

    pub fn save(&mut self, path: &Path) -> Result<()> {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        self.document.save(path).with_context(|| format!("save PDF {}", path.display()))?;
        Ok(())
    }
}

pub fn object_ref_string(id: ObjectId) -> String {
    format!("{} {} R", id.0, id.1)
}

fn content_refs(object: &Object) -> Vec<ObjectId> {
    match object {
        Object::Reference(id) => vec![*id],
        Object::Array(values) => values
            .iter()
            .filter_map(|value| match value {
                Object::Reference(id) => Some(*id),
                _ => None,
            })
            .collect(),
        _ => Vec::new(),
    }
}

fn resolve_dict(document: &Document, object: &Object) -> Result<Dictionary> {
    match object {
        Object::Dictionary(dict) => Ok(dict.clone()),
        Object::Reference(id) => Ok(document.get_object(*id)?.as_dict()?.clone()),
        _ => Err(anyhow!("object is not a dictionary")),
    }
}

fn extract_font_resources(document: &Document, resources: &Dictionary) -> BTreeMap<String, FontResourceInfo> {
    let mut result = BTreeMap::new();
    let Ok(font_obj) = resources.get(b"Font") else { return result; };
    let Ok(fonts) = resolve_dict(document, font_obj) else { return result; };
    for (name, object) in fonts.iter() {
        let name = String::from_utf8_lossy(name).to_string();
        let mut info = FontResourceInfo::default();
        let font_dict = match object {
            Object::Reference(id) => {
                info.object_ref = Some(object_ref_string(*id));
                document.get_object(*id).ok().and_then(|obj| obj.as_dict().ok()).cloned()
            }
            Object::Dictionary(dict) => Some(dict.clone()),
            _ => None,
        };
        if let Some(dict) = font_dict {
            info.subtype = dict_name(&dict, b"Subtype");
            info.base_font = dict_name(&dict, b"BaseFont");
            info.encoding = match dict.get(b"Encoding") {
                Ok(Object::Name(value)) => Some(String::from_utf8_lossy(value).to_string()),
                Ok(Object::Reference(id)) => Some(object_ref_string(*id)),
                Ok(Object::Dictionary(_)) => Some("dictionary".to_string()),
                _ => None,
            };
            info.to_unicode_ref = match dict.get(b"ToUnicode") {
                Ok(Object::Reference(id)) => Some(object_ref_string(*id)),
                Ok(Object::Stream(_)) => Some("embedded-stream".to_string()),
                _ => None,
            };
            info.to_unicode_cmap = match dict.get(b"ToUnicode") {
                Ok(Object::Reference(id)) => document
                    .get_object(*id)
                    .ok()
                    .and_then(|obj| obj.as_stream().ok())
                    .and_then(|stream| stream.decompressed_content().ok()),
                Ok(Object::Stream(stream)) => stream.decompressed_content().ok(),
                _ => None,
            };
        }
        result.insert(name, info);
    }
    result
}

fn dict_name(dict: &Dictionary, key: &[u8]) -> Option<String> {
    match dict.get(key) {
        Ok(Object::Name(value)) => Some(String::from_utf8_lossy(value).to_string()),
        _ => None,
    }
}

pub fn stream_object_mut(document: &mut Document, xref: u32) -> Result<&mut Stream> {
    let id = (xref, 0);
    Ok(document.get_object_mut(id)?.as_stream_mut()?)
}
