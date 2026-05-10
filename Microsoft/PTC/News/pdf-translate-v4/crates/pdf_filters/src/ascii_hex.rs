//! ASCIIHexDecode (PDF spec 7.4.2). Direct implementation per
//! `build/04-stream-filters/DESIGN.md`.

use pdf_core::{PdfError, PdfResult};

fn hex_value(b: u8) -> Option<u8> {
    match b {
        b'0'..=b'9' => Some(b - b'0'),
        b'a'..=b'f' => Some(10 + b - b'a'),
        b'A'..=b'F' => Some(10 + b - b'A'),
        _ => None,
    }
}

fn is_whitespace(b: u8) -> bool {
    matches!(b, 0 | b'\t' | b'\n' | 0x0C | b'\r' | b' ')
}

pub fn decode(input: &[u8]) -> PdfResult<Vec<u8>> {
    let mut out = Vec::with_capacity(input.len() / 2);
    let mut high: Option<u8> = None;
    for &b in input {
        if b == b'>' {
            break;
        }
        if is_whitespace(b) {
            continue;
        }
        let nibble = hex_value(b).ok_or_else(|| PdfError::FilterDecode {
            filter: "ASCIIHexDecode".into(),
            reason: format!("invalid hex digit: 0x{b:02x}"),
        })?;
        match high.take() {
            Some(h) => out.push((h << 4) | nibble),
            None => high = Some(nibble),
        }
    }
    if let Some(h) = high {
        out.push(h << 4);
    }
    Ok(out)
}

pub fn encode(input: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(input.len() * 2 + 1);
    const HEX: &[u8; 16] = b"0123456789ABCDEF";
    for &b in input {
        out.push(HEX[(b >> 4) as usize]);
        out.push(HEX[(b & 0x0F) as usize]);
    }
    out.push(b'>');
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn decode_basic() {
        assert_eq!(decode(b"48656c6c6f>").unwrap(), b"Hello");
    }

    #[test]
    fn decode_with_whitespace() {
        assert_eq!(decode(b"48 65 6C\n6C 6F>").unwrap(), b"Hello");
    }

    #[test]
    fn decode_odd_nibble_pads_zero() {
        // "F" -> 0xF0
        assert_eq!(decode(b"F>").unwrap(), vec![0xF0]);
    }

    #[test]
    fn decode_invalid() {
        assert!(decode(b"GG>").is_err());
    }
}
