//! ASCII85Decode (PDF spec 7.4.3). Direct implementation.

use pdf_core::{PdfError, PdfResult};

fn is_whitespace(b: u8) -> bool {
    matches!(b, 0 | b'\t' | b'\n' | 0x0C | b'\r' | b' ')
}

pub fn decode(input: &[u8]) -> PdfResult<Vec<u8>> {
    // Strip optional leading "<~"
    let mut data = input;
    if data.starts_with(b"<~") {
        data = &data[2..];
    }
    let mut out = Vec::with_capacity(input.len() * 4 / 5 + 4);
    let mut group: u32 = 0;
    let mut count: u32 = 0;

    for &b in data {
        if b == b'~' {
            break; // end-of-data sequence "~>"
        }
        if is_whitespace(b) {
            continue;
        }
        if b == b'z' {
            if count != 0 {
                return Err(PdfError::FilterDecode {
                    filter: "ASCII85Decode".into(),
                    reason: "'z' inside group".into(),
                });
            }
            out.extend_from_slice(&[0, 0, 0, 0]);
            continue;
        }
        if !(b'!'..=b'u').contains(&b) {
            return Err(PdfError::FilterDecode {
                filter: "ASCII85Decode".into(),
                reason: format!("char out of range: 0x{b:02x}"),
            });
        }
        group = group
            .checked_mul(85)
            .and_then(|g| g.checked_add((b - b'!') as u32))
            .ok_or_else(|| PdfError::FilterDecode {
                filter: "ASCII85Decode".into(),
                reason: "group overflow".into(),
            })?;
        count += 1;
        if count == 5 {
            out.push((group >> 24) as u8);
            out.push((group >> 16) as u8);
            out.push((group >> 8) as u8);
            out.push(group as u8);
            group = 0;
            count = 0;
        }
    }

    if count == 1 {
        return Err(PdfError::FilterDecode {
            filter: "ASCII85Decode".into(),
            reason: "trailing single character".into(),
        });
    }
    if count > 1 {
        // pad with 'u' (84) and emit count-1 bytes
        for _ in count..5 {
            group = group * 85 + 84;
        }
        let bytes = [
            (group >> 24) as u8,
            (group >> 16) as u8,
            (group >> 8) as u8,
            group as u8,
        ];
        out.extend_from_slice(&bytes[..(count as usize) - 1]);
    }
    Ok(out)
}

pub fn encode(input: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(input.len() * 5 / 4 + 4);
    let chunks = input.chunks(4);
    for chunk in chunks {
        if chunk == [0, 0, 0, 0] {
            out.push(b'z');
            continue;
        }
        let mut buf = [0u8; 4];
        let len = chunk.len();
        buf[..len].copy_from_slice(chunk);
        let group = u32::from_be_bytes(buf);
        let mut digits = [0u8; 5];
        let mut g = group;
        for d in digits.iter_mut().rev() {
            *d = (g % 85) as u8 + b'!';
            g /= 85;
        }
        out.extend_from_slice(&digits[..len + 1]);
    }
    out.extend_from_slice(b"~>");
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip_text() {
        let text = b"Hello, ASCII85!";
        let enc = encode(text);
        let dec = decode(&enc).unwrap();
        assert_eq!(dec, text);
    }

    #[test]
    fn z_shortcut_decodes_to_zeros() {
        assert_eq!(decode(b"z~>").unwrap(), vec![0u8; 4]);
    }
}
