use anyhow::{Context, Result};
use pdf_core::LoadedPdf;
use pdf_models::{ByteRange, PdfInputTextState, RebuildReport, ReportIssue};
use std::collections::BTreeMap;
use std::path::Path;

struct Replacement {
    id: String,
    range: ByteRange,
    replacement: Vec<u8>,
}

pub fn rebuild_pdf(source: &Path, input: &PdfInputTextState, output: &Path) -> Result<RebuildReport> {
    let mut pdf = LoadedPdf::open(source)?;
    let mut streams: BTreeMap<u32, Vec<u8>> = BTreeMap::new();
    for stream in pdf.content_streams()? {
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
        if range.end > content.len() || range.start >= range.end {
            report.ok = false;
            report.failed.push(issue(Some(run.id.clone()), "REBUILD_RANGE_OUT_OF_BOUNDS", "operandRange out of bounds"));
            continue;
        }
        if &content[range.start..range.end] != original {
            report.ok = false;
            report.failed.push(issue(Some(run.id.clone()), "REBUILD_RANGE_MISMATCH", "encodedOriginal mismatch at operandRange"));
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
    if report.ok || report.replaced > 0 {
        pdf.save(output)?;
    }
    Ok(report)
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
