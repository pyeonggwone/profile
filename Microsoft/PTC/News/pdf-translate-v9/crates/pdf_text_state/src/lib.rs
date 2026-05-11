use anyhow::Result;
use lopdf::Dictionary;
use pdf_core::LoadedPdf;
use pdf_models::*;
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
        let text_runs = parse_stream(stream.page, stream.object_id.0, &stream.decoded, stream.resources.as_ref());
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

fn parse_stream(page: u32, stream_xref: u32, bytes: &[u8], resources: Option<&Dictionary>) -> Vec<RawTextRun> {
    let tokens = tokenize(bytes);
    let mut state = TextState::default();
    let mut sequence: Vec<OperatorSnapshot> = Vec::new();
    let mut runs = Vec::new();
    let mut counter = 1;
    for index in 0..tokens.len() {
        let op = tokens[index].text.as_str();
        match op {
            "BT" | "ET" => sequence.push(OperatorSnapshot { op: op.to_string(), font: None, size: None, matrix: None }),
            "Tf" if index >= 2 => {
                state.font = Some(tokens[index - 2].text.clone());
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
            "Tj" | "'" | "\"" if index >= 1 => {
                let operand = tokens[index - 1].clone();
                runs.push(make_run(page, stream_xref, counter, op, operand, &sequence, &state, resources));
                counter += 1;
            }
            "TJ" if index >= 1 => {
                let operand = tokens[index - 1].clone();
                runs.push(make_run(page, stream_xref, counter, op, operand, &sequence, &state, resources));
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
    sequence: &[OperatorSnapshot],
    state: &TextState,
    _resources: Option<&Dictionary>,
) -> RawTextRun {
    let (decoded, _, _) = pdf_cmap::decode_pdf_operand(&operand.text);
    RawTextRun {
        id: format!("p{page:04}-s{stream_xref:04}-r{counter:05}"),
        restore_options: RestoreOptions {
            stream_xref,
            operator: operator.to_string(),
            operand_range: ByteRange { start: operand.start, end: operand.end },
            text_block_range: None,
            operator_sequence: sequence.to_vec(),
            text_state: state.clone(),
            font_state: FontState {
                resource_name: state.font.clone(),
                font_object_ref: None,
                subtype: None,
                base_font: None,
                encoding: None,
                to_unicode_ref: None,
            },
        },
        text_payload: TextPayload {
            encoded_original: operand.text,
            decoded_original: decoded,
            decoded_translated: None,
            replacement_encoded: None,
        },
    }
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
