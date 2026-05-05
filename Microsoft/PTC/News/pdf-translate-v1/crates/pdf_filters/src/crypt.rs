//! PDF /Encrypt support (PDF spec §7.6).
//!
//! Implements the "Standard" security handler for the algorithms
//! actually seen in the wild:
//!
//! | V | R  | Algorithm                       | Status |
//! |---|----|----------------------------------|--------|
//! | 1 | 2  | RC4, 40-bit key                  | done   |
//! | 2 | 3  | RC4, variable key length         | done   |
//! | 4 | 4  | AES-128 + per-object keys        | done   |
//! | 5 | 6  | AES-256 (Algorithm 2.B)          | stub   |
//!
//! The PDF-specific work (key derivation, per-object key, where to
//! decrypt strings vs streams) is implemented here directly. The cipher
//! primitives (MD5, RC4, AES, CBC) come from RustCrypto crates which
//! are pure-Rust source-open standard implementations.
//!
//! Per design `build/04-stream-filters/DESIGN.md`:
//! > Crypto primitives (AES, SHA, MD5) come from a standard OSS
//! > implementation. PDF-specific encryption logic is implemented here.

use aes::cipher::{block_padding::Pkcs7, BlockDecryptMut, KeyIvInit};
use md5::{Digest, Md5};
use pdf_core::{DictExt, ObjectId, PdfDict, PdfError, PdfObject, PdfResult, PdfString};

type Aes128CbcDec = cbc::Decryptor<aes::Aes128>;

/// Standard PDF password padding (PDF spec §7.6.3.3).
const PASSWORD_PAD: [u8; 32] = [
    0x28, 0xBF, 0x4E, 0x5E, 0x4E, 0x75, 0x8A, 0x41, 0x64, 0x00, 0x4E, 0x56, 0xFF, 0xFA, 0x01, 0x08,
    0x2E, 0x2E, 0x00, 0xB6, 0xD0, 0x68, 0x3E, 0x80, 0x2F, 0x0C, 0xA9, 0xFE, 0x64, 0x53, 0x69, 0x7A,
];

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CryptMethod {
    None,
    Rc4,
    Aes128,
    Aes256,
}

#[derive(Debug, Clone)]
pub struct DecryptionContext {
    pub file_key: Vec<u8>,
    pub method: CryptMethod,
    pub revision: u8,
    pub version: u8,
    pub key_length_bits: u32,
}

/// Authentication outcome from `from_trailer`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AuthResult {
    User,
    Owner,
    Failed,
}

impl DecryptionContext {
    /// Build the per-document encryption context. Returns `Ok(None)`
    /// if the document is not encrypted. Returns `Err(WrongPassword)`
    /// if a password is required and the supplied one fails.
    pub fn from_trailer(
        trailer: &PdfDict,
        encrypt: &PdfDict,
        password: &str,
    ) -> PdfResult<(Self, AuthResult)> {
        // /Filter must be /Standard (we don't implement public-key handlers).
        if let Some(PdfObject::Name(n)) = encrypt.get(b"Filter".as_ref()) {
            if n.as_slice() != b"Standard" {
                return Err(PdfError::FilterDecode {
                    filter: "Crypt".into(),
                    reason: format!(
                        "non-Standard security handler `{}`",
                        String::from_utf8_lossy(n)
                    ),
                });
            }
        }

        let v = encrypt.get_integer(b"V".as_ref()).unwrap_or(0) as u8;
        let r = encrypt.get_integer(b"R".as_ref()).unwrap_or(0) as u8;
        let length_bits = encrypt
            .get_integer(b"Length".as_ref())
            .unwrap_or(if v == 1 { 40 } else { 128 }) as u32;
        let p = encrypt
            .get_integer(b"P".as_ref())
            .ok_or_else(|| crypt_err("/Encrypt missing /P"))?;
        let o = encrypt
            .get(b"O".as_ref())
            .and_then(string_bytes)
            .ok_or_else(|| crypt_err("/Encrypt missing /O"))?;
        let u = encrypt
            .get(b"U".as_ref())
            .and_then(string_bytes)
            .ok_or_else(|| crypt_err("/Encrypt missing /U"))?;

        let id_first = trailer
            .get(b"ID".as_ref())
            .and_then(|o| match o {
                PdfObject::Array(arr) => arr.first().and_then(string_bytes),
                _ => None,
            })
            .unwrap_or_default();

        let method = match (v, r) {
            (1, _) => CryptMethod::Rc4,
            (2, _) => CryptMethod::Rc4,
            (4, _) => Self::detect_method_v4(encrypt),
            (5, _) | (_, 6) => CryptMethod::Aes256,
            _ => CryptMethod::Rc4,
        };

        if matches!(method, CryptMethod::Aes256) {
            return Err(PdfError::FilterDecode {
                filter: "Crypt".into(),
                reason: "AES-256 (V=5/R=6) not implemented yet".into(),
            });
        }

        // metadata-encrypted flag for R>=4
        let encrypt_metadata = encrypt
            .get(b"EncryptMetadata".as_ref())
            .map(|o| !matches!(o, PdfObject::Boolean(false)))
            .unwrap_or(true);

        // Try user password
        let key_bytes = (length_bits / 8) as usize;
        let user_key = derive_user_key(
            password.as_bytes(),
            &o,
            p as i32,
            &id_first,
            r,
            key_bytes,
            encrypt_metadata,
        );

        let user_check = compute_u(&user_key, r, &id_first);
        let user_match = match r {
            2 => user_check == u.as_slice(),
            _ => user_check.len().min(16) <= u.len()
                && user_check[..16] == u[..16],
        };

        let (file_key, auth) = if user_match {
            (user_key, AuthResult::User)
        } else {
            // Try treating as owner password
            match try_owner_password(
                password.as_bytes(),
                &o,
                &u,
                p as i32,
                &id_first,
                r,
                key_bytes,
                encrypt_metadata,
            ) {
                Some(k) => (k, AuthResult::Owner),
                None => {
                    return Err(PdfError::FilterDecode {
                        filter: "Crypt".into(),
                        reason: "wrong password".into(),
                    })
                }
            }
        };

        Ok((
            Self {
                file_key,
                method,
                revision: r,
                version: v,
                key_length_bits: length_bits,
            },
            auth,
        ))
    }

    fn detect_method_v4(encrypt: &PdfDict) -> CryptMethod {
        // /CF dictionary names a default crypt filter. /StmF chooses the
        // stream filter; the names "AESV2" / "V2" identify the cipher.
        let stmf = encrypt.get(b"StmF".as_ref()).and_then(|o| match o {
            PdfObject::Name(n) => Some(n.clone()),
            _ => None,
        });
        let cf = encrypt.get(b"CF".as_ref()).and_then(|o| match o {
            PdfObject::Dict(d) => Some(d.clone()),
            _ => None,
        });
        if let (Some(stmf), Some(cf)) = (stmf, cf) {
            if let Some(PdfObject::Dict(entry)) = cf.get(stmf.as_slice()) {
                if let Some(PdfObject::Name(cfm)) = entry.get(b"CFM".as_ref()) {
                    return match cfm.as_slice() {
                        b"AESV2" => CryptMethod::Aes128,
                        b"AESV3" => CryptMethod::Aes256,
                        _ => CryptMethod::Rc4,
                    };
                }
            }
        }
        // Default for V=4 with no recognised CF: AES-128.
        CryptMethod::Aes128
    }

    /// Per-object key (PDF spec §7.6.3.4).
    fn object_key(&self, obj_id: ObjectId) -> Vec<u8> {
        let mut buf: Vec<u8> = Vec::with_capacity(self.file_key.len() + 9);
        buf.extend_from_slice(&self.file_key);
        let n = obj_id.number;
        buf.push(n as u8);
        buf.push((n >> 8) as u8);
        buf.push((n >> 16) as u8);
        let g = obj_id.generation;
        buf.push(g as u8);
        buf.push((g >> 8) as u8);
        if matches!(self.method, CryptMethod::Aes128) {
            buf.extend_from_slice(b"sAlT");
        }
        let digest = Md5::digest(&buf);
        let take = (self.file_key.len() + 5).min(16);
        digest[..take].to_vec()
    }

    pub fn decrypt_string(&self, obj_id: ObjectId, bytes: Vec<u8>) -> PdfResult<Vec<u8>> {
        self.decrypt_bytes(obj_id, &bytes)
    }

    pub fn decrypt_stream(&self, obj_id: ObjectId, bytes: Vec<u8>) -> PdfResult<Vec<u8>> {
        self.decrypt_bytes(obj_id, &bytes)
    }

    fn decrypt_bytes(&self, obj_id: ObjectId, bytes: &[u8]) -> PdfResult<Vec<u8>> {
        let key = self.object_key(obj_id);
        match self.method {
            CryptMethod::Rc4 => Ok(rc4_xor(&key, bytes)),
            CryptMethod::Aes128 => {
                if bytes.len() < 16 {
                    return Err(PdfError::FilterDecode {
                        filter: "Crypt".into(),
                        reason: "AES stream shorter than IV".into(),
                    });
                }
                let (iv, ct) = bytes.split_at(16);
                let dec = Aes128CbcDec::new_from_slices(&key, iv).map_err(|e| {
                    PdfError::FilterDecode {
                        filter: "Crypt".into(),
                        reason: format!("AES init: {e}"),
                    }
                })?;
                let mut buf = ct.to_vec();
                let pt = dec
                    .decrypt_padded_mut::<Pkcs7>(&mut buf)
                    .map_err(|e| PdfError::FilterDecode {
                        filter: "Crypt".into(),
                        reason: format!("AES decrypt: {e}"),
                    })?;
                Ok(pt.to_vec())
            }
            CryptMethod::Aes256 => Err(PdfError::FilterDecode {
                filter: "Crypt".into(),
                reason: "AES-256 not implemented".into(),
            }),
            CryptMethod::None => Ok(bytes.to_vec()),
        }
    }
}

/// Algorithm 3.2 — file encryption key from user password.
fn derive_user_key(
    password: &[u8],
    o: &[u8],
    p: i32,
    id_first: &[u8],
    r: u8,
    key_bytes: usize,
    encrypt_metadata: bool,
) -> Vec<u8> {
    let mut buf: Vec<u8> = Vec::with_capacity(128);
    let padded = pad_password(password);
    buf.extend_from_slice(&padded);
    buf.extend_from_slice(o);
    buf.extend_from_slice(&p.to_le_bytes());
    buf.extend_from_slice(id_first);
    if r >= 4 && !encrypt_metadata {
        buf.extend_from_slice(&[0xFF, 0xFF, 0xFF, 0xFF]);
    }
    let mut digest: [u8; 16] = Md5::digest(&buf).into();
    if r >= 3 {
        for _ in 0..50 {
            digest = Md5::digest(&digest[..key_bytes]).into();
        }
    }
    digest[..key_bytes].to_vec()
}

fn pad_password(password: &[u8]) -> [u8; 32] {
    let mut out = [0u8; 32];
    let n = password.len().min(32);
    out[..n].copy_from_slice(&password[..n]);
    if n < 32 {
        out[n..].copy_from_slice(&PASSWORD_PAD[..32 - n]);
    }
    out
}

/// Algorithm 3.4/3.5 — produce the /U value from a candidate key.
fn compute_u(key: &[u8], r: u8, id_first: &[u8]) -> Vec<u8> {
    if r == 2 {
        // RC4 over the constant 32-byte padding.
        rc4_xor(key, &PASSWORD_PAD)
    } else {
        // R>=3: MD5(padding || ID), RC4 with key, then 19 rounds of RC4
        // with key XOR-with-counter.
        let mut h = Md5::new();
        h.update(PASSWORD_PAD);
        h.update(id_first);
        let digest = h.finalize();
        let mut data = rc4_xor(key, &digest);
        for i in 1u8..=19 {
            let xkey: Vec<u8> = key.iter().map(|b| b ^ i).collect();
            data = rc4_xor(&xkey, &data);
        }
        // PDF spec: /U is 32 bytes (the second 16 are arbitrary). Pad to 32.
        let mut out = vec![0u8; 32];
        out[..16].copy_from_slice(&data[..16]);
        out
    }
}

/// Algorithm 3.7 — try to authenticate as owner.
fn try_owner_password(
    password: &[u8],
    o: &[u8],
    u: &[u8],
    p: i32,
    id_first: &[u8],
    r: u8,
    key_bytes: usize,
    encrypt_metadata: bool,
) -> Option<Vec<u8>> {
    // Step 1: pad password and compute MD5 once (R=2) or 51 times (R>=3).
    let padded = pad_password(password);
    let mut digest: [u8; 16] = Md5::digest(padded).into();
    if r >= 3 {
        for _ in 0..50 {
            digest = Md5::digest(&digest[..key_bytes]).into();
        }
    }
    // Step 2: derive the candidate user-password padding by RC4 of /O.
    let candidate = if r == 2 {
        rc4_xor(&digest[..key_bytes], o)
    } else {
        let mut data = o.to_vec();
        for i in (0u8..=19).rev() {
            let xkey: Vec<u8> = digest[..key_bytes].iter().map(|b| b ^ i).collect();
            data = rc4_xor(&xkey, &data);
        }
        data
    };

    // Step 3: treat `candidate` as the user password, try Algorithm 3.6.
    let key = derive_user_key(&candidate, o, p, id_first, r, key_bytes, encrypt_metadata);
    let recomputed_u = compute_u(&key, r, id_first);
    let match_ok = if r == 2 {
        recomputed_u == u
    } else {
        recomputed_u.len() >= 16 && u.len() >= 16 && recomputed_u[..16] == u[..16]
    };
    if match_ok {
        Some(key)
    } else {
        None
    }
}

/// Direct RC4 (RFC compatibility). PDF only uses RC4 inside the
/// Standard security handler so we do not expose it elsewhere.
fn rc4_xor(key: &[u8], data: &[u8]) -> Vec<u8> {
    let mut s: [u8; 256] = std::array::from_fn(|i| i as u8);
    let mut j: u8 = 0;
    for i in 0..256u32 {
        j = j.wrapping_add(s[i as usize]).wrapping_add(key[(i as usize) % key.len()]);
        s.swap(i as usize, j as usize);
    }
    let mut i: u8 = 0;
    let mut j: u8 = 0;
    let mut out = Vec::with_capacity(data.len());
    for &byte in data {
        i = i.wrapping_add(1);
        j = j.wrapping_add(s[i as usize]);
        s.swap(i as usize, j as usize);
        let k = s[(s[i as usize].wrapping_add(s[j as usize])) as usize];
        out.push(byte ^ k);
    }
    out
}

/// Walk a `PdfObject` tree and decrypt any embedded strings + the
/// stream raw data using the containing object's id.
pub fn decrypt_object_in_place(
    ctx: &DecryptionContext,
    obj_id: ObjectId,
    obj: &mut PdfObject,
) -> PdfResult<()> {
    decrypt_recursive(ctx, obj_id, obj)
}

fn decrypt_recursive(
    ctx: &DecryptionContext,
    obj_id: ObjectId,
    obj: &mut PdfObject,
) -> PdfResult<()> {
    match obj {
        PdfObject::String(s) => {
            let (is_hex, bytes) = match s {
                PdfString::Literal(b) => (false, std::mem::take(b)),
                PdfString::Hex(b) => (true, std::mem::take(b)),
            };
            let decrypted = ctx.decrypt_string(obj_id, bytes)?;
            *s = if is_hex {
                PdfString::Hex(decrypted)
            } else {
                PdfString::Literal(decrypted)
            };
        }
        PdfObject::Array(arr) => {
            for v in arr.iter_mut() {
                decrypt_recursive(ctx, obj_id, v)?;
            }
        }
        PdfObject::Dict(d) => {
            for (_, v) in d.iter_mut() {
                decrypt_recursive(ctx, obj_id, v)?;
            }
        }
        PdfObject::Stream(s) => {
            for (_, v) in s.dict.iter_mut() {
                decrypt_recursive(ctx, obj_id, v)?;
            }
            let raw = std::mem::take(&mut s.raw_data);
            s.raw_data = ctx.decrypt_stream(obj_id, raw)?;
        }
        _ => {}
    }
    Ok(())
}

fn string_bytes(o: &PdfObject) -> Option<Vec<u8>> {
    match o {
        PdfObject::String(s) => Some(s.bytes().to_vec()),
        _ => None,
    }
}

fn crypt_err(msg: &str) -> PdfError {
    PdfError::FilterDecode {
        filter: "Crypt".into(),
        reason: msg.into(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rc4_known_vector() {
        // RFC 6229 test vector: key=0102030405, plaintext=00000000000000000000
        let key = [0x01, 0x02, 0x03, 0x04, 0x05];
        let pt = [0u8; 10];
        let ct = rc4_xor(&key, &pt);
        // Expected first 10 bytes of keystream: b2 39 63 05 f0 3d c0 27 cc c3 ...
        assert_eq!(
            ct,
            vec![0xb2, 0x39, 0x63, 0x05, 0xf0, 0x3d, 0xc0, 0x27, 0xcc, 0xc3]
        );
    }

    #[test]
    fn pad_short_password() {
        let p = pad_password(b"abc");
        assert_eq!(&p[..3], b"abc");
        assert_eq!(p[3], PASSWORD_PAD[0]);
    }
}
