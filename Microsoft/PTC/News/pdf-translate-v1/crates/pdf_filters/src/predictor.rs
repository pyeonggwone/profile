//! PNG/TIFF predictor post-processing for FlateDecode and LZWDecode
//! (PDF spec 7.4.4.4 + RFC 2083 §6).

use pdf_core::{DictExt, PdfDict, PdfError, PdfResult};

#[derive(Debug, Clone, Copy)]
struct Params {
    predictor: i64,
    colors: i64,
    bits_per_component: i64,
    columns: i64,
}

fn read_params(p: &PdfDict) -> Params {
    Params {
        predictor: p.get_integer(b"Predictor".as_ref()).unwrap_or(1),
        colors: p.get_integer(b"Colors".as_ref()).unwrap_or(1),
        bits_per_component: p.get_integer(b"BitsPerComponent".as_ref()).unwrap_or(8),
        columns: p.get_integer(b"Columns".as_ref()).unwrap_or(1),
    }
}

pub fn apply_predictor_decode(input: &[u8], params: &PdfDict) -> PdfResult<Vec<u8>> {
    let p = read_params(params);
    if p.predictor == 1 {
        return Ok(input.to_vec());
    }
    let bpp = ((p.colors * p.bits_per_component + 7) / 8).max(1) as usize;
    let row_bytes = ((p.columns * p.colors * p.bits_per_component + 7) / 8) as usize;

    if p.predictor == 2 {
        // TIFF predictor 2: only for 8-bit images here.
        return Err(PdfError::FilterDecode {
            filter: "Predictor".into(),
            reason: "TIFF predictor 2 not yet implemented".into(),
        });
    }

    if !(10..=15).contains(&p.predictor) {
        return Err(PdfError::FilterDecode {
            filter: "Predictor".into(),
            reason: format!("predictor {} not supported", p.predictor),
        });
    }

    // PNG predictors: 1 leading filter byte per row.
    let stride = row_bytes + 1;
    if input.len() % stride != 0 {
        return Err(PdfError::FilterDecode {
            filter: "Predictor".into(),
            reason: format!(
                "PNG predictor: input length {} not multiple of stride {}",
                input.len(),
                stride
            ),
        });
    }

    let row_count = input.len() / stride;
    let mut out = Vec::with_capacity(row_bytes * row_count);
    let mut prev_row: Vec<u8> = vec![0; row_bytes];
    let mut row: Vec<u8> = vec![0; row_bytes];

    for r in 0..row_count {
        let off = r * stride;
        let filter_type = input[off];
        let data = &input[off + 1..off + stride];
        match filter_type {
            0 => row.copy_from_slice(data),
            1 => {
                // Sub
                for i in 0..row_bytes {
                    let left = if i >= bpp { row[i - bpp] } else { 0 };
                    row[i] = data[i].wrapping_add(left);
                }
            }
            2 => {
                // Up
                for i in 0..row_bytes {
                    row[i] = data[i].wrapping_add(prev_row[i]);
                }
            }
            3 => {
                // Average
                for i in 0..row_bytes {
                    let left = if i >= bpp { row[i - bpp] } else { 0 };
                    let avg = ((left as u16 + prev_row[i] as u16) / 2) as u8;
                    row[i] = data[i].wrapping_add(avg);
                }
            }
            4 => {
                // Paeth
                for i in 0..row_bytes {
                    let left = if i >= bpp { row[i - bpp] } else { 0 };
                    let up = prev_row[i];
                    let upleft = if i >= bpp { prev_row[i - bpp] } else { 0 };
                    row[i] = data[i].wrapping_add(paeth(left, up, upleft));
                }
            }
            other => {
                return Err(PdfError::FilterDecode {
                    filter: "Predictor".into(),
                    reason: format!("unknown PNG filter type {other}"),
                })
            }
        }
        out.extend_from_slice(&row);
        std::mem::swap(&mut prev_row, &mut row);
    }
    Ok(out)
}

fn paeth(a: u8, b: u8, c: u8) -> u8 {
    let pa = (b as i32 - c as i32).abs();
    let pb = (a as i32 - c as i32).abs();
    let pc = (a as i32 + b as i32 - 2 * c as i32).abs();
    if pa <= pb && pa <= pc {
        a
    } else if pb <= pc {
        b
    } else {
        c
    }
}
