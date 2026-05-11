use anyhow::{anyhow, Result};

pub fn decode_pdf_operand(encoded: &str) -> (Option<String>, String, Vec<String>) {
    if encoded.starts_with('<') && encoded.ends_with('>') && !encoded.starts_with("<<") {
        return decode_hex_string(encoded);
    }
    if encoded.starts_with('(') && encoded.ends_with(')') {
        return (Some(decode_literal_string(encoded)), "literal-string".to_string(), Vec::new());
    }
    if encoded.starts_with('[') && encoded.ends_with(']') {
        let mut output = String::new();
        let mut issues = Vec::new();
        for part in extract_text_operands_from_tj_array(encoded) {
            let (decoded, _, mut part_issues) = decode_pdf_operand(&part);
            if let Some(text) = decoded {
                output.push_str(&text);
            }
            issues.append(&mut part_issues);
        }
        return (Some(output), "tj-array".to_string(), issues);
    }
    (None, "unknown".to_string(), vec!["unsupported operand encoding".to_string()])
}

pub fn encode_replacement_like(original_encoded: &str, translated: &str) -> Result<String> {
    if original_encoded.starts_with('<') && original_encoded.ends_with('>') && !original_encoded.starts_with("<<") {
        if translated.is_ascii() {
            return Ok(format!("<{}>", hex::encode_upper(translated.as_bytes())));
        }
        return Err(anyhow!(
            "non-ASCII translation cannot be encoded with the original simple font/CMap without an explicit mapping"
        ));
    }
    if original_encoded.starts_with('(') && original_encoded.ends_with(')') {
        if translated.is_ascii() {
            return Ok(format!("({})", escape_literal_string(translated)));
        }
        return Err(anyhow!("non-ASCII translation cannot be encoded as original literal string"));
    }
    Err(anyhow!("unsupported original operand encoding"))
}

fn decode_hex_string(encoded: &str) -> (Option<String>, String, Vec<String>) {
    let inner = &encoded[1..encoded.len() - 1];
    let normalized = if inner.len() % 2 == 0 { inner.to_string() } else { format!("{inner}0") };
    match hex::decode(normalized) {
        Ok(bytes) => {
            if bytes.starts_with(&[0xFE, 0xFF]) {
                return (Some(decode_utf16be(&bytes[2..])), "utf16be-bom".to_string(), Vec::new());
            }
            if bytes.iter().all(|b| b.is_ascii()) {
                return (Some(String::from_utf8_lossy(&bytes).to_string()), "ascii-hex".to_string(), Vec::new());
            }
            (None, "hex".to_string(), vec!["hex string needs ToUnicode/CMap for reliable decode".to_string()])
        }
        Err(err) => (None, "hex".to_string(), vec![format!("hex decode failed: {err}")]),
    }
}

fn decode_utf16be(bytes: &[u8]) -> String {
    let words = bytes
        .chunks_exact(2)
        .map(|chunk| u16::from_be_bytes([chunk[0], chunk[1]]))
        .collect::<Vec<_>>();
    String::from_utf16_lossy(&words)
}

fn decode_literal_string(encoded: &str) -> String {
    let inner = &encoded[1..encoded.len() - 1];
    let mut result = String::new();
    let mut chars = inner.chars();
    while let Some(ch) = chars.next() {
        if ch == '\\' {
            match chars.next() {
                Some('n') => result.push('\n'),
                Some('r') => result.push('\r'),
                Some('t') => result.push('\t'),
                Some('b') => result.push('\u{0008}'),
                Some('f') => result.push('\u{000C}'),
                Some(other) => result.push(other),
                None => break,
            }
        } else {
            result.push(ch);
        }
    }
    result
}

fn escape_literal_string(text: &str) -> String {
    text.replace('\\', "\\\\").replace('(', "\\(").replace(')', "\\)")
}

fn extract_text_operands_from_tj_array(encoded: &str) -> Vec<String> {
    let bytes = encoded.as_bytes();
    let mut values = Vec::new();
    let mut index = 0;
    while index < bytes.len() {
        match bytes[index] {
            b'<' if index + 1 < bytes.len() && bytes[index + 1] != b'<' => {
                let start = index;
                index += 1;
                while index < bytes.len() && bytes[index] != b'>' {
                    index += 1;
                }
                if index < bytes.len() {
                    values.push(String::from_utf8_lossy(&bytes[start..=index]).to_string());
                }
            }
            b'(' => {
                let start = index;
                index += 1;
                let mut escaped = false;
                while index < bytes.len() {
                    if escaped {
                        escaped = false;
                    } else if bytes[index] == b'\\' {
                        escaped = true;
                    } else if bytes[index] == b')' {
                        values.push(String::from_utf8_lossy(&bytes[start..=index]).to_string());
                        break;
                    }
                    index += 1;
                }
            }
            _ => {}
        }
        index += 1;
    }
    values
}
