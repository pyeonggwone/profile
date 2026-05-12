use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PdfSource {
    pub name: String,
    pub size_bytes: u64,
    pub sha256: String,
    pub path: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct JobState {
    pub job_id: String,
    pub source: PdfSource,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct RawPdfTextState {
    pub pages: Vec<RawPage>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RawPage {
    pub page: u32,
    pub contents: Vec<RawContentStream>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RawContentStream {
    pub stream_xref: u32,
    pub text_runs: Vec<RawTextRun>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RawTextRun {
    pub id: String,
    pub restore_options: RestoreOptions,
    pub text_payload: TextPayload,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RestoreOptions {
    pub stream_xref: u32,
    pub operator: String,
    pub operand_range: ByteRange,
    pub text_block_range: Option<ByteRange>,
    pub operator_sequence: Vec<OperatorSnapshot>,
    pub text_state: TextState,
    pub font_state: FontState,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ByteRange {
    pub start: usize,
    pub end: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OperatorSnapshot {
    pub op: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub font: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub size: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub matrix: Option<[f64; 6]>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct TextState {
    pub font: Option<String>,
    pub font_size: Option<f64>,
    pub text_matrix: Option<[f64; 6]>,
    pub line_matrix: Option<[f64; 6]>,
    pub char_spacing: f64,
    pub word_spacing: f64,
    pub horizontal_scaling: f64,
    pub leading: f64,
    pub render_mode: i32,
    pub rise: f64,
}

impl Default for TextState {
    fn default() -> Self {
        Self {
            font: None,
            font_size: None,
            text_matrix: None,
            line_matrix: None,
            char_spacing: 0.0,
            word_spacing: 0.0,
            horizontal_scaling: 100.0,
            leading: 0.0,
            render_mode: 0,
            rise: 0.0,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct FontState {
    pub resource_name: Option<String>,
    pub font_object_ref: Option<String>,
    pub subtype: Option<String>,
    pub base_font: Option<String>,
    pub encoding: Option<String>,
    pub to_unicode_ref: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct TextPayload {
    pub encoded_original: String,
    pub decoded_original: Option<String>,
    pub decoded_translated: Option<String>,
    pub replacement_encoded: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ReadableTextState {
    pub items: Vec<ReadableItem>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ReadableItem {
    pub id: String,
    pub page: u32,
    pub source: String,
    pub restore_options_ref: RestoreOptionsRef,
    pub decode: DecodeStatus,
    pub layout: LayoutInfo,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RestoreOptionsRef {
    pub stream_xref: u32,
    pub operator: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DecodeStatus {
    pub method: String,
    pub confidence: String,
    pub issues: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct LayoutInfo {
    pub matrix: Option<[f64; 6]>,
    pub bbox: Option<[f64; 4]>,
    pub estimated_width: Option<f64>,
    pub font_size: Option<f64>,
    pub horizontal_scaling: Option<f64>,
    pub source_visual_units: Option<f64>,
    pub spacing_visual_units: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct LayoutLimit {
    pub max_visual_units: f64,
    pub max_hangul_chars: usize,
    pub source_visual_units: f64,
    pub spacing_visual_units: f64,
    pub font_size: f64,
    pub safety_ratio: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct TranslationInput {
    pub items: Vec<TranslationInputItem>,
    pub terms: Vec<JobTerm>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct TranslationInputItem {
    pub id: String,
    pub text: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub layout_limit: Option<LayoutLimit>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct TranslationResults {
    pub items: Vec<TranslationResultItem>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TranslationResultItem {
    pub id: String,
    pub translated: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct PdfInputTextState {
    #[serde(rename = "textRuns")]
    pub text_runs: Vec<PdfInputTextRun>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct PdfInputTextRun {
    pub id: String,
    pub restore_options: RestoreOptions,
    pub text_payload: TextPayload,
    pub encode: EncodeStatus,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EncodeStatus {
    pub method: String,
    pub status: String,
    pub issues: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct ProperNounCandidates {
    pub candidates: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
pub struct JobTerms {
    pub terms: Vec<JobTerm>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JobTerm {
    pub term: String,
    pub translation: Option<String>,
    pub mode: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct RebuildReport {
    pub ok: bool,
    pub replaced: usize,
    pub failed: Vec<ReportIssue>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ValidationReport {
    pub ok: bool,
    pub command: String,
    pub exit_code: Option<i32>,
    pub stdout: String,
    pub stderr: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ReportIssue {
    #[serde(default)]
    pub id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub stage: Option<String>,
    #[serde(default)]
    pub code: String,
    #[serde(default)]
    pub severity: String,
    pub message: String,
    #[serde(default)]
    pub recoverable: bool,
}
