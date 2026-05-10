//! Tokenizer for the PDF content-stream operator language (PDF spec §7.8).
//!
//! Content streams are sequences of tokens followed by an operator name:
//!
//! ```text
//! 1 0 0 1 100 700 cm
//! BT /F1 12 Tf (Hello) Tj ET
//! ```
//!
//! We emit a flat stream of `(operands, operator)` records so callers can
//! walk it with a small interpreter.

use pdf_core::{PdfObject, PdfString};

#[derive(Debug, Clone)]
pub struct ContentInstruction {
    pub operator: Vec<u8>,
    pub operands: Vec<PdfObject>,
}

pub fn tokenize(content: &[u8]) -> Vec<ContentInstruction> {
    let mut out = Vec::new();
    let mut operands: Vec<PdfObject> = Vec::new();
    let mut cursor = 0usize;
    while cursor < content.len() {
        skip_ws(content, &mut cursor);
        if cursor >= content.len() {
            break;
        }
        let b = content[cursor];
        match b {
            b'%' => {
                while cursor < content.len() && content[cursor] != b'\n' && content[cursor] != b'\r' {
                    cursor += 1;
                }
            }
            b'(' => {
                operands.push(PdfObject::String(PdfString::Literal(read_literal_string(
                    content, &mut cursor,
                ))));
            }
            b'<' if peek(content, cursor + 1) == Some(b'<') => {
                // Inline dictionary -> we keep raw bytes as a hex string for simplicity.
                // Skip over `<<...>>` (very rare in content streams; e.g. /Properties).
                let start = cursor;
                let mut depth = 0;
                while cursor < content.len() {
                    if content[cursor] == b'<' && peek(content, cursor + 1) == Some(b'<') {
                        depth += 1;
                        cursor += 2;
                    } else if content[cursor] == b'>' && peek(content, cursor + 1) == Some(b'>') {
                        depth -= 1;
                        cursor += 2;
                        if depth == 0 {
                            break;
                        }
                    } else {
                        cursor += 1;
                    }
                }
                operands.push(PdfObject::String(PdfString::Literal(
                    content[start..cursor].to_vec(),
                )));
            }
            b'<' => {
                operands.push(PdfObject::String(PdfString::Hex(read_hex_string(
                    content, &mut cursor,
                ))));
            }
            b'[' => {
                operands.push(PdfObject::Array(read_array(content, &mut cursor)));
            }
            b'/' => {
                operands.push(PdfObject::Name(read_name(content, &mut cursor)));
            }
            b'+' | b'-' | b'.' | b'0'..=b'9' => {
                operands.push(read_number(content, &mut cursor));
            }
            _ => {
                let start = cursor;
                while cursor < content.len()
                    && !is_ws(content[cursor])
                    && !matches!(content[cursor], b'(' | b'<' | b'[' | b'/' | b'%')
                {
                    cursor += 1;
                }
                let op = content[start..cursor].to_vec();
                if !op.is_empty() {
                    out.push(ContentInstruction {
                        operator: op,
                        operands: std::mem::take(&mut operands),
                    });
                }
            }
        }
    }
    out
}

fn peek(content: &[u8], at: usize) -> Option<u8> {
    content.get(at).copied()
}

fn is_ws(b: u8) -> bool {
    matches!(b, 0 | b'\t' | b'\n' | 0x0C | b'\r' | b' ')
}

fn skip_ws(content: &[u8], cursor: &mut usize) {
    while let Some(&b) = content.get(*cursor) {
        if is_ws(b) {
            *cursor += 1;
        } else {
            break;
        }
    }
}

fn read_literal_string(content: &[u8], cursor: &mut usize) -> Vec<u8> {
    *cursor += 1; // consume '('
    let mut out = Vec::new();
    let mut depth: i32 = 1;
    while *cursor < content.len() && depth > 0 {
        let b = content[*cursor];
        *cursor += 1;
        match b {
            b'(' => {
                depth += 1;
                out.push(b);
            }
            b')' => {
                depth -= 1;
                if depth > 0 {
                    out.push(b);
                }
            }
            b'\\' => {
                if let Some(&n) = content.get(*cursor) {
                    *cursor += 1;
                    match n {
                        b'n' => out.push(b'\n'),
                        b'r' => out.push(b'\r'),
                        b't' => out.push(b'\t'),
                        b'b' => out.push(0x08),
                        b'f' => out.push(0x0C),
                        b'(' => out.push(b'('),
                        b')' => out.push(b')'),
                        b'\\' => out.push(b'\\'),
                        b'\r' => {
                            if content.get(*cursor) == Some(&b'\n') {
                                *cursor += 1;
                            }
                        }
                        b'\n' => {}
                        d @ b'0'..=b'7' => {
                            let mut value = (d - b'0') as u16;
                            for _ in 0..2 {
                                match content.get(*cursor) {
                                    Some(c @ b'0'..=b'7') => {
                                        value = value * 8 + (*c - b'0') as u16;
                                        *cursor += 1;
                                    }
                                    _ => break,
                                }
                            }
                            out.push(value as u8);
                        }
                        other => out.push(other),
                    }
                }
            }
            other => out.push(other),
        }
    }
    out
}

fn read_hex_string(content: &[u8], cursor: &mut usize) -> Vec<u8> {
    *cursor += 1; // consume '<'
    let mut nibbles: Vec<u8> = Vec::new();
    while *cursor < content.len() {
        let b = content[*cursor];
        *cursor += 1;
        if b == b'>' {
            break;
        }
        if is_ws(b) {
            continue;
        }
        let n = match b {
            b'0'..=b'9' => b - b'0',
            b'a'..=b'f' => 10 + b - b'a',
            b'A'..=b'F' => 10 + b - b'A',
            _ => continue,
        };
        nibbles.push(n);
    }
    if nibbles.len() % 2 == 1 {
        nibbles.push(0);
    }
    nibbles.chunks_exact(2).map(|c| (c[0] << 4) | c[1]).collect()
}

fn read_array(content: &[u8], cursor: &mut usize) -> Vec<PdfObject> {
    *cursor += 1; // consume '['
    let mut out = Vec::new();
    loop {
        skip_ws(content, cursor);
        if *cursor >= content.len() {
            break;
        }
        if content[*cursor] == b']' {
            *cursor += 1;
            break;
        }
        match content[*cursor] {
            b'(' => out.push(PdfObject::String(PdfString::Literal(read_literal_string(
                content, cursor,
            )))),
            b'<' => out.push(PdfObject::String(PdfString::Hex(read_hex_string(
                content, cursor,
            )))),
            b'/' => out.push(PdfObject::Name(read_name(content, cursor))),
            b'+' | b'-' | b'.' | b'0'..=b'9' => out.push(read_number(content, cursor)),
            _ => *cursor += 1,
        }
    }
    out
}

fn read_name(content: &[u8], cursor: &mut usize) -> Vec<u8> {
    *cursor += 1; // consume '/'
    let start = *cursor;
    while *cursor < content.len() {
        let b = content[*cursor];
        if is_ws(b) || matches!(b, b'(' | b'<' | b'[' | b'/' | b']' | b'>' | b'%') {
            break;
        }
        *cursor += 1;
    }
    content[start..*cursor].to_vec()
}

fn read_number(content: &[u8], cursor: &mut usize) -> PdfObject {
    let start = *cursor;
    if matches!(content[*cursor], b'+' | b'-') {
        *cursor += 1;
    }
    while let Some(&b) = content.get(*cursor) {
        if b.is_ascii_digit() || b == b'.' {
            *cursor += 1;
        } else {
            break;
        }
    }
    let s = std::str::from_utf8(&content[start..*cursor]).unwrap_or("0");
    if s.contains('.') {
        PdfObject::Number(pdf_core::PdfNumber::Real(s.parse().unwrap_or(0.0)))
    } else {
        PdfObject::Number(pdf_core::PdfNumber::Integer(s.parse().unwrap_or(0)))
    }
}
