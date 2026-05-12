use anyhow::{anyhow, Result};
use std::collections::BTreeMap;

#[derive(Debug, Clone, Default)]
pub struct CMap {
    pub code_to_unicode: BTreeMap<Vec<u8>, String>,
    pub unicode_to_code: BTreeMap<String, Vec<u8>>,
}

#[derive(Debug, Clone)]
pub struct DecodeResult {
    pub text: Option<String>,
    pub method: String,
    pub issues: Vec<String>,
}

pub fn parse_to_unicode_cmap(bytes: &[u8]) -> Result<CMap> {
    let text = String::from_utf8_lossy(bytes);
    let mut cmap = CMap::default();
    let mut lines = text.lines().peekable();
    while let Some(line) = lines.next() {
        if line.contains("beginbfchar") {
            while let Some(entry) = lines.next() {
                if entry.contains("endbfchar") { break; }
                let tokens = hex_tokens(entry);
                if tokens.len() >= 2 {
                    insert_mapping(&mut cmap, &tokens[0], &tokens[1]);
                }
            }
        } else if line.contains("beginbfrange") {
            while let Some(entry) = lines.next() {
                if entry.contains("endbfrange") { break; }
                parse_bfrange_line(&mut cmap, entry);
            }
        }
    }
    if cmap.code_to_unicode.is_empty() {
        return Err(anyhow!("ToUnicode CMap did not contain bfchar/bfrange mappings"));
    }
    Ok(cmap)
}

pub fn decode_with_cmap(encoded: &str, cmap: &CMap) -> DecodeResult {
    let bytes = match operand_bytes(encoded) {
        Ok(value) => value,
        Err(err) => return DecodeResult { text: None, method: "to-unicode-cmap".to_string(), issues: vec![err.to_string()] },
    };
    let mut index = 0;
    let mut output = String::new();
    let mut issues = Vec::new();
    while index < bytes.len() {
        let mut matched = None;
        for width in (1..=4).rev() {
            if index + width <= bytes.len() {
                let code = &bytes[index..index + width];
                if let Some(value) = cmap.code_to_unicode.get(code) {
                    matched = Some((width, value.clone()));
                    break;
                }
            }
        }
        if let Some((width, value)) = matched {
            output.push_str(&value);
            index += width;
        } else {
            issues.push(format!("missing CMap mapping at byte offset {index}"));
            index += 1;
        }
    }
    DecodeResult { text: Some(output), method: "to-unicode-cmap".to_string(), issues }
}

pub fn encode_with_cmap(text: &str, cmap: &CMap) -> Result<String> {
    let mut bytes = Vec::new();
    for ch in text.chars() {
        let key = ch.to_string();
        let code = cmap.unicode_to_code.get(&key).ok_or_else(|| anyhow!("missing reverse CMap mapping for {key}"))?;
        bytes.extend(code);
    }
    Ok(format!("<{}>", hex::encode_upper(bytes)))
}

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
    if original_encoded.starts_with('[') && original_encoded.ends_with(']') {
        if translated.is_ascii() {
            return Ok(format!("[({})]", escape_literal_string(translated)));
        }
        return Err(anyhow!("non-ASCII translation cannot be encoded as original TJ array without an explicit mapping"));
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

fn parse_bfrange_line(cmap: &mut CMap, line: &str) {
    let tokens = hex_tokens(line);
    if tokens.len() < 3 {
        return;
    }
    let Ok(start) = hex::decode(&tokens[0]) else { return; };
    let Ok(end) = hex::decode(&tokens[1]) else { return; };
    let start_value = bytes_to_number(&start);
    let end_value = bytes_to_number(&end);
    if line.contains('[') {
        for (offset, token) in tokens.iter().skip(2).enumerate() {
            let code = number_to_bytes(start_value + offset as u32, start.len());
            insert_mapping(cmap, &hex::encode_upper(code), token);
        }
    } else {
        let Ok(target) = hex::decode(&tokens[2]) else { return; };
        let target_value = bytes_to_number(&target);
        for value in start_value..=end_value {
            let code = number_to_bytes(value, start.len());
            let unicode = number_to_bytes(target_value + (value - start_value), target.len());
            insert_mapping(cmap, &hex::encode_upper(code), &hex::encode_upper(unicode));
        }
    }
}

fn insert_mapping(cmap: &mut CMap, code_hex: &str, unicode_hex: &str) {
    let Ok(code) = hex::decode(normalize_hex(code_hex)) else { return; };
    let Ok(unicode_bytes) = hex::decode(normalize_hex(unicode_hex)) else { return; };
    let text = decode_utf16be(&unicode_bytes);
    cmap.code_to_unicode.insert(code.clone(), text.clone());
    cmap.unicode_to_code.entry(text).or_insert(code);
}

fn operand_bytes(encoded: &str) -> Result<Vec<u8>> {
    if encoded.starts_with('<') && encoded.ends_with('>') && !encoded.starts_with("<<") {
        return Ok(hex::decode(normalize_hex(&encoded[1..encoded.len() - 1]))?);
    }
    Err(anyhow!("ToUnicode decode currently supports hex string operands"))
}

fn hex_tokens(line: &str) -> Vec<String> {
    let mut tokens = Vec::new();
    let bytes = line.as_bytes();
    let mut index = 0;
    while index < bytes.len() {
        if bytes[index] == b'<' && index + 1 < bytes.len() && bytes[index + 1] != b'<' {
            let start = index + 1;
            index += 1;
            while index < bytes.len() && bytes[index] != b'>' {
                index += 1;
            }
            if index < bytes.len() {
                tokens.push(String::from_utf8_lossy(&bytes[start..index]).to_string());
            }
        }
        index += 1;
    }
    tokens
}

fn normalize_hex(value: &str) -> String {
    let mut value = value.chars().filter(|ch| !ch.is_whitespace()).collect::<String>();
    if value.len() % 2 == 1 {
        value.push('0');
    }
    value
}

fn bytes_to_number(bytes: &[u8]) -> u32 {
    bytes.iter().fold(0, |acc, byte| (acc << 8) | *byte as u32)
}

fn number_to_bytes(value: u32, width: usize) -> Vec<u8> {
    (0..width).rev().map(|shift| ((value >> (shift * 8)) & 0xff) as u8).collect()
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
