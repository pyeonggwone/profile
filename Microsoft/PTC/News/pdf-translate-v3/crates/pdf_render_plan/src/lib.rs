//! pdf_render_plan
//!
//! Builds a JSON-friendly intermediate representation of a PDF page that
//! the browser Canvas viewer can render directly. The browser does not
//! parse PDFs — see `build/09-web-viewer-editor/DESIGN.md`.

#![forbid(unsafe_code)]

use pdf_core::PdfResult;
use pdf_analysis::{extract_text, PageText};
use pdf_reader::ParsedPdf;

#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone)]
#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
#[cfg_attr(feature = "serde", serde(tag = "op", rename_all = "camelCase"))]
pub enum RenderCommand {
    Text {
        text: String,
        x: f32,
        y: f32,
        font_size: f32,
        font_resource: Option<String>,
    },
}

#[derive(Debug, Clone)]
#[cfg_attr(feature = "serde", derive(Serialize, Deserialize))]
#[cfg_attr(feature = "serde", serde(rename_all = "camelCase"))]
pub struct PageRenderPlan {
    pub page: u32,
    pub width: f32,
    pub height: f32,
    pub commands: Vec<RenderCommand>,
}

pub fn build_render_plan(doc: &ParsedPdf) -> PdfResult<Vec<PageRenderPlan>> {
    let pages = extract_text(doc)?;
    Ok(pages.into_iter().map(plan_for_page).collect())
}

fn plan_for_page(page: PageText) -> PageRenderPlan {
    let commands = page
        .runs
        .into_iter()
        .map(|r| RenderCommand::Text {
            text: r.text,
            x: r.x,
            y: page.height - r.y, // convert to top-left origin for the browser
            font_size: r.font_size,
            font_resource: r.font_resource,
        })
        .collect();
    PageRenderPlan {
        page: page.page,
        width: page.width,
        height: page.height,
        commands,
    }
}
