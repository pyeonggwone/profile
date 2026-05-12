//! Low-level byte cursor and tokenizer for PDF.
//!
//! The PDF grammar is whitespace-delimited and supports comments
//! (`%` to end-of-line). This module provides primitive helpers shared
//! by both `object_parser` and `xref`.

use pdf_core::{PdfError, PdfResult};

#[inline]
pub fn is_whitespace(b: u8) -> bool {
    matches!(b, 0 | b'\t' | b'\n' | 0x0C | b'\r' | b' ')
}

#[inline]
pub fn is_delimiter(b: u8) -> bool {
    matches!(
        b,
        b'(' | b')' | b'<' | b'>' | b'[' | b']' | b'{' | b'}' | b'/' | b'%'
    )
}

#[inline]
pub fn is_regular(b: u8) -> bool {
    !is_whitespace(b) && !is_delimiter(b)
}

/// Cursor into the original PDF buffer.
#[derive(Clone)]
pub struct Cursor<'a> {
    pub data: &'a [u8],
    pub pos: usize,
}

impl<'a> Cursor<'a> {
    pub fn new(data: &'a [u8]) -> Self {
        Self { data, pos: 0 }
    }

    pub fn at(data: &'a [u8], pos: usize) -> Self {
        Self { data, pos }
    }

    pub fn remaining(&self) -> &'a [u8] {
        &self.data[self.pos..]
    }

    pub fn peek(&self) -> Option<u8> {
        self.data.get(self.pos).copied()
    }

    pub fn peek_at(&self, off: usize) -> Option<u8> {
        self.data.get(self.pos + off).copied()
    }

    pub fn advance(&mut self, n: usize) {
        self.pos = self.pos.saturating_add(n).min(self.data.len());
    }

    pub fn eof(&self) -> bool {
        self.pos >= self.data.len()
    }

    /// Skip whitespace and `%`-comments.
    pub fn skip_ws_and_comments(&mut self) {
        loop {
            while let Some(b) = self.peek() {
                if is_whitespace(b) {
                    self.pos += 1;
                } else {
                    break;
                }
            }
            if self.peek() == Some(b'%') {
                while let Some(b) = self.peek() {
                    self.pos += 1;
                    if b == b'\n' || b == b'\r' {
                        break;
                    }
                }
                continue;
            }
            break;
        }
    }

    /// Skip plain whitespace only (no comment handling) — used inside
    /// content/stream contexts where `%` is not a comment.
    pub fn skip_ws_only(&mut self) {
        while let Some(b) = self.peek() {
            if is_whitespace(b) {
                self.pos += 1;
            } else {
                break;
            }
        }
    }

    pub fn match_keyword(&mut self, kw: &[u8]) -> bool {
        if self.remaining().starts_with(kw) {
            // Ensure word boundary
            let after = self.data.get(self.pos + kw.len()).copied();
            let boundary = after
                .map(|b| is_whitespace(b) || is_delimiter(b))
                .unwrap_or(true);
            if boundary {
                self.pos += kw.len();
                return true;
            }
        }
        false
    }

    pub fn read_regular_token(&mut self) -> &'a [u8] {
        let start = self.pos;
        while let Some(b) = self.peek() {
            if is_regular(b) {
                self.pos += 1;
            } else {
                break;
            }
        }
        &self.data[start..self.pos]
    }

    pub fn expect_byte(&mut self, expected: u8) -> PdfResult<()> {
        match self.peek() {
            Some(b) if b == expected => {
                self.pos += 1;
                Ok(())
            }
            _ => Err(PdfError::UnexpectedEof(self.pos)),
        }
    }
}
