//! Page-level text extraction.
//!
//! Walks the tokenized content stream, maintains a small text-state
//! machine and emits `TextRun` records with PDF user-space coordinates.
//! When the current font has a `/ToUnicode` CMap we decode source
//! bytes through it; otherwise we fall back to PDFDocEncoding /
//! WinAnsi (Latin-1 passthrough).

use std::collections::HashMap;

use pdf_core::{PdfObject, PdfResult, PdfString};
use pdf_reader::{PageInfo, ParsedPdf};

use crate::cmap::ToUnicodeCMap;
use crate::content_tokens::{tokenize, ContentInstruction};

#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone)]
#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
pub struct TextRun {
    pub text: String,
    pub x: f32,
    pub y: f32,
    pub font_size: f32,
    pub font_resource: Option<String>,
}

#[derive(Debug, Clone, Default)]
#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
pub struct PageText {
    pub page: u32,
    pub width: f32,
    pub height: f32,
    pub runs: Vec<TextRun>,
}

pub fn extract_text(doc: &ParsedPdf) -> PdfResult<Vec<PageText>> {
    let pages = doc.page_tree()?;
    let mut out = Vec::with_capacity(pages.pages.len());
    for (idx, page) in pages.pages.iter().enumerate() {
        out.push(extract_page(doc, idx as u32 + 1, page)?);
    }
    Ok(out)
}

fn extract_page(doc: &ParsedPdf, page_number: u32, page: &PageInfo) -> PdfResult<PageText> {
    let mut content_bytes = Vec::new();
    for cid in &page.content_object_ids {
        if let Some(PdfObject::Stream(s)) = doc.lookup(*cid) {
            let decoded = pdf_filters::decode_stream(&s.dict, &s.raw_data)?;
            content_bytes.extend_from_slice(&decoded.bytes);
            content_bytes.push(b'\n');
        }
    }
    let cmaps = build_font_cmaps(doc, page);
    let instructions = tokenize(&content_bytes);
    let runs = run_text_state_machine(&instructions, &cmaps);

    let (width, height) = page
        .media_box
        .map(|mb| ((mb[2] - mb[0]) as f32, (mb[3] - mb[1]) as f32))
        .unwrap_or((612.0, 792.0));

    Ok(PageText {
        page: page_number,
        width,
        height,
        runs,
    })
}

/// For each font resource on this page, resolve its `/ToUnicode` stream
/// (if any) and parse it into a `ToUnicodeCMap`.
fn build_font_cmaps(
    doc: &ParsedPdf,
    page: &PageInfo,
) -> HashMap<String, ToUnicodeCMap> {
    let mut out = HashMap::new();
    let resources = match &page.resources {
        Some(r) => r,
        None => return out,
    };
    let fonts = match resources.get(b"Font".as_ref()) {
        Some(PdfObject::Dict(d)) => d,
        _ => return out,
    };
    for (name, value) in fonts {
        let font_dict = match value {
            PdfObject::Reference(r) => match doc.lookup(r.id).and_then(PdfObject::as_dict) {
                Some(d) => d,
                None => continue,
            },
            PdfObject::Dict(d) => d,
            _ => continue,
        };
        let to_unicode_ref = match font_dict.get(b"ToUnicode".as_ref()) {
            Some(PdfObject::Reference(r)) => *r,
            _ => continue,
        };
        let stream = match doc.lookup(to_unicode_ref.id) {
            Some(PdfObject::Stream(s)) => s,
            _ => continue,
        };
        let decoded = match pdf_filters::decode_stream(&stream.dict, &stream.raw_data) {
            Ok(d) => d,
            Err(_) => continue,
        };
        let cmap = ToUnicodeCMap::parse(&decoded.bytes);
        out.insert(String::from_utf8_lossy(name).into_owned(), cmap);
    }
    out
}

#[derive(Default, Clone, Copy)]
struct Mat {
    a: f32,
    b: f32,
    c: f32,
    d: f32,
    e: f32,
    f: f32,
}

impl Mat {
    fn identity() -> Self {
        Self {
            a: 1.0,
            b: 0.0,
            c: 0.0,
            d: 1.0,
            e: 0.0,
            f: 0.0,
        }
    }

    fn mul(self, other: Mat) -> Mat {
        Mat {
            a: self.a * other.a + self.b * other.c,
            b: self.a * other.b + self.b * other.d,
            c: self.c * other.a + self.d * other.c,
            d: self.c * other.b + self.d * other.d,
            e: self.e * other.a + self.f * other.c + other.e,
            f: self.e * other.b + self.f * other.d + other.f,
        }
    }

    fn transform(&self, x: f32, y: f32) -> (f32, f32) {
        (self.a * x + self.c * y + self.e, self.b * x + self.d * y + self.f)
    }
}

#[derive(Default)]
struct TextState {
    tm: Mat,    // text matrix
    tlm: Mat,   // text line matrix
    font_size: f32,
    font_resource: Option<String>,
    in_text: bool,
}

fn op_num(operands: &[PdfObject], idx: usize) -> Option<f32> {
    operands
        .get(idx)
        .and_then(|o| o.as_number())
        .map(|n| n.as_f64() as f32)
}

fn run_text_state_machine(
    instructions: &[ContentInstruction],
    cmaps: &HashMap<String, ToUnicodeCMap>,
) -> Vec<TextRun> {
    let mut runs = Vec::new();
    let mut ctm_stack: Vec<Mat> = vec![Mat::identity()];
    let mut text = TextState::default();

    for instr in instructions {
        let op = instr.operator.as_slice();
        let ops = &instr.operands;
        match op {
            b"q" => ctm_stack.push(*ctm_stack.last().unwrap()),
            b"Q" => {
                if ctm_stack.len() > 1 {
                    ctm_stack.pop();
                }
            }
            b"cm" => {
                if ops.len() == 6 {
                    let m = Mat {
                        a: op_num(ops, 0).unwrap_or(1.0),
                        b: op_num(ops, 1).unwrap_or(0.0),
                        c: op_num(ops, 2).unwrap_or(0.0),
                        d: op_num(ops, 3).unwrap_or(1.0),
                        e: op_num(ops, 4).unwrap_or(0.0),
                        f: op_num(ops, 5).unwrap_or(0.0),
                    };
                    let top = ctm_stack.last_mut().unwrap();
                    *top = m.mul(*top);
                }
            }
            b"BT" => {
                text.in_text = true;
                text.tm = Mat::identity();
                text.tlm = Mat::identity();
            }
            b"ET" => {
                text.in_text = false;
            }
            b"Tf" => {
                if let Some(PdfObject::Name(n)) = ops.first() {
                    text.font_resource = Some(String::from_utf8_lossy(n).into_owned());
                }
                text.font_size = op_num(ops, 1).unwrap_or(text.font_size);
            }
            b"Tm" => {
                if ops.len() == 6 {
                    let m = Mat {
                        a: op_num(ops, 0).unwrap_or(1.0),
                        b: op_num(ops, 1).unwrap_or(0.0),
                        c: op_num(ops, 2).unwrap_or(0.0),
                        d: op_num(ops, 3).unwrap_or(1.0),
                        e: op_num(ops, 4).unwrap_or(0.0),
                        f: op_num(ops, 5).unwrap_or(0.0),
                    };
                    text.tm = m;
                    text.tlm = m;
                }
            }
            b"Td" | b"TD" => {
                let tx = op_num(ops, 0).unwrap_or(0.0);
                let ty = op_num(ops, 1).unwrap_or(0.0);
                let translate = Mat {
                    a: 1.0,
                    b: 0.0,
                    c: 0.0,
                    d: 1.0,
                    e: tx,
                    f: ty,
                };
                text.tlm = translate.mul(text.tlm);
                text.tm = text.tlm;
            }
            b"T*" => {
                // Move to start of next line: T* = 0 -leading Td
                let translate = Mat {
                    a: 1.0,
                    b: 0.0,
                    c: 0.0,
                    d: 1.0,
                    e: 0.0,
                    f: -text.font_size,
                };
                text.tlm = translate.mul(text.tlm);
                text.tm = text.tlm;
            }
            b"Tj" | b"'" | b"\"" => {
                if let Some(s) = ops
                    .first()
                    .and_then(|o| match o {
                        PdfObject::String(s) => Some(decode_pdf_string(s, &text, cmaps)),
                        _ => None,
                    })
                {
                    emit_text_run(&mut runs, &ctm_stack, &text, &s);
                }
            }
            b"TJ" => {
                if let Some(PdfObject::Array(arr)) = ops.first() {
                    let mut buf = String::new();
                    for item in arr {
                        if let PdfObject::String(s) = item {
                            buf.push_str(&decode_pdf_string(s, &text, cmaps));
                        }
                    }
                    if !buf.is_empty() {
                        emit_text_run(&mut runs, &ctm_stack, &text, &buf);
                    }
                }
            }
            _ => {}
        }
    }
    runs
}

fn emit_text_run(runs: &mut Vec<TextRun>, ctm_stack: &[Mat], text: &TextState, s: &str) {
    let ctm = ctm_stack.last().copied().unwrap_or_else(Mat::identity);
    let combined = text.tm.mul(ctm);
    let (x, y) = combined.transform(0.0, 0.0);
    runs.push(TextRun {
        text: s.to_string(),
        x,
        y,
        font_size: if text.font_size != 0.0 {
            text.font_size
        } else {
            12.0
        },
        font_resource: text.font_resource.clone(),
    });
}

fn decode_pdf_string(
    s: &PdfString,
    text: &TextState,
    cmaps: &HashMap<String, ToUnicodeCMap>,
) -> String {
    let bytes = s.bytes();
    if let Some(font) = text.font_resource.as_deref() {
        if let Some(cmap) = cmaps.get(font) {
            return cmap.decode_bytes(bytes);
        }
    }
    // Detect UTF-16BE BOM
    if bytes.len() >= 2 && bytes[0] == 0xFE && bytes[1] == 0xFF {
        let mut out = String::new();
        let mut i = 2;
        while i + 1 < bytes.len() {
            let code = ((bytes[i] as u16) << 8) | bytes[i + 1] as u16;
            if let Some(c) = char::from_u32(code as u32) {
                out.push(c);
            }
            i += 2;
        }
        return out;
    }
    // WinAnsi / PDFDocEncoding fallback (mostly identical to Latin-1).
    bytes.iter().map(|&b| b as char).collect()
}
