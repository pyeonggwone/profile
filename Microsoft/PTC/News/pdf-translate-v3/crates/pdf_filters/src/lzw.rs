//! LZWDecode (PDF spec 7.4.4). Direct implementation per
//! `build/04-stream-filters/DESIGN.md`.
//!
//! - Initial code size: 9 bits
//! - Clear code: 256
//! - End-of-data: 257
//! - Code size grows when the dictionary fills, with PDF "early change"
//!   semantics.

use pdf_core::{PdfError, PdfResult};

const CLEAR: u16 = 256;
const EOD: u16 = 257;

struct BitReader<'a> {
    data: &'a [u8],
    bit_pos: usize,
}

impl<'a> BitReader<'a> {
    fn new(data: &'a [u8]) -> Self {
        Self { data, bit_pos: 0 }
    }

    fn read(&mut self, n: u32) -> Option<u32> {
        let total_bits = self.data.len() * 8;
        if self.bit_pos + n as usize > total_bits {
            return None;
        }
        let mut value: u32 = 0;
        for _ in 0..n {
            let byte = self.data[self.bit_pos / 8];
            let bit = (byte >> (7 - (self.bit_pos % 8))) & 1;
            value = (value << 1) | bit as u32;
            self.bit_pos += 1;
        }
        Some(value)
    }
}

pub fn decode(input: &[u8], early_change: bool) -> PdfResult<Vec<u8>> {
    let mut reader = BitReader::new(input);
    let mut dict: Vec<Vec<u8>> = Vec::with_capacity(4096);
    reset_dict(&mut dict);
    let mut code_size: u32 = 9;
    let mut prev: Option<Vec<u8>> = None;
    let mut out: Vec<u8> = Vec::with_capacity(input.len() * 2);

    let bump_threshold = |size: u32, early: bool| -> usize {
        let cap = 1usize << size;
        if early {
            cap - 1
        } else {
            cap
        }
    };

    while let Some(code32) = reader.read(code_size) {
        let code = code32 as u16;
        if code == EOD {
            break;
        }
        if code == CLEAR {
            reset_dict(&mut dict);
            code_size = 9;
            prev = None;
            continue;
        }

        let entry: Vec<u8> = if (code as usize) < dict.len() {
            dict[code as usize].clone()
        } else if (code as usize) == dict.len() {
            // KwKwK case
            let mut e = prev
                .clone()
                .ok_or_else(|| PdfError::FilterDecode {
                    filter: "LZWDecode".into(),
                    reason: "KwKwK before any prior code".into(),
                })?;
            e.push(e[0]);
            e
        } else {
            return Err(PdfError::FilterDecode {
                filter: "LZWDecode".into(),
                reason: format!("code {code} out of range"),
            });
        };

        out.extend_from_slice(&entry);

        if let Some(p) = prev.take() {
            let mut new_entry = p;
            new_entry.push(entry[0]);
            dict.push(new_entry);
            if dict.len() == bump_threshold(code_size, early_change) && code_size < 12 {
                code_size += 1;
            }
        }
        prev = Some(entry);
    }
    Ok(out)
}

fn reset_dict(dict: &mut Vec<Vec<u8>>) {
    dict.clear();
    for i in 0u16..256 {
        dict.push(vec![i as u8]);
    }
    dict.push(Vec::new()); // CLEAR
    dict.push(Vec::new()); // EOD
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn decode_clear_then_eod_yields_empty() {
        // 9-bit codes: 256 (CLEAR) = 1_0000_0000, 257 (EOD) = 1_0000_0001
        // Bit-packed big-endian, padded to byte boundary.
        // bits: 100000000 100000001 -> 0x80 0x40 0x40 with trailing pad
        let bits: Vec<bool> = [
            (0b100000000u32, 9),
            (0b100000001u32, 9),
        ]
        .iter()
        .flat_map(|&(v, n)| (0..n).rev().map(move |i| (v >> i) & 1 == 1))
        .collect();
        let mut bytes = vec![0u8; (bits.len() + 7) / 8];
        for (i, b) in bits.iter().enumerate() {
            if *b {
                bytes[i / 8] |= 1 << (7 - (i % 8));
            }
        }
        assert_eq!(decode(&bytes, true).unwrap(), Vec::<u8>::new());
    }
}
