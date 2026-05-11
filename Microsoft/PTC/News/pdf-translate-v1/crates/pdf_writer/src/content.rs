//! Build PDF content streams from semantic edit operations.
//!
//! `ContentStreamBuilder` produces PDF graphics/text operator bytes such
//! as the `q ... BT /F1 12 Tf 1 0 0 1 x y Tm (text) Tj ET ... Q` block
//! described in `build/06-pdf-writer/DESIGN.md`.

use std::io::Write;

#[derive(Default)]
pub struct ContentStreamBuilder {
    bytes: Vec<u8>,
}

impl ContentStreamBuilder {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn save_state(mut self) -> Self {
        self.bytes.extend_from_slice(b"q\n");
        self
    }

    pub fn restore_state(mut self) -> Self {
        self.bytes.extend_from_slice(b"Q\n");
        self
    }

    pub fn set_rgb_fill(mut self, r: f32, g: f32, b: f32) -> Self {
        let _ = write!(&mut self.bytes, "{r:.3} {g:.3} {b:.3} rg\n");
        self
    }

    pub fn add_text(mut self, font_resource: &str, size: f32, x: f32, y: f32, text: &str) -> Self {
        self.bytes.extend_from_slice(b"BT\n");
        let _ = write!(&mut self.bytes, "/{font_resource} {size} Tf\n");
        let _ = write!(&mut self.bytes, "1 0 0 1 {x:.3} {y:.3} Tm\n");
        self.bytes.push(b'(');
        for &c in text.as_bytes() {
            match c {
                b'(' => self.bytes.extend_from_slice(b"\\("),
                b')' => self.bytes.extend_from_slice(b"\\)"),
                b'\\' => self.bytes.extend_from_slice(b"\\\\"),
                b'\r' => self.bytes.extend_from_slice(b"\\r"),
                b'\n' => self.bytes.extend_from_slice(b"\\n"),
                other => self.bytes.push(other),
            }
        }
        self.bytes.extend_from_slice(b") Tj\n");
        self.bytes.extend_from_slice(b"ET\n");
        self
    }

    /// Add Unicode text using a Type0 / CIDFontType2 font. `hex_string`
    /// must be a `<...>` hex literal whose bytes are 2-byte big-endian
    /// CID values, as produced by `EmbeddedFont::encode_to_hex`.
    pub fn add_text_unicode(
        mut self,
        font_resource: &str,
        size: f32,
        x: f32,
        y: f32,
        hex_string: &str,
    ) -> Self {
        self.bytes.extend_from_slice(b"BT\n");
        let _ = write!(&mut self.bytes, "/{font_resource} {size} Tf\n");
        let _ = write!(&mut self.bytes, "1 0 0 1 {x:.3} {y:.3} Tm\n");
        self.bytes.extend_from_slice(hex_string.as_bytes());
        self.bytes.extend_from_slice(b" Tj\n");
        self.bytes.extend_from_slice(b"ET\n");
        self
    }

    /// Draw an image XObject. The image is positioned with a `cm`
    /// transform that places it at `(x, y)` with the given pixel
    /// dimensions, then drawn with `Do`.
    ///
    /// `image_resource` is the name under which the image XObject was
    /// added to the page's `/Resources/XObject` dictionary.
    pub fn draw_image(
        mut self,
        image_resource: &str,
        x: f32,
        y: f32,
        width: f32,
        height: f32,
    ) -> Self {
        self.bytes.extend_from_slice(b"q\n");
        // PDF cm: width 0 0 height x y cm
        let _ = write!(
            &mut self.bytes,
            "{width:.3} 0 0 {height:.3} {x:.3} {y:.3} cm\n"
        );
        let _ = write!(&mut self.bytes, "/{image_resource} Do\n");
        self.bytes.extend_from_slice(b"Q\n");
        self
    }

    pub fn finish(self) -> Vec<u8> {
        self.bytes
    }
}
