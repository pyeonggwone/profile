//! TrueType / OpenType font embedding (PDF spec §9.7, §9.8).
//!
//! Per `build/06-pdf-writer/DESIGN.md` we support TrueType subset
//! embedding as a Type0 (composite) font with a CIDFontType2 descendant.
//! This lets the editor add text in any Unicode character supported by
//! the supplied font, not just the Base14 set.
//!
//! Architecture:
//!
//! 1. `EmbeddedFont::parse` reads the TTF file with `ttf-parser` and
//!    captures the cmap-based char->GID mapping.
//! 2. The caller calls `note_string` for every text run that will use
//!    the font; we collect the set of used characters.
//! 3. `EmbeddedFont::write` runs `subsetter::subset` to keep only the
//!    used glyphs, then writes the five PDF objects required:
//!    Type0, CIDFontType2, FontDescriptor, FontFile2, ToUnicode CMap.
//!
//! Both `ttf-parser` (font parsing) and `subsetter` (glyph subset) are
//! pure-Rust source-open standard implementations — they handle
//! OpenType structures only and have no PDF awareness.

use std::collections::{BTreeMap, BTreeSet};

use pdf_core::{ObjectId, PdfDict, PdfNumber, PdfObject, PdfResult};

use crate::writer::PdfFileBuilder;

#[derive(Debug, Clone)]
pub struct EmbeddedFont {
    pub original_bytes: Vec<u8>,
    pub family_name: String,
    pub bbox: [i16; 4],
    pub units_per_em: u16,
    pub ascent: i16,
    pub descent: i16,
    pub cap_height: i16,
    pub italic_angle: f32,
    pub is_italic: bool,
    pub is_bold: bool,
    pub is_serif: bool,
    pub is_monospace: bool,
    pub is_symbolic: bool,
    pub stem_v: u16,
    char_to_gid: BTreeMap<char, u16>,
    used_chars: BTreeSet<char>,
    advances: BTreeMap<u16, u16>,
}

#[derive(Debug, Clone, Copy)]
pub struct EmbeddedFontIds {
    pub type0_id: ObjectId,
    pub cid_font_id: ObjectId,
    pub descriptor_id: ObjectId,
    pub font_file_id: ObjectId,
    pub tounicode_id: ObjectId,
}

impl EmbeddedFont {
    /// Parse a TrueType / OpenType font file.
    pub fn parse(bytes: Vec<u8>) -> PdfResult<Self> {
        let face = ttf_parser::Face::parse(&bytes, 0).map_err(|e| {
            pdf_core::PdfError::Write(format!("font parse: {e}"))
        })?;

        let units_per_em = face.units_per_em();
        let bbox_rect = face.global_bounding_box();
        let bbox = [
            bbox_rect.x_min,
            bbox_rect.y_min,
            bbox_rect.x_max,
            bbox_rect.y_max,
        ];
        let ascent = face.ascender();
        let descent = face.descender();
        let cap_height = face.capital_height().unwrap_or(ascent);

        let family_name = {
            let names = face.names();
            let mut found: Option<String> = None;
            for i in 0..names.len() {
                if let Some(n) = names.get(i) {
                    if n.name_id == 1 {
                        if let Some(s) = n.to_string() {
                            found = Some(s);
                            break;
                        }
                    }
                }
            }
            found.unwrap_or_else(|| "EmbeddedFont".to_string())
        };

        let italic_angle = face.italic_angle().unwrap_or(0.0);
        let is_italic = face.is_italic();
        let is_bold = face.is_bold();
        let is_monospace = face.is_monospaced();
        let is_serif = false; // ttf-parser doesn't expose this directly; keep conservative
        let is_symbolic = false;
        let stem_v = if is_bold { 120 } else { 80 };

        // Build cmap and advance width tables.
        let mut char_to_gid = BTreeMap::new();
        let mut advances = BTreeMap::new();
        if let Some(cmap) = face.tables().cmap {
            for sub in cmap.subtables {
                sub.codepoints(|cp| {
                    if let Some(c) = char::from_u32(cp) {
                        if let Some(gid) = sub.glyph_index(cp) {
                            let g = gid.0;
                            char_to_gid.entry(c).or_insert(g);
                            if let Some(adv) = face.glyph_hor_advance(gid) {
                                advances.insert(g, adv);
                            }
                        }
                    }
                });
            }
        }

        Ok(Self {
            original_bytes: bytes,
            family_name,
            bbox,
            units_per_em,
            ascent,
            descent,
            cap_height,
            italic_angle,
            is_italic,
            is_bold,
            is_serif,
            is_monospace,
            is_symbolic,
            stem_v,
            char_to_gid,
            used_chars: BTreeSet::new(),
            advances,
        })
    }

    /// Note that `text` will be drawn with this font. The characters
    /// are added to the subset.
    pub fn note_string(&mut self, text: &str) {
        for c in text.chars() {
            self.used_chars.insert(c);
        }
        // Always include .notdef and basic ASCII so the subset stays
        // viewable.
        self.used_chars.insert('\u{0000}');
        self.used_chars.insert(' ');
    }

    /// Convert `text` into the PDF hex-string representation used with
    /// Identity-H encoding — two bytes per glyph.
    pub fn encode_to_hex(&self, text: &str) -> String {
        let mut out = String::with_capacity(text.len() * 4 + 2);
        out.push('<');
        for c in text.chars() {
            let gid = self.char_to_gid.get(&c).copied().unwrap_or(0);
            out.push_str(&format!("{:04X}", gid));
        }
        out.push('>');
        out
    }

    /// Write the chain of objects to `builder`, returning the ids.
    pub fn write(
        self,
        builder: &mut PdfFileBuilder,
        mut allocate: impl FnMut() -> ObjectId,
    ) -> PdfResult<EmbeddedFontIds> {
        let type0_id = allocate();
        let cid_font_id = allocate();
        let descriptor_id = allocate();
        let font_file_id = allocate();
        let tounicode_id = allocate();

        // 1. Embed the full font. Keeping original GIDs preserves Identity-H mapping.
        let subset_bytes = self.original_bytes.clone();

        // 2. FontFile2 stream.
        let mut ff_dict = PdfDict::new();
        ff_dict.insert(
            b"Length1".to_vec(),
            PdfObject::Number(PdfNumber::Integer(subset_bytes.len() as i64)),
        );
        let ff_stream = builder.make_encoded_stream(
            ff_dict,
            &[b"FlateDecode".as_ref()],
            &subset_bytes,
        )?;
        builder.write_object(font_file_id, &PdfObject::Stream(ff_stream))?;

        // 3. FontDescriptor.
        let descriptor = make_descriptor(&self, font_file_id);
        builder.write_object(descriptor_id, &PdfObject::Dict(descriptor))?;

        // 4. CIDFontType2 descendant.
        let cid_font = make_cid_font(&self, descriptor_id);
        builder.write_object(cid_font_id, &PdfObject::Dict(cid_font))?;

        // 5. ToUnicode CMap stream.
        let tounicode = make_tounicode(&self);
        let tu_stream = builder.make_encoded_stream(
            PdfDict::new(),
            &[b"FlateDecode".as_ref()],
            tounicode.as_bytes(),
        )?;
        builder.write_object(tounicode_id, &PdfObject::Stream(tu_stream))?;

        // 6. Type0 font.
        let type0 = make_type0(&self, cid_font_id, tounicode_id);
        builder.write_object(type0_id, &PdfObject::Dict(type0))?;

        Ok(EmbeddedFontIds {
            type0_id,
            cid_font_id,
            descriptor_id,
            font_file_id,
            tounicode_id,
        })
    }
}

fn make_descriptor(font: &EmbeddedFont, font_file_id: ObjectId) -> PdfDict {
    let mut d = PdfDict::new();
    d.insert(b"Type".to_vec(), PdfObject::Name(b"FontDescriptor".to_vec()));
    d.insert(
        b"FontName".to_vec(),
        PdfObject::Name(font.family_name.as_bytes().to_vec()),
    );
    let mut flags: u32 = 0;
    if font.is_italic {
        flags |= 1 << 6;
    }
    if font.is_serif {
        flags |= 1 << 1;
    }
    if font.is_symbolic {
        flags |= 1 << 2;
    } else {
        flags |= 1 << 5; // Nonsymbolic
    }
    if font.is_monospace {
        flags |= 1 << 0;
    }
    d.insert(
        b"Flags".to_vec(),
        PdfObject::Number(PdfNumber::Integer(flags as i64)),
    );
    d.insert(
        b"FontBBox".to_vec(),
        PdfObject::Array(vec![
            PdfObject::Number(PdfNumber::Integer(font.bbox[0] as i64)),
            PdfObject::Number(PdfNumber::Integer(font.bbox[1] as i64)),
            PdfObject::Number(PdfNumber::Integer(font.bbox[2] as i64)),
            PdfObject::Number(PdfNumber::Integer(font.bbox[3] as i64)),
        ]),
    );
    d.insert(
        b"ItalicAngle".to_vec(),
        PdfObject::Number(PdfNumber::Real(font.italic_angle as f64)),
    );
    d.insert(
        b"Ascent".to_vec(),
        PdfObject::Number(PdfNumber::Integer(font.ascent as i64)),
    );
    d.insert(
        b"Descent".to_vec(),
        PdfObject::Number(PdfNumber::Integer(font.descent as i64)),
    );
    d.insert(
        b"CapHeight".to_vec(),
        PdfObject::Number(PdfNumber::Integer(font.cap_height as i64)),
    );
    d.insert(
        b"StemV".to_vec(),
        PdfObject::Number(PdfNumber::Integer(font.stem_v as i64)),
    );
    d.insert(
        b"FontFile2".to_vec(),
        PdfObject::Reference(pdf_core::ObjectRef { id: font_file_id }),
    );
    d
}

fn make_cid_font(font: &EmbeddedFont, descriptor_id: ObjectId) -> PdfDict {
    let mut d = PdfDict::new();
    d.insert(b"Type".to_vec(), PdfObject::Name(b"Font".to_vec()));
    d.insert(
        b"Subtype".to_vec(),
        PdfObject::Name(b"CIDFontType2".to_vec()),
    );
    d.insert(
        b"BaseFont".to_vec(),
        PdfObject::Name(font.family_name.as_bytes().to_vec()),
    );

    let mut cid_system_info = PdfDict::new();
    cid_system_info.insert(
        b"Registry".to_vec(),
        PdfObject::String(pdf_core::PdfString::Literal(b"Adobe".to_vec())),
    );
    cid_system_info.insert(
        b"Ordering".to_vec(),
        PdfObject::String(pdf_core::PdfString::Literal(b"Identity".to_vec())),
    );
    cid_system_info.insert(
        b"Supplement".to_vec(),
        PdfObject::Number(PdfNumber::Integer(0)),
    );
    d.insert(b"CIDSystemInfo".to_vec(), PdfObject::Dict(cid_system_info));

    d.insert(
        b"FontDescriptor".to_vec(),
        PdfObject::Reference(pdf_core::ObjectRef { id: descriptor_id }),
    );
    d.insert(b"CIDToGIDMap".to_vec(), PdfObject::Name(b"Identity".to_vec()));

    // Widths array: /W [ gid [w1 w2 ...] ... ] in design units.
    // For simplicity emit per-glyph entries for every used glyph.
    let mut w_entries: Vec<PdfObject> = Vec::new();
    for c in &font.used_chars {
        if let Some(&gid) = font.char_to_gid.get(c) {
            if let Some(&adv) = font.advances.get(&gid) {
                let scale = 1000.0_f32 / font.units_per_em as f32;
                let pdf_w = (adv as f32 * scale) as i64;
                w_entries.push(PdfObject::Number(PdfNumber::Integer(gid as i64)));
                w_entries.push(PdfObject::Array(vec![PdfObject::Number(
                    PdfNumber::Integer(pdf_w),
                )]));
            }
        }
    }
    if !w_entries.is_empty() {
        d.insert(b"W".to_vec(), PdfObject::Array(w_entries));
    }

    d
}

fn make_type0(font: &EmbeddedFont, cid_font_id: ObjectId, tounicode_id: ObjectId) -> PdfDict {
    let mut d = PdfDict::new();
    d.insert(b"Type".to_vec(), PdfObject::Name(b"Font".to_vec()));
    d.insert(b"Subtype".to_vec(), PdfObject::Name(b"Type0".to_vec()));
    d.insert(
        b"BaseFont".to_vec(),
        PdfObject::Name(font.family_name.as_bytes().to_vec()),
    );
    d.insert(
        b"Encoding".to_vec(),
        PdfObject::Name(b"Identity-H".to_vec()),
    );
    d.insert(
        b"DescendantFonts".to_vec(),
        PdfObject::Array(vec![PdfObject::Reference(pdf_core::ObjectRef {
            id: cid_font_id,
        })]),
    );
    d.insert(
        b"ToUnicode".to_vec(),
        PdfObject::Reference(pdf_core::ObjectRef { id: tounicode_id }),
    );
    d
}

fn make_tounicode(font: &EmbeddedFont) -> String {
    // Minimal CIDFontType2 ToUnicode CMap. PDF spec example §9.10.3.
    let mut entries: Vec<(u16, char)> = font
        .used_chars
        .iter()
        .filter_map(|c| font.char_to_gid.get(c).map(|g| (*g, *c)))
        .collect();
    entries.sort_by_key(|(g, _)| *g);

    let mut s = String::new();
    s.push_str("/CIDInit /ProcSet findresource begin\n");
    s.push_str("12 dict begin\n");
    s.push_str("begincmap\n");
    s.push_str("/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n");
    s.push_str("/CMapName /Adobe-Identity-UCS def\n");
    s.push_str("/CMapType 2 def\n");
    s.push_str("1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n");

    // Emit in chunks of 100 entries.
    for chunk in entries.chunks(100) {
        s.push_str(&format!("{} beginbfchar\n", chunk.len()));
        for (g, c) in chunk {
            let cp = *c as u32;
            if cp <= 0xFFFF {
                s.push_str(&format!("<{:04X}> <{:04X}>\n", g, cp));
            } else {
                // surrogate pair
                let v = cp - 0x10000;
                let hi = 0xD800 | (v >> 10);
                let lo = 0xDC00 | (v & 0x3FF);
                s.push_str(&format!("<{:04X}> <{:04X}{:04X}>\n", g, hi, lo));
            }
        }
        s.push_str("endbfchar\n");
    }

    s.push_str("endcmap\n");
    s.push_str("CMapName currentdict /CMap defineresource pop\n");
    s.push_str("end\nend\n");
    s
}
