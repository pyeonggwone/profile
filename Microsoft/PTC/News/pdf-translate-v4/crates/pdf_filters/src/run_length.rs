//! RunLengthDecode (PDF spec 7.4.5). Direct implementation.

use pdf_core::{PdfError, PdfResult};

pub fn decode(input: &[u8]) -> PdfResult<Vec<u8>> {
    let mut out = Vec::with_capacity(input.len());
    let mut i = 0;
    while i < input.len() {
        let len = input[i] as i32;
        i += 1;
        match len {
            0..=127 => {
                let copy = (len as usize) + 1;
                if i + copy > input.len() {
                    return Err(PdfError::FilterDecode {
                        filter: "RunLengthDecode".into(),
                        reason: "literal run truncated".into(),
                    });
                }
                out.extend_from_slice(&input[i..i + copy]);
                i += copy;
            }
            128 => break, // EOD
            _ => {
                if i >= input.len() {
                    return Err(PdfError::FilterDecode {
                        filter: "RunLengthDecode".into(),
                        reason: "repeat byte missing".into(),
                    });
                }
                let byte = input[i];
                i += 1;
                let times = 257 - len as usize;
                out.extend(std::iter::repeat(byte).take(times));
            }
        }
    }
    Ok(out)
}

pub fn encode(input: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(input.len());
    let mut i = 0;
    while i < input.len() {
        // Find run length up to 128.
        let mut run = 1;
        while run < 128 && i + run < input.len() && input[i + run] == input[i] {
            run += 1;
        }
        if run >= 3 {
            out.push((257 - run) as u8);
            out.push(input[i]);
            i += run;
            continue;
        }
        // Otherwise build a literal run up to 128 bytes, stopping if a
        // 3+ byte repeat is detected.
        let start = i;
        let mut lit = 0usize;
        while i < input.len() && lit < 128 {
            if i + 2 < input.len()
                && input[i] == input[i + 1]
                && input[i + 1] == input[i + 2]
            {
                break;
            }
            i += 1;
            lit += 1;
        }
        out.push((lit - 1) as u8);
        out.extend_from_slice(&input[start..start + lit]);
    }
    out.push(128); // EOD
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn decode_eod() {
        assert_eq!(decode(&[128]).unwrap(), Vec::<u8>::new());
    }

    #[test]
    fn decode_literal_then_repeat() {
        // 0x02 = literal 3 bytes; 0xFE = repeat 3 times of next byte
        let input = [0x02, b'A', b'B', b'C', 0xFE, b'X', 128];
        assert_eq!(decode(&input).unwrap(), b"ABCXXX");
    }

    #[test]
    fn roundtrip() {
        let data = b"AAAAAAAABCDEEFFGGGGGGGG";
        let enc = encode(data);
        let dec = decode(&enc).unwrap();
        assert_eq!(dec, data);
    }
}
