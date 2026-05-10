//! ToUnicode CMap parser (PDF spec §9.10.3, Adobe Technical Note #5014).
//!
//! A PDF font dictionary may have a `/ToUnicode` reference to a stream
//! whose bytes contain a PostScript-flavoured CMap that maps source
//! character codes to Unicode strings. We need it to extract correct
//! text from PDFs whose internal font encoding is non-trivial (Identity-H
//! CIDs, custom Type1 encodings, etc.).
//!
//! Supported operators:
//!
//! - `beginbfchar` / `endbfchar`
//! - `beginbfrange` / `endbfrange`
//! - `begincodespacerange` / `endcodespacerange`
//!
//! Other CMap operators (`begincidchar`, `usecmap`, …) are ignored
//! gracefully — we just fall back to single-byte identity for codes
//! that are not in the parsed map.

use std::collections::BTreeMap;

#[derive(Debug, Clone, Default)]
pub struct ToUnicodeCMap {
    /// Maps a source code (as a u32 packed big-endian) to the Unicode
    /// string it produces.
    pub map: BTreeMap<u32, String>,
    /// Detected codespace ranges. Pairs of (low, high) byte ranges.
    /// We use these only to know the source-code byte width.
    pub codespace: Vec<(u32, u32)>,
    /// Effective byte width of source codes (1 or 2 in practice).
    pub source_byte_width: u8,
}

impl ToUnicodeCMap {
    pub fn parse(bytes: &[u8]) -> Self {
        let mut p = Parser::new(bytes);
        let mut cmap = ToUnicodeCMap::default();
        while let Some(token) = p.next_token() {
            match token.as_slice() {
                b"begincodespacerange" => parse_codespace(&mut p, &mut cmap),
                b"beginbfchar" => parse_bfchar(&mut p, &mut cmap),
                b"beginbfrange" => parse_bfrange(&mut p, &mut cmap),
                _ => {}
            }
        }
        cmap.source_byte_width = if cmap
            .codespace
            .iter()
            .any(|(_, hi)| *hi > 0xFF)
        {
            2
        } else {
            1
        };
        cmap
    }

    /// Decode a sequence of source bytes into Unicode using this CMap.
    /// Falls back to passing the raw byte through as a Latin-1 char if
    /// the code is not mapped.
    pub fn decode_bytes(&self, bytes: &[u8]) -> String {
        let width = self.source_byte_width.max(1) as usize;
        let mut out = String::new();
        let mut i = 0;
        while i < bytes.len() {
            let take = width.min(bytes.len() - i);
            let mut code: u32 = 0;
            for k in 0..take {
                code = (code << 8) | bytes[i + k] as u32;
            }
            i += take;
            if let Some(s) = self.map.get(&code) {
                out.push_str(s);
            } else if width == 1 {
                out.push(code as u8 as char);
            } else {
                // Last-resort: treat as U+0000..U+FFFF directly.
                if let Some(c) = char::from_u32(code) {
                    out.push(c);
                }
            }
        }
        out
    }
}

fn parse_codespace(p: &mut Parser<'_>, cmap: &mut ToUnicodeCMap) {
    loop {
        let lo = match read_hex(p) {
            Some(v) => v,
            None => return,
        };
        let hi = match read_hex(p) {
            Some(v) => v,
            None => return,
        };
        cmap.codespace.push((lo, hi));
        // Look ahead for endcodespacerange
        let save = p.pos;
        if let Some(t) = p.next_token() {
            if t == b"endcodespacerange" {
                return;
            }
        }
        p.pos = save;
    }
}

fn parse_bfchar(p: &mut Parser<'_>, cmap: &mut ToUnicodeCMap) {
    loop {
        let save = p.pos;
        if let Some(t) = peek_token(p) {
            if t == b"endbfchar" {
                p.next_token();
                return;
            }
        }
        p.pos = save;
        let src = match read_hex(p) {
            Some(v) => v,
            None => return,
        };
        let dst = match read_hex_string(p) {
            Some(v) => v,
            None => return,
        };
        cmap.map.insert(src, dst);
    }
}

fn parse_bfrange(p: &mut Parser<'_>, cmap: &mut ToUnicodeCMap) {
    loop {
        let save = p.pos;
        if let Some(t) = peek_token(p) {
            if t == b"endbfrange" {
                p.next_token();
                return;
            }
        }
        p.pos = save;
        let lo = match read_hex(p) {
            Some(v) => v,
            None => return,
        };
        let hi = match read_hex(p) {
            Some(v) => v,
            None => return,
        };
        // Third token is either <hex> or [<hex> <hex> ...]
        p.skip_ws();
        match p.peek() {
            Some(b'[') => {
                p.advance(1);
                let mut idx = 0u32;
                loop {
                    p.skip_ws();
                    if p.peek() == Some(b']') {
                        p.advance(1);
                        break;
                    }
                    match read_hex_string(p) {
                        Some(s) => {
                            cmap.map.insert(lo + idx, s);
                            idx += 1;
                        }
                        None => return,
                    }
                }
            }
            Some(b'<') => {
                let start = match read_hex_string(p) {
                    Some(v) => v,
                    None => return,
                };
                let start_cp = start.chars().next().map(|c| c as u32).unwrap_or(0);
                for offset in 0..=(hi - lo) {
                    if let Some(c) = char::from_u32(start_cp + offset) {
                        cmap.map.insert(lo + offset, c.to_string());
                    }
                }
            }
            _ => return,
        }
    }
}

struct Parser<'a> {
    data: &'a [u8],
    pos: usize,
}

impl<'a> Parser<'a> {
    fn new(data: &'a [u8]) -> Self {
        Self { data, pos: 0 }
    }

    fn peek(&self) -> Option<u8> {
        self.data.get(self.pos).copied()
    }

    fn advance(&mut self, n: usize) {
        self.pos = (self.pos + n).min(self.data.len());
    }

    fn skip_ws(&mut self) {
        loop {
            while let Some(b) = self.peek() {
                if matches!(b, 0 | b'\t' | b'\n' | 0x0C | b'\r' | b' ') {
                    self.pos += 1;
                } else {
                    break;
                }
            }
            // skip comments too
            if self.peek() == Some(b'%') {
                while let Some(b) = self.peek() {
                    self.pos += 1;
                    if b == b'\n' {
                        break;
                    }
                }
                continue;
            }
            break;
        }
    }

    fn next_token(&mut self) -> Option<Vec<u8>> {
        self.skip_ws();
        let b = self.peek()?;
        if b == b'<' || b == b'[' || b == b'(' {
            return None; // structural tokens are read by helpers
        }
        let start = self.pos;
        while let Some(b) = self.peek() {
            if matches!(b, 0 | b'\t' | b'\n' | 0x0C | b'\r' | b' ' | b'<' | b'[' | b'(') {
                break;
            }
            self.pos += 1;
        }
        if start == self.pos {
            return None;
        }
        Some(self.data[start..self.pos].to_vec())
    }
}

fn peek_token(p: &mut Parser<'_>) -> Option<Vec<u8>> {
    let save = p.pos;
    let t = p.next_token();
    p.pos = save;
    t
}

fn read_hex(p: &mut Parser<'_>) -> Option<u32> {
    p.skip_ws();
    if p.peek() != Some(b'<') {
        return None;
    }
    p.advance(1);
    let start = p.pos;
    while let Some(b) = p.peek() {
        if b == b'>' {
            break;
        }
        p.pos += 1;
    }
    let hex_bytes = &p.data[start..p.pos];
    if p.peek() == Some(b'>') {
        p.advance(1);
    }
    let mut value: u32 = 0;
    for b in hex_bytes {
        if matches!(b, b' ' | b'\t' | b'\n' | b'\r') {
            continue;
        }
        let nib = match b {
            b'0'..=b'9' => b - b'0',
            b'a'..=b'f' => 10 + b - b'a',
            b'A'..=b'F' => 10 + b - b'A',
            _ => return None,
        };
        value = (value << 4) | nib as u32;
    }
    Some(value)
}

fn read_hex_string(p: &mut Parser<'_>) -> Option<String> {
    p.skip_ws();
    if p.peek() != Some(b'<') {
        return None;
    }
    p.advance(1);
    let start = p.pos;
    while let Some(b) = p.peek() {
        if b == b'>' {
            break;
        }
        p.pos += 1;
    }
    let hex_bytes = &p.data[start..p.pos];
    if p.peek() == Some(b'>') {
        p.advance(1);
    }
    let mut bytes = Vec::with_capacity(hex_bytes.len() / 2);
    let mut high: Option<u8> = None;
    for b in hex_bytes {
        if matches!(b, b' ' | b'\t' | b'\n' | b'\r') {
            continue;
        }
        let nib = match b {
            b'0'..=b'9' => b - b'0',
            b'a'..=b'f' => 10 + b - b'a',
            b'A'..=b'F' => 10 + b - b'A',
            _ => return None,
        };
        match high.take() {
            Some(h) => bytes.push((h << 4) | nib),
            None => high = Some(nib),
        }
    }
    if let Some(h) = high {
        bytes.push(h << 4);
    }
    // Treat as UTF-16BE (most ToUnicode CMaps use 2-byte BE strings).
    let mut out = String::new();
    let mut i = 0;
    while i + 1 < bytes.len() {
        let u = ((bytes[i] as u16) << 8) | bytes[i + 1] as u16;
        if (0xD800..=0xDBFF).contains(&u) && i + 3 < bytes.len() {
            let lo = ((bytes[i + 2] as u16) << 8) | bytes[i + 3] as u16;
            let cp = 0x10000
                + (((u - 0xD800) as u32) << 10)
                + (lo - 0xDC00) as u32;
            if let Some(c) = char::from_u32(cp) {
                out.push(c);
            }
            i += 4;
        } else if let Some(c) = char::from_u32(u as u32) {
            out.push(c);
            i += 2;
        } else {
            i += 2;
        }
    }
    if i < bytes.len() {
        out.push(bytes[i] as char);
    }
    Some(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_bfchar() {
        let cmap_text = b"\
/CIDInit /ProcSet findresource begin\n\
12 dict begin\n\
begincmap\n\
1 begincodespacerange\n<00> <FF>\nendcodespacerange\n\
2 beginbfchar\n\
<41> <0041>\n\
<42> <0042>\n\
endbfchar\n\
endcmap\n";
        let m = ToUnicodeCMap::parse(cmap_text);
        assert_eq!(m.map.get(&0x41), Some(&"A".to_string()));
        assert_eq!(m.map.get(&0x42), Some(&"B".to_string()));
        assert_eq!(m.source_byte_width, 1);
        assert_eq!(m.decode_bytes(b"\x41\x42"), "AB");
    }

    #[test]
    fn parses_bfrange_start_string() {
        let cmap_text = b"\
1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n\
1 beginbfrange\n\
<0030> <0039> <0030>\n\
endbfrange\n";
        let m = ToUnicodeCMap::parse(cmap_text);
        assert_eq!(m.map.get(&0x30), Some(&"0".to_string()));
        assert_eq!(m.map.get(&0x39), Some(&"9".to_string()));
    }
}
