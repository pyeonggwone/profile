//! Direct recursive-descent parser for PDF objects (PDF spec §7.3).

use pdf_core::{
    ByteRange, ObjectId, ObjectRef, PdfDict, PdfError, PdfNumber, PdfObject, PdfResult, PdfStream,
    PdfString,
};

use crate::lexer::{is_delimiter, is_whitespace, Cursor};

/// Top-level object record produced by `parse_indirect_object`.
#[derive(Debug, Clone)]
pub struct ObjectEntry {
    pub id: ObjectId,
    pub value: PdfObject,
    /// Byte range of the entire `n g obj … endobj` block in the source PDF.
    pub byte_range: ByteRange,
}

/// Stateless recursive-descent parser. The "state" is the cursor passed in.
pub struct ObjectParser;

impl ObjectParser {
    /// Parse an indirect object starting at `cursor.pos`. Expects to see
    /// `n g obj <object> endobj`.
    pub fn parse_indirect_object(cursor: &mut Cursor<'_>) -> PdfResult<ObjectEntry> {
        let obj_start = cursor.pos;
        cursor.skip_ws_and_comments();
        let number = parse_unsigned_int(cursor)?;
        cursor.skip_ws_and_comments();
        let gen = parse_unsigned_int(cursor)? as u16;
        cursor.skip_ws_and_comments();
        if !cursor.match_keyword(b"obj") {
            return Err(PdfError::ObjectParse {
                obj: number,
                gen,
                reason: "missing `obj` keyword".into(),
            });
        }
        cursor.skip_ws_and_comments();
        let value = Self::parse_object(cursor)?;
        // After value: optionally a stream (handled inside parse_object),
        // then `endobj`.
        cursor.skip_ws_and_comments();
        if !cursor.match_keyword(b"endobj") {
            // Recoverable: scan forward for `endobj` to locate the block end.
            if let Some(p) = find_keyword(cursor.data, cursor.pos, b"endobj") {
                cursor.pos = p + b"endobj".len();
            } else {
                return Err(PdfError::ObjectParse {
                    obj: number,
                    gen,
                    reason: "missing `endobj` keyword".into(),
                });
            }
        }
        Ok(ObjectEntry {
            id: ObjectId::new(number, gen),
            value,
            byte_range: ByteRange::new(obj_start, cursor.pos),
        })
    }

    /// Parse a single PDF object (no `n g obj` wrapper). May return a
    /// `PdfObject::Stream` if the dictionary is followed by `stream`.
    pub fn parse_object(cursor: &mut Cursor<'_>) -> PdfResult<PdfObject> {
        cursor.skip_ws_and_comments();
        let b = cursor.peek().ok_or(PdfError::UnexpectedEof(cursor.pos))?;
        match b {
            b'<' if cursor.peek_at(1) == Some(b'<') => Self::parse_dict_or_stream(cursor),
            b'<' => Ok(PdfObject::String(PdfString::Hex(parse_hex_string(cursor)?))),
            b'(' => Ok(PdfObject::String(PdfString::Literal(parse_literal_string(
                cursor,
            )?))),
            b'/' => Ok(PdfObject::Name(parse_name(cursor)?)),
            b'[' => Ok(PdfObject::Array(parse_array(cursor)?)),
            b't' | b'f' | b'n' => parse_keyword_literal(cursor),
            b'+' | b'-' | b'.' | b'0'..=b'9' => parse_number_or_reference(cursor),
            other => Err(PdfError::ObjectParse {
                obj: 0,
                gen: 0,
                reason: format!("unexpected byte 0x{other:02x} at {}", cursor.pos),
            }),
        }
    }

    fn parse_dict_or_stream(cursor: &mut Cursor<'_>) -> PdfResult<PdfObject> {
        let dict_start = cursor.pos;
        let dict = parse_dict(cursor)?;
        cursor.skip_ws_and_comments();
        // Look ahead for `stream`
        let save = cursor.pos;
        if cursor.match_keyword(b"stream") {
            // Per spec: `stream` keyword followed by EOL (CR LF or LF, never bare CR).
            // Be tolerant.
            match cursor.peek() {
                Some(b'\r') => {
                    cursor.advance(1);
                    if cursor.peek() == Some(b'\n') {
                        cursor.advance(1);
                    }
                }
                Some(b'\n') => cursor.advance(1),
                _ => {}
            }
            let body_start = cursor.pos;
            // /Length value: must be an integer in the dictionary OR
            // an indirect reference (we cannot resolve that without the
            // xref; in that case fall back to scanning for `endstream`).
            let declared_len = dict.get(b"Length".as_ref()).and_then(|o| match o {
                PdfObject::Number(PdfNumber::Integer(i)) => Some(*i as usize),
                _ => None,
            });
            let body_end = if let Some(n) = declared_len {
                // Validate: bytes after offset+n should be `endstream` keyword
                // (after optional EOL).
                let candidate = body_start + n;
                if candidate <= cursor.data.len() {
                    cursor.pos = candidate;
                    candidate
                } else {
                    // Fall through to scan
                    scan_endstream(cursor.data, body_start)?
                }
            } else {
                scan_endstream(cursor.data, body_start)?
            };
            let raw_data = cursor.data[body_start..body_end].to_vec();
            cursor.pos = body_end;
            // Skip trailing whitespace before `endstream`
            cursor.skip_ws_only();
            if !cursor.match_keyword(b"endstream") {
                // Try harder: scan for endstream
                if let Some(p) = find_keyword(cursor.data, cursor.pos, b"endstream") {
                    cursor.pos = p + b"endstream".len();
                } else {
                    return Err(PdfError::StreamLengthMismatch {
                        declared: declared_len.unwrap_or(0),
                        scanned: 0,
                    });
                }
            }
            Ok(PdfObject::Stream(PdfStream {
                dict,
                raw_data,
                raw_range: Some(ByteRange::new(body_start, body_end)),
            }))
        } else {
            cursor.pos = save;
            // No stream, just a dictionary
            let _ = dict_start; // currently unused
            Ok(PdfObject::Dict(dict))
        }
    }
}

fn parse_dict(cursor: &mut Cursor<'_>) -> PdfResult<PdfDict> {
    cursor.expect_byte(b'<').map_err(|_| PdfError::DictParse("expected `<<`".into()))?;
    cursor.expect_byte(b'<').map_err(|_| PdfError::DictParse("expected `<<`".into()))?;
    let mut dict = PdfDict::new();
    loop {
        cursor.skip_ws_and_comments();
        match cursor.peek() {
            Some(b'>') if cursor.peek_at(1) == Some(b'>') => {
                cursor.advance(2);
                return Ok(dict);
            }
            Some(b'/') => {
                let key = parse_name(cursor)?;
                cursor.skip_ws_and_comments();
                let value = ObjectParser::parse_object(cursor)?;
                dict.insert(key, value);
            }
            Some(other) => {
                return Err(PdfError::DictParse(format!(
                    "expected name key, got 0x{other:02x} at {}",
                    cursor.pos
                )));
            }
            None => return Err(PdfError::UnexpectedEof(cursor.pos)),
        }
    }
}

fn parse_array(cursor: &mut Cursor<'_>) -> PdfResult<Vec<PdfObject>> {
    cursor.expect_byte(b'[').map_err(|_| PdfError::ArrayParse("expected `[`".into()))?;
    let mut out = Vec::new();
    loop {
        cursor.skip_ws_and_comments();
        match cursor.peek() {
            Some(b']') => {
                cursor.advance(1);
                return Ok(out);
            }
            Some(_) => {
                let v = ObjectParser::parse_object(cursor)?;
                out.push(v);
            }
            None => return Err(PdfError::UnexpectedEof(cursor.pos)),
        }
    }
}

fn parse_name(cursor: &mut Cursor<'_>) -> PdfResult<Vec<u8>> {
    cursor.expect_byte(b'/').map_err(|_| PdfError::InvalidName("expected `/`".into()))?;
    let mut out = Vec::new();
    while let Some(b) = cursor.peek() {
        if is_whitespace(b) || is_delimiter(b) {
            break;
        }
        cursor.advance(1);
        if b == b'#' {
            // Hex escape: two hex digits
            let h = cursor.peek().ok_or(PdfError::InvalidName("`#` truncated".into()))?;
            cursor.advance(1);
            let l = cursor.peek().ok_or(PdfError::InvalidName("`#` truncated".into()))?;
            cursor.advance(1);
            let hi = hex_digit(h).ok_or_else(|| PdfError::InvalidName("bad hex".into()))?;
            let lo = hex_digit(l).ok_or_else(|| PdfError::InvalidName("bad hex".into()))?;
            out.push((hi << 4) | lo);
        } else {
            out.push(b);
        }
    }
    Ok(out)
}

fn hex_digit(b: u8) -> Option<u8> {
    match b {
        b'0'..=b'9' => Some(b - b'0'),
        b'a'..=b'f' => Some(10 + b - b'a'),
        b'A'..=b'F' => Some(10 + b - b'A'),
        _ => None,
    }
}

fn parse_literal_string(cursor: &mut Cursor<'_>) -> PdfResult<Vec<u8>> {
    cursor.expect_byte(b'(').map_err(|_| PdfError::InvalidString("expected `(`".into()))?;
    let mut out = Vec::new();
    let mut depth: i32 = 1;
    while depth > 0 {
        let b = cursor.peek().ok_or(PdfError::UnexpectedEof(cursor.pos))?;
        cursor.advance(1);
        match b {
            b'(' => {
                depth += 1;
                out.push(b);
            }
            b')' => {
                depth -= 1;
                if depth == 0 {
                    break;
                }
                out.push(b);
            }
            b'\\' => {
                let n = cursor.peek().ok_or(PdfError::UnexpectedEof(cursor.pos))?;
                cursor.advance(1);
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
                        if cursor.peek() == Some(b'\n') {
                            cursor.advance(1);
                        }
                    }
                    b'\n' => {}
                    d @ b'0'..=b'7' => {
                        // Up to three octal digits
                        let mut value = (d - b'0') as u16;
                        for _ in 0..2 {
                            match cursor.peek() {
                                Some(c @ b'0'..=b'7') => {
                                    cursor.advance(1);
                                    value = value * 8 + (c - b'0') as u16;
                                }
                                _ => break,
                            }
                        }
                        out.push(value as u8);
                    }
                    other => out.push(other),
                }
            }
            b'\r' => {
                // Normalize CR/CRLF -> LF
                if cursor.peek() == Some(b'\n') {
                    cursor.advance(1);
                }
                out.push(b'\n');
            }
            other => out.push(other),
        }
    }
    Ok(out)
}

fn parse_hex_string(cursor: &mut Cursor<'_>) -> PdfResult<Vec<u8>> {
    cursor.expect_byte(b'<').map_err(|_| PdfError::InvalidString("expected `<`".into()))?;
    let mut nibbles: Vec<u8> = Vec::new();
    while let Some(b) = cursor.peek() {
        cursor.advance(1);
        if b == b'>' {
            break;
        }
        if is_whitespace(b) {
            continue;
        }
        let n = hex_digit(b).ok_or_else(|| {
            PdfError::InvalidString(format!("bad hex digit 0x{b:02x}"))
        })?;
        nibbles.push(n);
    }
    if nibbles.len() % 2 == 1 {
        nibbles.push(0);
    }
    Ok(nibbles
        .chunks_exact(2)
        .map(|c| (c[0] << 4) | c[1])
        .collect())
}

fn parse_unsigned_int(cursor: &mut Cursor<'_>) -> PdfResult<u32> {
    let start = cursor.pos;
    while let Some(b) = cursor.peek() {
        if b.is_ascii_digit() {
            cursor.advance(1);
        } else {
            break;
        }
    }
    let s = std::str::from_utf8(&cursor.data[start..cursor.pos])
        .map_err(|_| PdfError::InvalidNumber(format!("non-utf8 at {start}")))?;
    s.parse::<u32>()
        .map_err(|_| PdfError::InvalidNumber(format!("bad uint `{s}`")))
}

fn parse_keyword_literal(cursor: &mut Cursor<'_>) -> PdfResult<PdfObject> {
    let token = cursor.read_regular_token();
    match token {
        b"true" => Ok(PdfObject::Boolean(true)),
        b"false" => Ok(PdfObject::Boolean(false)),
        b"null" => Ok(PdfObject::Null),
        other => Err(PdfError::ObjectParse {
            obj: 0,
            gen: 0,
            reason: format!("unknown keyword `{}`", String::from_utf8_lossy(other)),
        }),
    }
}

fn parse_number_or_reference(cursor: &mut Cursor<'_>) -> PdfResult<PdfObject> {
    let start = cursor.pos;
    let token = cursor.read_regular_token().to_vec();
    let s = std::str::from_utf8(&token)
        .map_err(|_| PdfError::InvalidNumber("non-utf8 number".into()))?;
    let first_num = parse_pdf_number(s)?;

    // Check for indirect reference: `<int> <int> R`
    let save = cursor.pos;
    cursor.skip_ws_only();
    let mut peek_cursor = cursor.clone();
    let token2 = peek_cursor.read_regular_token().to_vec();
    if !token2.is_empty() && token2.iter().all(|b| b.is_ascii_digit()) {
        peek_cursor.skip_ws_only();
        let token3 = peek_cursor.read_regular_token().to_vec();
        if token3 == b"R" {
            // Confirmed reference
            let num = match first_num {
                PdfNumber::Integer(i) if i >= 0 => i as u32,
                _ => {
                    cursor.pos = save;
                    return Ok(PdfObject::Number(first_num));
                }
            };
            let gen: u16 = std::str::from_utf8(&token2)
                .ok()
                .and_then(|s| s.parse().ok())
                .ok_or_else(|| PdfError::InvalidNumber("bad generation".into()))?;
            cursor.pos = peek_cursor.pos;
            let _ = start;
            return Ok(PdfObject::Reference(ObjectRef::new(num, gen)));
        }
    }
    cursor.pos = save;
    Ok(PdfObject::Number(first_num))
}

fn parse_pdf_number(s: &str) -> PdfResult<PdfNumber> {
    if s.contains('.') || s.contains('e') || s.contains('E') {
        s.parse::<f64>()
            .map(PdfNumber::Real)
            .map_err(|_| PdfError::InvalidNumber(s.to_string()))
    } else {
        s.parse::<i64>()
            .map(PdfNumber::Integer)
            .map_err(|_| PdfError::InvalidNumber(s.to_string()))
    }
}

fn scan_endstream(data: &[u8], from: usize) -> PdfResult<usize> {
    let needle = b"endstream";
    if let Some(rel) = data[from..].windows(needle.len()).position(|w| w == needle) {
        // Walk back over EOL (PDF: `endstream` preceded by EOL).
        let mut end = from + rel;
        while end > from && matches!(data[end - 1], b'\r' | b'\n') {
            end -= 1;
        }
        Ok(end)
    } else {
        Err(PdfError::StreamLengthMismatch {
            declared: 0,
            scanned: 0,
        })
    }
}

pub(crate) fn find_keyword(data: &[u8], from: usize, kw: &[u8]) -> Option<usize> {
    data[from..].windows(kw.len()).position(|w| w == kw).map(|p| from + p)
}
