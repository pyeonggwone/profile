//! ICC-based color management.
//!
//! Backed by `qcms`, the pure-Rust ICC profile transform from the
//! Servo project. PDF doesn't know about ICC math; `qcms` interprets
//! the bytes of an ICC profile and produces transforms.
//!
//! Typical use here: convert a CMYK / Lab / non-sRGB image stream into
//! sRGB so the browser can display it.

use qcms::{DataType, Intent, Profile, Transform};

#[derive(Debug, Clone, Copy)]
pub enum PixelFormat {
    Rgb8,
    Rgba8,
    Cmyk,
    Gray8,
}

impl PixelFormat {
    fn data_type(self) -> DataType {
        match self {
            PixelFormat::Rgb8 => DataType::RGB8,
            PixelFormat::Rgba8 => DataType::RGBA8,
            PixelFormat::Cmyk => DataType::CMYK,
            PixelFormat::Gray8 => DataType::Gray8,
        }
    }
}

pub struct ColorTransform {
    inner: Transform,
}

impl ColorTransform {
    /// Build a transform from a source ICC profile to sRGB.
    pub fn to_srgb(
        source_icc: &[u8],
        source_format: PixelFormat,
        dest_format: PixelFormat,
    ) -> Option<Self> {
        let src = Profile::new_from_slice(source_icc, false)?;
        let mut dst = Profile::new_sRGB();
        dst.precache_output_transform();
        let inner = Transform::new_to(
            &src,
            &dst,
            source_format.data_type(),
            dest_format.data_type(),
            Intent::Perceptual,
        )?;
        Some(Self { inner })
    }

    /// Apply the transform in place. The buffer must already be sized
    /// for the destination format (qcms reads and writes through the
    /// same slice, expanding pixel groups as configured by the
    /// transform).
    pub fn apply_in_place(&self, data: &mut [u8]) {
        self.inner.apply(data);
    }
}
