//! Primitive serializer (PDF spec §7.3, §7.5).
//!
//! Produces deterministic, byte-stable PDF source for any `PdfObject`.

use std::io::Write;

use pdf_core::{
    ObjectId, PdfDict, PdfError, PdfNumber, PdfObject, PdfResult, PdfStream, PdfString,
};

pub fn write_object<W: Write>(w: &mut W, id: ObjectId, value: &PdfObject) -> PdfResult<()> {
    write!(w, "{} {} obj\n", id.number, id.generation).map_err(io)?;
    write_value(w, value)?;
    w.write_all(b"\nendobj\n").map_err(io)?;
    Ok(())
}

pub fn write_value<W: Write>(w: &mut W, value: &PdfObject) -> PdfResult<()> {
    match value {
        PdfObject::Null => w.write_all(b"null").map_err(io)?,
        PdfObject::Boolean(true) => w.write_all(b"true").map_err(io)?,
        PdfObject::Boolean(false) => w.write_all(b"false").map_err(io)?,
        PdfObject::Number(n) => write_number(w, *n)?,
        PdfObject::Name(name) => write_name(w, name)?,
        PdfObject::String(PdfString::Literal(b)) => write_literal_string(w, b)?,
        PdfObject::String(PdfString::Hex(b)) => write_hex_string(w, b)?,
        PdfObject::Array(arr) => {
            w.write_all(b"[").map_err(io)?;
            for (i, v) in arr.iter().enumerate() {
                if i > 0 {
                    w.write_all(b" ").map_err(io)?;
                }
                write_value(w, v)?;
            }
            w.write_all(b"]").map_err(io)?;
        }
        PdfObject::Dict(d) => write_dict(w, d)?,
        PdfObject::Stream(s) => write_stream(w, s)?,
        PdfObject::Reference(r) => {
            write!(w, "{} {} R", r.id.number, r.id.generation).map_err(io)?
        }
    }
    Ok(())
}

fn write_number<W: Write>(w: &mut W, n: PdfNumber) -> PdfResult<()> {
    match n {
        PdfNumber::Integer(i) => write!(w, "{i}").map_err(io)?,
        PdfNumber::Real(r) => {
            if r.fract() == 0.0 && r.is_finite() {
                write!(w, "{r:.1}").map_err(io)?;
            } else {
                // Strip trailing zeros from `{r:.6}` to keep streams tight.
                let s = format!("{r:.6}");
                let trimmed = s.trim_end_matches('0').trim_end_matches('.');
                w.write_all(trimmed.as_bytes()).map_err(io)?;
            }
        }
    }
    Ok(())
}

fn write_name<W: Write>(w: &mut W, name: &[u8]) -> PdfResult<()> {
    w.write_all(b"/").map_err(io)?;
    for &b in name {
        if b <= 0x20 || b >= 0x7F || matches!(b, b'#' | b'/' | b'(' | b')' | b'<' | b'>' | b'[' | b']' | b'{' | b'}' | b'%') {
            write!(w, "#{:02X}", b).map_err(io)?;
        } else {
            w.write_all(&[b]).map_err(io)?;
        }
    }
    Ok(())
}

fn write_literal_string<W: Write>(w: &mut W, b: &[u8]) -> PdfResult<()> {
    w.write_all(b"(").map_err(io)?;
    for &c in b {
        match c {
            b'(' => w.write_all(b"\\(").map_err(io)?,
            b')' => w.write_all(b"\\)").map_err(io)?,
            b'\\' => w.write_all(b"\\\\").map_err(io)?,
            b'\n' => w.write_all(b"\\n").map_err(io)?,
            b'\r' => w.write_all(b"\\r").map_err(io)?,
            b'\t' => w.write_all(b"\\t").map_err(io)?,
            0x08 => w.write_all(b"\\b").map_err(io)?,
            0x0C => w.write_all(b"\\f").map_err(io)?,
            other => w.write_all(&[other]).map_err(io)?,
        }
    }
    w.write_all(b")").map_err(io)?;
    Ok(())
}

fn write_hex_string<W: Write>(w: &mut W, b: &[u8]) -> PdfResult<()> {
    const HEX: &[u8; 16] = b"0123456789ABCDEF";
    w.write_all(b"<").map_err(io)?;
    for &c in b {
        w.write_all(&[HEX[(c >> 4) as usize], HEX[(c & 0x0F) as usize]])
            .map_err(io)?;
    }
    w.write_all(b">").map_err(io)?;
    Ok(())
}

pub fn write_dict<W: Write>(w: &mut W, dict: &PdfDict) -> PdfResult<()> {
    w.write_all(b"<<").map_err(io)?;
    for (k, v) in dict {
        w.write_all(b" ").map_err(io)?;
        write_name(w, k)?;
        w.write_all(b" ").map_err(io)?;
        write_value(w, v)?;
    }
    w.write_all(b" >>").map_err(io)?;
    Ok(())
}

fn write_stream<W: Write>(w: &mut W, s: &PdfStream) -> PdfResult<()> {
    write_dict(w, &s.dict)?;
    w.write_all(b"\nstream\n").map_err(io)?;
    w.write_all(&s.raw_data).map_err(io)?;
    w.write_all(b"\nendstream").map_err(io)?;
    Ok(())
}

fn io(e: std::io::Error) -> PdfError {
    PdfError::Write(e.to_string())
}
