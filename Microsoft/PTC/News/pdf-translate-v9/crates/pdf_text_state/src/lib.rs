use anyhow::Result;
use lopdf::Dictionary;
use pdf_core::{FontResourceInfo, LoadedPdf};
use pdf_models::*;
use std::collections::BTreeMap;
use std::path::Path;

#[derive(Debug, Clone)]
struct Token {
    text: String,
    start: usize,
    end: usize,
}

pub fn extract_raw_text_state(source: &Path) -> Result<RawPdfTextState> {
    let pdf = LoadedPdf::open(source)?;
    let mut pages = Vec::new();
    for stream in pdf.content_streams()? {
        let text_runs = parse_stream(stream.page, stream.object_id.0, &stream.decoded, stream.resources.as_ref(), &stream.font_resources);
        pages.push(RawPage {
            page: stream.page,
            contents: vec![RawContentStream {
                stream_xref: stream.object_id.0,
                text_runs,
            }],
        });
    }
    Ok(RawPdfTextState { pages })
}

fn parse_stream(page: u32, stream_xref: u32, bytes: &[u8], resources: Option<&Dictionary>, fonts: &BTreeMap<String, FontResourceInfo>) -> Vec<RawTextRun> {
    let tokens = tokenize(bytes);
    let block_ranges = text_block_ranges(&tokens);
    let mut state = TextState::default();
    let mut state_stack: Vec<TextState> = Vec::new();
    let mut sequence: Vec<OperatorSnapshot> = Vec::new();
    let mut runs = Vec::new();
    let mut counter = 1;
    for index in 0..tokens.len() {
        let op = tokens[index].text.as_str();
        match op {
            "BT" | "ET" => sequence.push(OperatorSnapshot { op: op.to_string(), font: None, size: None, matrix: None }),
            "q" => state_stack.push(state.clone()),
            "Q" => {
                if let Some(previous) = state_stack.pop() {
                    state = previous;
                }
            }
            "Tf" if index >= 2 => {
                state.font = Some(normalize_resource_name(&tokens[index - 2].text));
                state.font_size = tokens[index - 1].text.parse::<f64>().ok();
                sequence.push(OperatorSnapshot { op: "Tf".to_string(), font: state.font.clone(), size: state.font_size, matrix: None });
            }
            "Tm" if index >= 6 => {
                let matrix = parse_matrix(&tokens[index - 6..index]);
                state.text_matrix = matrix;
                state.line_matrix = matrix;
                sequence.push(OperatorSnapshot { op: "Tm".to_string(), font: None, size: None, matrix });
            }
            "Tc" if index >= 1 => state.char_spacing = tokens[index - 1].text.parse().unwrap_or(state.char_spacing),
            "Tw" if index >= 1 => state.word_spacing = tokens[index - 1].text.parse().unwrap_or(state.word_spacing),
            "Tz" if index >= 1 => state.horizontal_scaling = tokens[index - 1].text.parse().unwrap_or(state.horizontal_scaling),
            "TL" if index >= 1 => state.leading = tokens[index - 1].text.parse().unwrap_or(state.leading),
            "Tr" if index >= 1 => state.render_mode = tokens[index - 1].text.parse().unwrap_or(state.render_mode),
            "Ts" if index >= 1 => state.rise = tokens[index - 1].text.parse().unwrap_or(state.rise),
            "Td" if index >= 2 => apply_text_move(&mut state, tokens[index - 2].text.parse().unwrap_or(0.0), tokens[index - 1].text.parse().unwrap_or(0.0)),
            "TD" if index >= 2 => {
                state.leading = -tokens[index - 1].text.parse::<f64>().unwrap_or(-state.leading);
                apply_text_move(&mut state, tokens[index - 2].text.parse().unwrap_or(0.0), tokens[index - 1].text.parse().unwrap_or(0.0));
            }
            "T*" => {
                let leading = state.leading;
                apply_text_move(&mut state, 0.0, -leading);
            }
            "Tj" | "'" | "\"" if index >= 1 => {
                let operand = tokens[index - 1].clone();
                runs.push(make_run(page, stream_xref, counter, op, operand, block_ranges[index].clone(), &sequence, &state, resources, fonts));
                counter += 1;
            }
            "TJ" if index >= 1 => {
                let operand = tokens[index - 1].clone();
                runs.push(make_run(page, stream_xref, counter, op, operand, block_ranges[index].clone(), &sequence, &state, resources, fonts));
                counter += 1;
            }
            _ => {}
        }
    }
    runs
}

fn make_run(
    page: u32,
    stream_xref: u32,
    counter: usize,
    operator: &str,
    operand: Token,
    text_block_range: Option<ByteRange>,
    sequence: &[OperatorSnapshot],
    state: &TextState,
    _resources: Option<&Dictionary>,
    fonts: &BTreeMap<String, FontResourceInfo>,
) -> RawTextRun {
    let font_state = state.font.as_ref().and_then(|font| fonts.get(font).map(|info| font_state_from_info(font, info))).unwrap_or_else(|| FontState {
        resource_name: state.font.clone(),
        font_object_ref: None,
        subtype: None,
        base_font: None,
        encoding: None,
        to_unicode_ref: None,
    });
    let (decoded, _, _) = decode_operand_with_font(&operand.text, state.font.as_ref().and_then(|font| fonts.get(font)));
    RawTextRun {
        id: format!("p{page:04}-s{stream_xref:04}-r{counter:05}"),
        restore_options: RestoreOptions {
            stream_xref,
            operator: operator.to_string(),
            operand_range: ByteRange { start: operand.start, end: operand.end },
            text_block_range,
            operator_sequence: sequence.to_vec(),
            text_state: state.clone(),
            font_state,
        },
        text_payload: TextPayload {
            encoded_original: operand.text,
            decoded_original: decoded,
            decoded_translated: None,
            replacement_encoded: None,
        },
    }
}

fn decode_operand_with_font(encoded: &str, font: Option<&FontResourceInfo>) -> (Option<String>, String, Vec<String>) {
    let decoded = pdf_cmap::decode_pdf_operand(encoded);
    if decoded.0.is_some() {
        return decoded;
    }
    let Some(cmap_bytes) = font.and_then(|info| info.to_unicode_cmap.as_ref()) else {
        return decoded;
    };
    match pdf_cmap::parse_to_unicode_cmap(cmap_bytes) {
        Ok(cmap) => {
            let result = pdf_cmap::decode_with_cmap(encoded, &cmap);
            (result.text, result.method, result.issues)
        }
        Err(err) => (decoded.0, decoded.1, vec![format!("ToUnicode CMap parse failed: {err}")]),
    }
}

fn text_block_ranges(tokens: &[Token]) -> Vec<Option<ByteRange>> {
    let mut ranges = vec![None; tokens.len()];
    let mut block_start: Option<(usize, usize)> = None;
    for (index, token) in tokens.iter().enumerate() {
        if token.text == "BT" {
            block_start = Some((index, token.start));
        } else if token.text == "ET" {
            if let Some((start_index, start)) = block_start.take() {
                let range = ByteRange { start, end: token.end };
                for slot in ranges.iter_mut().take(index + 1).skip(start_index) {
                    *slot = Some(range.clone());
                }
            }
        }
    }
    ranges
}

fn normalize_resource_name(value: &str) -> String {
    value.trim_start_matches('/').to_string()
}

fn font_state_from_info(resource_name: &str, info: &FontResourceInfo) -> FontState {
    FontState {
        resource_name: Some(resource_name.to_string()),
        font_object_ref: info.object_ref.clone(),
        subtype: info.subtype.clone(),
        base_font: info.base_font.clone(),
        encoding: info.encoding.clone(),
        to_unicode_ref: info.to_unicode_ref.clone(),
    }
}

fn apply_text_move(state: &mut TextState, tx: f64, ty: f64) {
    let mut matrix = state.line_matrix.unwrap_or([1.0, 0.0, 0.0, 1.0, 0.0, 0.0]);
    matrix[4] += tx;
    matrix[5] += ty;
    state.line_matrix = Some(matrix);
    state.text_matrix = Some(matrix);
}

fn parse_matrix(tokens: &[Token]) -> Option<[f64; 6]> {
    if tokens.len() != 6 { return None; }
    let mut values = [0.0; 6];
    for (index, token) in tokens.iter().enumerate() {
        values[index] = token.text.parse::<f64>().ok()?;
    }
    Some(values)
}

fn tokenize(bytes: &[u8]) -> Vec<Token> {
    let mut tokens = Vec::new();
    let mut index = 0;
    while index < bytes.len() {
        if is_ws(bytes[index]) {
            index += 1;
            continue;
        }
        let start = index;
        match bytes[index] {
            b'%' => {
                while index < bytes.len() && bytes[index] != b'\n' && bytes[index] != b'\r' { index += 1; }
            }
            b'(' => {
                index += 1;
                let mut depth = 1;
                let mut escaped = false;
                while index < bytes.len() && depth > 0 {
                    if escaped { escaped = false; }
                    else if bytes[index] == b'\\' { escaped = true; }
                    else if bytes[index] == b'(' { depth += 1; }
                    else if bytes[index] == b')' { depth -= 1; }
                    index += 1;
                }
                tokens.push(Token { text: String::from_utf8_lossy(&bytes[start..index]).to_string(), start, end: index });
            }
            b'<' if index + 1 < bytes.len() && bytes[index + 1] != b'<' => {
                index += 1;
                while index < bytes.len() && bytes[index] != b'>' { index += 1; }
                if index < bytes.len() { index += 1; }
                tokens.push(Token { text: String::from_utf8_lossy(&bytes[start..index]).to_string(), start, end: index });
            }
            b'[' => {
                index += 1;
                let mut escaped = false;
                let mut literal_depth = 0;
                while index < bytes.len() {
                    let ch = bytes[index];
                    if literal_depth > 0 {
                        if escaped { escaped = false; }
                        else if ch == b'\\' { escaped = true; }
                        else if ch == b'(' { literal_depth += 1; }
                        else if ch == b')' { literal_depth -= 1; }
                    } else if ch == b'(' { literal_depth = 1; }
                    else if ch == b']' { index += 1; break; }
                    index += 1;
                }
                tokens.push(Token { text: String::from_utf8_lossy(&bytes[start..index]).to_string(), start, end: index });
            }
            _ => {
                while index < bytes.len() && !is_ws(bytes[index]) && !b"[]<>(){}".contains(&bytes[index]) {
                    index += 1;
                }
                if index > start {
                    tokens.push(Token { text: String::from_utf8_lossy(&bytes[start..index]).to_string(), start, end: index });
                } else {
                    index += 1;
                }
            }
        }
    }
    tokens
}

fn is_ws(byte: u8) -> bool {
    matches!(byte, b'\0' | b'\t' | b'\n' | b'\x0C' | b'\r' | b' ')
}
