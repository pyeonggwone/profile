use anyhow::{Context, Result};
use pdf_core::LoadedPdf;
use pdf_models::{ByteRange, PdfInputTextState, RebuildReport, ReportIssue};
use lopdf::{Dictionary, Object, ObjectId, Stream};
use std::collections::BTreeMap;
use std::fs;
use std::path::Path;

struct Replacement {
    id: String,
    range: ByteRange,
    replacement: Vec<u8>,
}

pub fn rebuild_pdf(source: &Path, input: &PdfInputTextState, output: &Path) -> Result<RebuildReport> {
    let mut pdf = LoadedPdf::open(source)?;
    let mut streams: BTreeMap<u32, Vec<u8>> = BTreeMap::new();
    let mut stream_pages: BTreeMap<u32, u32> = BTreeMap::new();
    for stream in pdf.content_streams()? {
        stream_pages.insert(stream.object_id.0, stream.page);
        streams.insert(stream.object_id.0, stream.decoded);
    }

    let mut report = RebuildReport { ok: true, replaced: 0, failed: Vec::new() };
    let mut replacements: BTreeMap<u32, Vec<Replacement>> = BTreeMap::new();
    for run in &input.text_runs {
        let xref = run.restore_options.stream_xref;
        let Some(content) = streams.get(&xref) else {
            report.ok = false;
            report.failed.push(issue(Some(run.id.clone()), "REBUILD_STREAM_NOT_FOUND", format!("stream {xref} not found")));
            continue;
        };
        let range = &run.restore_options.operand_range;
        let original = run.text_payload.encoded_original.as_bytes();
        let replacement = match &run.text_payload.replacement_encoded {
            Some(value) => value.as_bytes(),
            None => {
                report.ok = false;
                report.failed.push(issue(Some(run.id.clone()), "REPLACEMENT_ENCODED_MISSING", "replacementEncoded missing"));
                continue;
            }
        };
        if replacement == original {
            continue;
        }
        if range.end > content.len() || range.start >= range.end {
            report.ok = false;
            report.failed.push(issue(Some(run.id.clone()), "REBUILD_RANGE_OUT_OF_BOUNDS", "operandRange out of bounds"));
            continue;
        }
        if &content[range.start..range.end] != original {
            if preserve_mismatch_as_original() {
                report.failed.push(warning(Some(run.id.clone()), "REBUILD_RANGE_MISMATCH_PRESERVED_ORIGINAL", "encodedOriginal mismatch at operandRange; replacement skipped to preserve original PDF bytes"));
            } else {
                report.ok = false;
                report.failed.push(issue(Some(run.id.clone()), "REBUILD_RANGE_MISMATCH", "encodedOriginal mismatch at operandRange"));
            }
            continue;
        }
        replacements.entry(xref).or_default().push(Replacement {
            id: run.id.clone(),
            range: range.clone(),
            replacement: replacement.to_vec(),
        });
    }

    for (xref, mut stream_replacements) in replacements {
        let Some(content) = streams.get_mut(&xref) else {
            report.ok = false;
            report.failed.push(issue(None, "REBUILD_STREAM_NOT_FOUND", format!("stream {xref} not found before replacement")));
            continue;
        };
        stream_replacements.sort_by(|left, right| right.range.start.cmp(&left.range.start));
        for replacement in stream_replacements {
            if replacement.range.end > content.len() || replacement.range.start >= replacement.range.end {
                report.ok = false;
                report.failed.push(issue(Some(replacement.id), "REBUILD_RANGE_OUT_OF_BOUNDS", "operandRange out of bounds after sorting"));
                continue;
            }
            content.splice(replacement.range.start..replacement.range.end, replacement.replacement.iter().copied());
            report.replaced += 1;
        }
    }

    for (xref, decoded) in streams {
        pdf.replace_stream_content((xref, 0), decoded)
            .with_context(|| format!("replace stream {xref}"))?;
    }
    if translation_render_mode() == "overlay" {
        add_korean_overlay(&mut pdf, input, &stream_pages, &mut report)?;
    }
    if report.ok || report.replaced > 0 {
        pdf.save(output)?;
    }
    Ok(report)
}

fn add_korean_overlay(pdf: &mut LoadedPdf, input: &PdfInputTextState, stream_pages: &BTreeMap<u32, u32>, report: &mut RebuildReport) -> Result<()> {
    let Some(font_path) = overlay_font_path() else {
        report.ok = false;
        report.failed.push(issue(None, "OVERLAY_FONT_MISSING", "PDF_TRANSLATION_RENDER_MODE=overlay requires FONT_REGULAR, FONT_FALLBACK, or FONT_BOLD"));
        return Ok(());
    };
    let font_ref = install_overlay_font(pdf, &font_path)?;
    let mut overlays: BTreeMap<u32, Vec<String>> = BTreeMap::new();
    for run in &input.text_runs {
        let original = run.text_payload.decoded_original.as_deref().unwrap_or_default();
        let translated = run.text_payload.decoded_translated.as_deref().unwrap_or_default();
        if translated.trim().is_empty() || translated == original {
            continue;
        }
        let Some(page) = stream_pages.get(&run.restore_options.stream_xref).copied() else {
            report.failed.push(warning(Some(run.id.clone()), "OVERLAY_PAGE_NOT_FOUND", "content stream page not found for overlay"));
            continue;
        };
        let Some(matrix) = run.restore_options.text_state.text_matrix else {
            report.failed.push(warning(Some(run.id.clone()), "OVERLAY_TEXT_MATRIX_MISSING", "text matrix missing; overlay skipped"));
            continue;
        };
        let font_size = run.restore_options.text_state.font_size.unwrap_or_else(default_overlay_font_size).max(1.0);
        overlays.entry(page).or_default().push(overlay_text_command(matrix[4], matrix[5], font_size, translated));
    }
    let pages = pdf.document.get_pages();
    for (page, commands) in overlays {
        let Some(page_id) = pages.get(&page).copied() else { continue; };
        add_font_resource(&mut pdf.document, page_id, font_ref)?;
        append_overlay_stream(&mut pdf.document, page_id, commands.join("\n").into_bytes())?;
    }
    Ok(())
}

fn install_overlay_font(pdf: &mut LoadedPdf, font_path: &Path) -> Result<ObjectId> {
    let font_bytes = fs::read(font_path).with_context(|| format!("read overlay font {}", font_path.display()))?;
    let face = ttf_parser::Face::parse(&font_bytes, 0).map_err(|err| anyhow::anyhow!("parse overlay font {}: {err:?}", font_path.display()))?;
    let bbox = face.global_bounding_box();
    let units = face.units_per_em() as f64;
    let scale = 1000.0 / units;
    let font_bbox = vec![real(bbox.x_min as f64 * scale), real(bbox.y_min as f64 * scale), real(bbox.x_max as f64 * scale), real(bbox.y_max as f64 * scale)];
    let ascent = real(face.ascender() as f64 * scale);
    let descent = real(face.descender() as f64 * scale);
    let cap_height = real(face.ascender() as f64 * scale);
    let cid_to_gid = cid_to_gid_map(&face);

    let font_file_ref = pdf.document.add_object(Stream::new(dict_with_length1(font_bytes.len()), font_bytes));
    let mut descriptor = Dictionary::new();
    descriptor.set("Type", Object::Name(b"FontDescriptor".to_vec()));
    descriptor.set("FontName", Object::Name(b"KoreanOverlayFont".to_vec()));
    descriptor.set("Flags", 4);
    descriptor.set("FontBBox", font_bbox);
    descriptor.set("ItalicAngle", 0);
    descriptor.set("Ascent", ascent);
    descriptor.set("Descent", descent);
    descriptor.set("CapHeight", cap_height);
    descriptor.set("StemV", 80);
    descriptor.set("FontFile2", Object::Reference(font_file_ref));
    let descriptor_ref = pdf.document.add_object(Object::Dictionary(descriptor));

    let cid_to_gid_ref = pdf.document.add_object(Stream::new(Dictionary::new(), cid_to_gid));
    let mut cid_system = Dictionary::new();
    cid_system.set("Registry", Object::string_literal("Adobe"));
    cid_system.set("Ordering", Object::string_literal("Identity"));
    cid_system.set("Supplement", 0);

    let mut cid_font = Dictionary::new();
    cid_font.set("Type", Object::Name(b"Font".to_vec()));
    cid_font.set("Subtype", Object::Name(b"CIDFontType2".to_vec()));
    cid_font.set("BaseFont", Object::Name(b"KoreanOverlayFont".to_vec()));
    cid_font.set("CIDSystemInfo", Object::Dictionary(cid_system));
    cid_font.set("FontDescriptor", Object::Reference(descriptor_ref));
    cid_font.set("CIDToGIDMap", Object::Reference(cid_to_gid_ref));
    cid_font.set("DW", 1000);
    let cid_font_ref = pdf.document.add_object(Object::Dictionary(cid_font));

    let mut type0 = Dictionary::new();
    type0.set("Type", Object::Name(b"Font".to_vec()));
    type0.set("Subtype", Object::Name(b"Type0".to_vec()));
    type0.set("BaseFont", Object::Name(b"KoreanOverlayFont".to_vec()));
    type0.set("Encoding", Object::Name(b"Identity-H".to_vec()));
    type0.set("DescendantFonts", vec![Object::Reference(cid_font_ref)]);
    Ok(pdf.document.add_object(Object::Dictionary(type0)))
}

fn cid_to_gid_map(face: &ttf_parser::Face<'_>) -> Vec<u8> {
    let mut output = Vec::with_capacity(usize::from(u16::MAX) * 2 + 2);
    for cid in 0..=u16::MAX {
        let glyph = char::from_u32(u32::from(cid)).and_then(|value| face.glyph_index(value)).map(|gid| gid.0).unwrap_or(0);
        output.push((glyph >> 8) as u8);
        output.push((glyph & 0xff) as u8);
    }
    output
}

fn add_font_resource(document: &mut lopdf::Document, page_id: ObjectId, font_ref: ObjectId) -> Result<()> {
    let resources = document
        .get_object(page_id)
        .with_context(|| format!("read page object {:?} for overlay resources", page_id))?
        .as_dict()
        .with_context(|| format!("page object {:?} is not a dictionary", page_id))?
        .get(b"Resources")
        .ok()
        .and_then(|object| clone_dict(document, object).ok())
        .unwrap_or_default();
    let mut resources = resources;
    let mut fonts = resources
        .get(b"Font")
        .ok()
        .and_then(|object| clone_dict(document, object).ok())
        .unwrap_or_default();
    fonts.set("FKoOverlay", Object::Reference(font_ref));
    resources.set("Font", Object::Dictionary(fonts));
    document
        .get_object_mut(page_id)
        .with_context(|| format!("update page object {:?} overlay resources", page_id))?
        .as_dict_mut()
        .with_context(|| format!("page object {:?} is not a mutable dictionary", page_id))?
        .set("Resources", Object::Dictionary(resources));
    Ok(())
}

fn append_overlay_stream(document: &mut lopdf::Document, page_id: ObjectId, content: Vec<u8>) -> Result<()> {
    let stream_ref = document.add_object(Stream::new(Dictionary::new(), content));
    let contents = document
        .get_object(page_id)
        .with_context(|| format!("read page object {:?} for overlay contents", page_id))?
        .as_dict()
        .with_context(|| format!("page object {:?} is not a dictionary", page_id))?
        .get(b"Contents")
        .ok()
        .cloned();
    let new_contents = match contents {
        Some(Object::Array(mut values)) => {
            values.push(Object::Reference(stream_ref));
            Object::Array(values)
        }
        Some(Object::Reference(existing)) => Object::Array(vec![Object::Reference(existing), Object::Reference(stream_ref)]),
        Some(other) => Object::Array(vec![other, Object::Reference(stream_ref)]),
        None => Object::Reference(stream_ref),
    };
    document
        .get_object_mut(page_id)
        .with_context(|| format!("update page object {:?} overlay contents", page_id))?
        .as_dict_mut()
        .with_context(|| format!("page object {:?} is not a mutable dictionary", page_id))?
        .set("Contents", new_contents);
    Ok(())
}

fn clone_dict(document: &lopdf::Document, object: &Object) -> Result<Dictionary> {
    match object {
        Object::Dictionary(dict) => Ok(dict.clone()),
        Object::Reference(id) => Ok(document
            .get_object(*id)
            .with_context(|| format!("read referenced resource dictionary {:?}", id))?
            .as_dict()
            .with_context(|| format!("referenced resource object {:?} is not a dictionary", id))?
            .clone()),
        _ => Ok(Dictionary::new()),
    }
}

fn overlay_text_command(x: f64, y: f64, font_size: f64, text: &str) -> String {
    format!("q BT /FKoOverlay {:.3} Tf 0 0 0 rg 1 0 0 1 {:.3} {:.3} Tm <{}> Tj ET Q", font_size, x, y, utf16be_hex(text))
}

fn utf16be_hex(text: &str) -> String {
    let mut output = String::new();
    for unit in text.encode_utf16() {
        output.push_str(&format!("{unit:04X}"));
    }
    output
}

fn overlay_font_path() -> Option<std::path::PathBuf> {
    ["FONT_REGULAR", "FONT_FALLBACK", "FONT_BOLD"]
        .into_iter()
        .filter_map(|key| std::env::var(key).ok())
        .map(|value| std::path::PathBuf::from(value.trim()))
        .find(|path| path.exists())
}

fn dict_with_length1(length: usize) -> Dictionary {
    let mut dict = Dictionary::new();
    dict.set("Length1", length as i64);
    dict
}

fn real(value: f64) -> Object {
    Object::Real(value as f32)
}

fn default_overlay_font_size() -> f64 {
    std::env::var("LAYOUT_DEFAULT_FONT_SIZE").ok().and_then(|value| value.parse().ok()).unwrap_or(10.0)
}

fn translation_render_mode() -> String {
    std::env::var("PDF_TRANSLATION_RENDER_MODE").unwrap_or_else(|_| "overlay".to_string()).trim().to_ascii_lowercase()
}

fn issue(id: Option<String>, code: &str, message: impl Into<String>) -> ReportIssue {
    ReportIssue {
        id,
        stage: Some("rebuild".to_string()),
        code: code.to_string(),
        severity: "error".to_string(),
        message: message.into(),
        recoverable: true,
    }
}

fn warning(id: Option<String>, code: &str, message: impl Into<String>) -> ReportIssue {
    ReportIssue {
        id,
        stage: Some("rebuild".to_string()),
        code: code.to_string(),
        severity: "warning".to_string(),
        message: message.into(),
        recoverable: true,
    }
}

fn preserve_mismatch_as_original() -> bool {
    std::env::var("REBUILD_MISMATCH_POLICY")
        .ok()
        .map(|value| value.trim().eq_ignore_ascii_case("preserve-original"))
        .unwrap_or(true)
}
