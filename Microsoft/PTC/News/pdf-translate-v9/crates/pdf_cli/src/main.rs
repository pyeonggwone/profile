use anyhow::{anyhow, Context, Result};
use clap::{Parser, Subcommand};
use pdf_models::*;
use pdf_state_db::StateDb;
use reqwest::blocking::{Client, Response};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::mpsc;
use std::thread;
use std::time::{Duration, Instant};

#[derive(Parser)]
#[command(name = "pdf-translate-v9")]
struct Cli {
    #[command(subcommand)]
    command: Option<Commands>,
}

#[derive(Subcommand)]
enum Commands {
    Run {
        input: Option<PathBuf>,
        #[arg(long)]
        source_lang: Option<String>,
        #[arg(long)]
        target_lang: Option<String>,
        #[arg(long)]
        model: Option<String>,
    },
    Extract { input: PathBuf },
    Rebuild { job: String },
    Doctor,
    Status,
    Inspect { job: String },
    Resume { job: String },
    Finalize { job: String },
}

struct Paths {
    root: PathBuf,
    job: String,
    job_root: PathBuf,
    source_pdf: PathBuf,
    qdf_pdf: PathBuf,
    raw_json: PathBuf,
    readable_json: PathBuf,
    candidates_json: PathBuf,
    terms_json: PathBuf,
    translation_input_json: PathBuf,
    translation_results_json: PathBuf,
    pdf_input_json: PathBuf,
    rebuild_report_json: PathBuf,
    validation_report_json: PathBuf,
    term_application_report_json: PathBuf,
    encode_report_json: PathBuf,
    translation_report_json: PathBuf,
    raw_completeness_report_json: PathBuf,
    qdf_reference_report_json: PathBuf,
    ocr_report_json: PathBuf,
    font_report_json: PathBuf,
    render_report_json: PathBuf,
    structure_report_json: PathBuf,
    rebuilt_pdf: PathBuf,
    output_pdf: PathBuf,
    rejected_pdf: PathBuf,
    report_bundle_dir: PathBuf,
    state_db: PathBuf,
    tm_db: PathBuf,
    terms_db: PathBuf,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct RunSummary {
    job: String,
    source_pdf: String,
    output_pdf: String,
    classification: String,
    fallback_used: bool,
    validated_pdf: Option<String>,
    rejected_pdf: Option<String>,
    source_sha256: String,
    output_sha256: Option<String>,
    degraded: bool,
    translation_error: bool,
    text_runs: usize,
    changed_text_runs: usize,
    unchanged_text_runs: usize,
    encode_ok: usize,
    encode_failed: usize,
    rebuild_ok: bool,
    rebuild_replaced: usize,
    rebuild_failed: usize,
    validation_ok: bool,
    notes: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
struct TranslationReport {
    ok: bool,
    provider: String,
    requested: usize,
    cached: usize,
    translated: usize,
    fallback: usize,
    missing_ids: Vec<String>,
    unknown_ids: Vec<String>,
    duplicate_ids: Vec<String>,
    chunks: Vec<TranslationChunkReport>,
    issues: Vec<ReportIssue>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
#[serde(rename_all = "camelCase")]
struct TranslationChunkReport {
    #[serde(default)]
    part: usize,
    #[serde(default)]
    total_parts: usize,
    chunk: usize,
    total_chunks: usize,
    status: String,
    requested: usize,
    returned: usize,
    fallback: usize,
    missing_ids: Vec<String>,
    unknown_ids: Vec<String>,
    duplicate_ids: Vec<String>,
    error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Default)]
#[serde(rename_all = "camelCase")]
struct EncodeReport {
    ok: bool,
    total: usize,
    ok_count: usize,
    failed_count: usize,
    methods: BTreeMap<String, usize>,
    issues: Vec<ReportIssue>,
}

#[derive(Debug)]
struct TranslationPartOutput {
    part: usize,
    results: TranslationResults,
    report: TranslationReport,
    degraded_errors: Vec<String>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct TermApplicationReport {
    ok: bool,
    checked_items: usize,
    violations: Vec<TermViolation>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct TermViolation {
    id: String,
    term: String,
    mode: String,
    expected: String,
    actual: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct DoctorReport {
    ok: bool,
    root: String,
    qpdf_ok: bool,
    provider: String,
    input_dir: String,
    output_dir: String,
    work_dir: String,
    glossary_ok: bool,
    state_db_ok: bool,
    tm_db_ok: bool,
    issues: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Default)]
#[serde(rename_all = "camelCase")]
struct RawCompletenessReport {
    ok: bool,
    pages: usize,
    content_streams: usize,
    text_runs: usize,
    decoded_missing: usize,
    font_resource_missing: usize,
    to_unicode_missing: usize,
    issues: Vec<ReportIssue>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct FeatureReport {
    ok: bool,
    mode: String,
    status: String,
    message: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct StructureReport {
    ok: bool,
    source_pages: usize,
    output_pages: usize,
    source_sha256: String,
    output_sha256: Option<String>,
    issues: Vec<ReportIssue>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct QdfReferenceReport {
    ok: bool,
    qdf_pdf: String,
    raw_extraction_basis: String,
    stream_xrefs: Vec<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct OcrReport {
    ok: bool,
    mode: String,
    status: String,
    provider: String,
    pages_requested: Vec<u32>,
    pages_completed: usize,
    text_items: Vec<OcrTextItem>,
    issues: Vec<ReportIssue>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct OcrTextItem {
    page: u32,
    text: String,
    bounding_box: Option<Vec<f64>>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct AzureReadResult {
    status: String,
    #[serde(default)]
    analyze_result: Option<AzureAnalyzeResult>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct AzureAnalyzeResult {
    #[serde(default)]
    read_results: Vec<AzureReadPage>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct AzureReadPage {
    #[serde(default)]
    lines: Vec<AzureReadLine>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct AzureReadLine {
    text: String,
    #[serde(default)]
    bounding_box: Option<Vec<f64>>,
}

fn main() -> Result<()> {
    let root = project_root()?;
    std::env::set_var("PDF_TRANSLATE_ROOT", &root);
    load_dotenv_file(&root.join(".env"))?;
    let cli = Cli::parse();
    match cli.command {
        Some(Commands::Run { input, source_lang, target_lang, model }) => {
            let source_lang = source_lang.unwrap_or_else(|| env_or_default("SOURCE_LANG", "en"));
            let target_lang = target_lang.unwrap_or_else(|| env_or_default("TARGET_LANG", "ko"));
            let model = model.unwrap_or_else(|| env_or_default("OPENAI_MODEL", "gpt-4o-mini"));
            run_requested_input(input.as_deref(), &source_lang, &target_lang, &model)
        }
        Some(Commands::Extract { input }) => {
            let paths = init_job(&input)?;
            extract_raw(&paths)?;
            convert_readable(&paths)?;
            Ok(())
        }
        Some(Commands::Rebuild { job }) => {
            let paths = paths_for_job(&job, None)?;
            rebuild(&paths)?;
            Ok(())
        }
        Some(Commands::Doctor) => doctor(),
        Some(Commands::Status) => status(),
        Some(Commands::Inspect { job }) => inspect(&job),
        Some(Commands::Resume { job }) => {
            let paths = paths_for_job(&job, None)?;
            let source_lang = env_or_default("SOURCE_LANG", "en");
            let target_lang = env_or_default("TARGET_LANG", "ko");
            let model = env_or_default("OPENAI_MODEL", "gpt-4o-mini");
            let summary = run_existing_job(paths, &source_lang, &target_lang, &model, true)?;
            print_summary(&summary);
            Ok(())
        }
        Some(Commands::Finalize { job }) => {
            let paths = paths_for_job(&job, None)?;
            let summary = finalize_existing_job(paths)?;
            print_summary(&summary);
            Ok(())
        }
        None => {
            let source_lang = env_or_default("SOURCE_LANG", "en");
            let target_lang = env_or_default("TARGET_LANG", "ko");
            let model = env_or_default("OPENAI_MODEL", "gpt-4o-mini");
            run_requested_input(None, &source_lang, &target_lang, &model)
        }
    }
}

fn load_dotenv_file(path: &Path) -> Result<()> {
    if !path.exists() {
        return Ok(());
    }
    let text = fs::read_to_string(path).with_context(|| format!("read {}", path.display()))?;
    for line in text.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let Some((key, value)) = line.split_once('=') else { continue; };
        let key = key.trim();
        if key.is_empty() || std::env::var_os(key).is_some() {
            continue;
        }
        let value = value.trim().trim_matches('"').trim_matches('\'');
        std::env::set_var(key, value);
    }
    Ok(())
}

fn env_or_default(key: &str, default: &str) -> String {
    std::env::var(key).ok().filter(|value| !value.trim().is_empty()).unwrap_or_else(|| default.to_string())
}

fn allow_degraded_tools() -> bool {
    if env_bool("STRICT_TOOLS") {
        return false;
    }
    env_bool("ALLOW_DEGRADED")
}

fn env_bool(key: &str) -> bool {
    std::env::var(key)
        .ok()
        .map(|value| matches!(value.trim().to_ascii_lowercase().as_str(), "1" | "true" | "yes" | "on"))
        .unwrap_or(false)
}

fn env_usize_or_default(key: &str, default: usize) -> usize {
    std::env::var(key)
        .ok()
        .and_then(|value| value.trim().parse::<usize>().ok())
        .filter(|value| *value > 0)
        .unwrap_or(default)
}

fn env_u64_or_default(key: &str, default: u64) -> u64 {
    std::env::var(key)
        .ok()
        .and_then(|value| value.trim().parse::<u64>().ok())
        .filter(|value| *value > 0)
        .unwrap_or(default)
}

fn env_f64_or_default(key: &str, default: f64) -> f64 {
    std::env::var(key)
        .ok()
        .and_then(|value| value.trim().parse::<f64>().ok())
        .filter(|value| value.is_finite() && *value >= 0.0)
        .unwrap_or(default)
}

fn run_requested_input(input: Option<&Path>, source_lang: &str, target_lang: &str, model: &str) -> Result<()> {
    let root = project_root()?;
    let runtime = runtime_paths(&root);
    let target = input.map(PathBuf::from).unwrap_or(runtime.input_dir);
    if target.is_file() {
        let summary = run_pipeline(&target, source_lang, target_lang, model)?;
        print_summary(&summary);
        return Ok(());
    }
    if target.exists() && !target.is_dir() {
        return Err(anyhow!("input path is neither a PDF file nor a directory: {}", target.display()));
    }
    run_directory(&target, source_lang, target_lang, model)
}

fn run_directory(input_dir: &Path, source_lang: &str, target_lang: &str, model: &str) -> Result<()> {
    fs::create_dir_all(input_dir).with_context(|| format!("create input directory {}", input_dir.display()))?;
    let ready_dir = input_dir.join("ready");
    let queue_dir = if ready_dir.is_dir() { ready_dir.as_path() } else { input_dir };
    let mut pdfs = Vec::new();
    for entry in fs::read_dir(queue_dir).with_context(|| format!("read input directory {}", queue_dir.display()))? {
        let path = entry?.path();
        if path.is_file() && path.extension().and_then(|value| value.to_str()).is_some_and(|ext| ext.eq_ignore_ascii_case("pdf")) {
            pdfs.push(path);
        }
    }
    pdfs.sort_by(|left, right| left.file_name().cmp(&right.file_name()));
    if pdfs.is_empty() {
        return Err(anyhow!("no PDF files found in {}", queue_dir.display()));
    }

    let mut failed = Vec::new();
    for pdf in pdfs {
        match run_pipeline(&pdf, source_lang, target_lang, model) {
            Ok(summary) => {
                archive_input(&pdf, &summary.classification)?;
                print_summary(&summary);
            }
            Err(err) => {
                archive_input(&pdf, "failed")?;
                eprintln!("failed {}: {err}", pdf.display());
                failed.push(format!("{}: {err}", pdf.display()));
            }
        }
    }
    if failed.is_empty() {
        Ok(())
    } else {
        Err(anyhow!("{} PDF file(s) failed\n{}", failed.len(), failed.join("\n")))
    }
}

fn run_pipeline(input: &Path, source_lang: &str, target_lang: &str, model: &str) -> Result<RunSummary> {
    let paths = init_job(input)?;
    run_existing_job(paths, source_lang, target_lang, model, false)
}

fn run_existing_job(paths: Paths, source_lang: &str, target_lang: &str, model: &str, resume: bool) -> Result<RunSummary> {
    let db = StateDb::open(&paths.state_db)?;
    let source = read_json::<PdfSource>(&paths.job_root.join("state/pdf-source.json"))?;
    db.upsert_job(&paths.job, &source.path, &source.sha256, "running")?;

    run_step(&db, &paths, "02_qpdf_reference", resume, || qpdf_reference(&paths))?;
    run_step(&db, &paths, "03_extract_raw_pdf_text_state", resume, || extract_raw(&paths))?;
    write_feature_reports(&paths)?;
    record_artifacts(&db, &paths, "03_extract_raw_pdf_text_state")?;
    run_step(&db, &paths, "04_convert_raw_to_readable_text_state", resume, || convert_readable(&paths))?;
    run_step(&db, &paths, "05_extract_and_apply_job_terms", resume, || extract_terms(&paths))?;
    run_step(&db, &paths, "06_translate_readable_text_state", resume, || translate(&paths, source_lang, target_lang, model))?;
    run_step(&db, &paths, "07_convert_translation_to_pdf_input_state", resume, || convert_pdf_input(&paths))?;
    run_step(&db, &paths, "08_rebuild_pdf_with_extracted_options", resume, || rebuild(&paths))?;
    run_step(&db, &paths, "09_qpdf_validate_output", resume, || validate_output(&paths))?;
    run_step(&db, &paths, "10_publish_output", resume, || publish(&paths))?;
    let summary = write_run_summary(&paths)?;
    db.upsert_job(&paths.job, &source.path, &source.sha256, &summary.classification)?;
    cleanup_work_if_requested(&paths, &summary)?;
    Ok(summary)
}

fn finalize_existing_job(paths: Paths) -> Result<RunSummary> {
    let db = StateDb::open(&paths.state_db)?;
    let source = read_json::<PdfSource>(&paths.job_root.join("state/pdf-source.json"))?;
    db.upsert_job(&paths.job, &source.path, &source.sha256, "finalizing")?;
    run_step(&db, &paths, "08_rebuild_pdf_with_extracted_options", false, || rebuild(&paths))?;
    run_step(&db, &paths, "09_qpdf_validate_output", false, || validate_output(&paths))?;
    run_step(&db, &paths, "10_publish_output", false, || publish(&paths))?;
    let summary = write_run_summary(&paths)?;
    db.upsert_job(&paths.job, &source.path, &source.sha256, &summary.classification)?;
    Ok(summary)
}

fn run_step<F>(db: &StateDb, paths: &Paths, name: &str, resume: bool, action: F) -> Result<()>
where
    F: FnOnce() -> Result<()>,
{
    if resume && step_outputs_exist(paths, name) {
        progress_line(format!("[skip] {name} existing artifacts"));
        db.set_step(&paths.job, name, "completed", Some("resume skipped existing artifacts"))?;
        record_artifacts(db, paths, name)?;
        return Ok(());
    }
    let started = Instant::now();
    progress_line(format!("[start] {name}"));
    match step(db, &paths.job, name, action) {
        Ok(()) => {
            record_artifacts(db, paths, name)?;
            progress_line(format!("[ok] {name} elapsed={}s", started.elapsed().as_secs()));
            Ok(())
        }
        Err(err) => {
            progress_line(format!("[fail] {name} elapsed={}s error={}", started.elapsed().as_secs(), error_chain(&err)));
            Err(err)
        }
    }
}

fn step_outputs_exist(paths: &Paths, name: &str) -> bool {
    match name {
        "02_qpdf_reference" => paths.job_root.join("state/qpdf-check.json").exists(),
        "03_extract_raw_pdf_text_state" => paths.raw_json.exists() && paths.raw_completeness_report_json.exists() && paths.qdf_reference_report_json.exists(),
        "04_convert_raw_to_readable_text_state" => paths.readable_json.exists(),
        "05_extract_and_apply_job_terms" => paths.terms_json.exists(),
        "06_translate_readable_text_state" => paths.translation_results_json.exists() && paths.translation_report_json.exists(),
        "07_convert_translation_to_pdf_input_state" => paths.pdf_input_json.exists() && paths.encode_report_json.exists(),
        "08_rebuild_pdf_with_extracted_options" => paths.rebuild_report_json.exists() && paths.rebuilt_pdf.exists(),
        "09_qpdf_validate_output" => paths.validation_report_json.exists(),
        "10_publish_output" => paths.output_pdf.exists() || paths.rejected_pdf.exists(),
        _ => false,
    }
}

fn print_summary(summary: &RunSummary) {
    let status = &summary.classification;
    println!(
        "{status} output={} changed={} unchanged={} encode_failed={} rebuild_ok={} validation_ok={} degraded={}",
        summary.output_pdf,
        summary.changed_text_runs,
        summary.unchanged_text_runs,
        summary.encode_failed,
        summary.rebuild_ok,
        summary.validation_ok,
        summary.degraded
    );
}

fn progress_line(message: impl AsRef<str>) {
    println!("{}", message.as_ref());
    let _ = io::stdout().flush();
}

fn step<F>(db: &StateDb, job: &str, name: &str, action: F) -> Result<()>
where
    F: FnOnce() -> Result<()>,
{
    db.set_step(job, name, "running", None)?;
    match action() {
        Ok(()) => {
            db.set_step(job, name, "completed", None)?;
            Ok(())
        }
        Err(err) => {
            db.set_step(job, name, "failed", Some(&err.to_string()))?;
            Err(err)
        }
    }
}

fn record_artifacts(db: &StateDb, paths: &Paths, step_name: &str) -> Result<()> {
    let artifacts: Vec<(&str, PathBuf)> = match step_name {
        "02_qpdf_reference" => vec![("qdf-pdf", paths.qdf_pdf.clone()), ("qpdf-check", paths.job_root.join("state/qpdf-check.json"))],
        "03_extract_raw_pdf_text_state" => vec![
            ("raw-json", paths.raw_json.clone()),
            ("raw-completeness-report", paths.raw_completeness_report_json.clone()),
            ("qdf-reference-report", paths.qdf_reference_report_json.clone()),
            ("ocr-report", paths.ocr_report_json.clone()),
            ("font-report", paths.font_report_json.clone()),
            ("render-report", paths.render_report_json.clone()),
        ],
        "04_convert_raw_to_readable_text_state" => vec![("readable-json", paths.readable_json.clone())],
        "05_extract_and_apply_job_terms" => vec![("proper-noun-candidates", paths.candidates_json.clone()), ("terms-json", paths.terms_json.clone())],
        "06_translate_readable_text_state" => vec![
            ("translation-input", paths.translation_input_json.clone()),
            ("translation-results", paths.translation_results_json.clone()),
            ("translation-report", paths.translation_report_json.clone()),
            ("term-application-report", paths.term_application_report_json.clone()),
        ],
        "07_convert_translation_to_pdf_input_state" => vec![("pdf-input-json", paths.pdf_input_json.clone()), ("encode-report", paths.encode_report_json.clone())],
        "08_rebuild_pdf_with_extracted_options" => vec![("rebuilt-pdf", paths.rebuilt_pdf.clone()), ("rebuild-report", paths.rebuild_report_json.clone())],
        "09_qpdf_validate_output" => vec![("validation-report", paths.validation_report_json.clone()), ("structure-report", paths.structure_report_json.clone())],
        "10_publish_output" => vec![("validated-pdf", paths.output_pdf.clone()), ("rejected-pdf", paths.rejected_pdf.clone()), ("report-bundle", paths.report_bundle_dir.clone())],
        _ => Vec::new(),
    };
    for (kind, path) in artifacts {
        if path.exists() {
            db.add_artifact(&paths.job, kind, &relative(&path, &paths.root))?;
        }
    }
    record_validation_events(db, paths, step_name)
}

fn record_validation_events(db: &StateDb, paths: &Paths, step_name: &str) -> Result<()> {
    if step_name == "07_convert_translation_to_pdf_input_state" && paths.encode_report_json.exists() {
        let report = read_json::<serde_json::Value>(&paths.encode_report_json)?;
        if report.get("ok").and_then(|value| value.as_bool()) == Some(false) {
            db.add_validation_event(&paths.job, "encode", "error", "ENCODE_FAILED", None, "one or more text runs could not be encoded")?;
        }
    }
    if step_name == "03_extract_raw_pdf_text_state" && paths.raw_completeness_report_json.exists() {
        let report = read_json::<serde_json::Value>(&paths.raw_completeness_report_json)?;
        if report.get("ok").and_then(|value| value.as_bool()) == Some(false) {
            db.add_validation_event(&paths.job, "raw-extraction", "warning", "RAW_COMPLETENESS_WARNING", None, "raw extraction completeness report is not ok")?;
        }
    }
    if step_name == "08_rebuild_pdf_with_extracted_options" && paths.rebuild_report_json.exists() {
        let report = read_json::<RebuildReport>(&paths.rebuild_report_json)?;
        for issue in report.failed {
            db.add_validation_event(&paths.job, "rebuild", "error", "REBUILD_FAILED", issue.id.as_deref(), &issue.message)?;
        }
    }
    if step_name == "09_qpdf_validate_output" && paths.validation_report_json.exists() {
        let report = read_json::<ValidationReport>(&paths.validation_report_json)?;
        if !report.ok {
            db.add_validation_event(&paths.job, "validation", "error", "QPDF_VALIDATION_FAILED", None, &report.stderr)?;
        }
    }
    if step_name == "09_qpdf_validate_output" && paths.structure_report_json.exists() {
        let report = read_json::<serde_json::Value>(&paths.structure_report_json)?;
        if report.get("ok").and_then(|value| value.as_bool()) == Some(false) {
            db.add_validation_event(&paths.job, "structure-validation", "error", "STRUCTURE_VALIDATION_FAILED", None, "structure-report.json is not ok")?;
        }
    }
    Ok(())
}

fn init_job(input: &Path) -> Result<Paths> {
    let root = project_root()?;
    let name = input.file_stem().and_then(|v| v.to_str()).ok_or_else(|| anyhow!("invalid input filename"))?;
    let job = sanitize_job_id(name);
    let paths = paths_for_job(&job, Some(input))?;
    create_job_dirs(&paths)?;
    fs::copy(input, &paths.source_pdf)
        .with_context(|| format!("copy {} to {}", input.display(), paths.source_pdf.display()))?;
    let bytes = fs::read(&paths.source_pdf)?;
    let sha256 = hex::encode(Sha256::digest(&bytes));
    let source = PdfSource {
        name: input.file_name().unwrap().to_string_lossy().to_string(),
        size_bytes: bytes.len() as u64,
        sha256,
        path: relative(&paths.source_pdf, &root),
    };
    write_json(&paths.job_root.join("state/job.json"), &JobState { job_id: job, source: source.clone() })?;
    write_json(&paths.job_root.join("state/pdf-source.json"), &source)?;
    Ok(paths)
}

fn qpdf_reference(paths: &Paths) -> Result<()> {
    if let Err(err) = pdf_qpdf::ensure_qpdf() {
        if allow_degraded_tools() {
            write_json(&paths.job_root.join("state/qpdf-check.json"), &ValidationReport {
                ok: false,
                command: "qpdf --version".to_string(),
                exit_code: None,
                stdout: String::new(),
                stderr: format!("qpdf skipped in degraded mode: {err}"),
            })?;
            return Ok(());
        }
        return Err(err);
    }
    let qdf = pdf_qpdf::create_qdf(&paths.source_pdf, &paths.qdf_pdf)?;
    write_json(&paths.job_root.join("state/qpdf-check.json"), &qdf)?;
    if !qdf.ok {
        return Err(anyhow!("qpdf QDF reference generation failed"));
    }
    let check = pdf_qpdf::check_pdf(&paths.source_pdf)?;
    if !check.ok {
        write_json(&paths.job_root.join("state/qpdf-check.json"), &check)?;
        return Err(anyhow!("qpdf check failed for source PDF"));
    }
    Ok(())
}

fn extract_raw(paths: &Paths) -> Result<()> {
    let raw = pdf_text_state::extract_raw_text_state(&paths.source_pdf)?;
    let report = raw_completeness_report(&raw);
    write_json(&paths.raw_completeness_report_json, &report)?;
    write_qdf_reference_report(paths, &raw)?;
    write_json(&paths.raw_json, &raw)
}

fn convert_readable(paths: &Paths) -> Result<()> {
    let raw = read_json::<RawPdfTextState>(&paths.raw_json)?;
    let mut readable = ReadableTextState::default();
    for page in raw.pages {
        for content in page.contents {
            for run in content.text_runs {
                let (decoded, method, issues) = pdf_cmap::decode_pdf_operand(&run.text_payload.encoded_original);
                if let Some(source) = decoded.or(run.text_payload.decoded_original) {
                    readable.items.push(ReadableItem {
                        id: run.id,
                        page: page.page,
                        source: source.clone(),
                        restore_options_ref: RestoreOptionsRef {
                            stream_xref: run.restore_options.stream_xref,
                            operator: run.restore_options.operator,
                        },
                        decode: DecodeStatus { method, confidence: if issues.is_empty() { "high" } else { "low" }.to_string(), issues },
                        layout: layout_info(&source, &run.restore_options.text_state),
                    });
                }
            }
        }
    }
    write_json(&paths.readable_json, &readable)
}

fn extract_terms(paths: &Paths) -> Result<()> {
    let readable = read_json::<ReadableTextState>(&paths.readable_json)?;
    let candidates = pdf_terms::extract_candidates(&readable);
    let glossary_path = project_relative_path(&paths.root, &env_or_default("GLOSSARY_PATH", "glossary.csv"));
    let auto_terms = pdf_terms::default_job_terms(&candidates);
    let glossary_terms = pdf_terms::load_glossary_csv(&glossary_path)?;
    let current_terms = read_json::<JobTerms>(&paths.terms_json).unwrap_or_default();
    let terms = pdf_terms::merge_job_terms(pdf_terms::merge_job_terms(auto_terms, glossary_terms), current_terms);
    let terms_db = StateDb::open(&paths.terms_db)?;
    for term in &terms.terms {
        terms_db.put_term(&term.term, term.translation.as_deref(), &term.mode, "job-terms")?;
    }
    write_json(&paths.candidates_json, &candidates)?;
    write_json(&paths.terms_json, &terms)
}

fn translate(paths: &Paths, source_lang: &str, target_lang: &str, model: &str) -> Result<()> {
    let readable = read_json::<ReadableTextState>(&paths.readable_json)?;
    let terms = read_json::<JobTerms>(&paths.terms_json).unwrap_or_default();
    let db = StateDb::open(&paths.tm_db)?;
    let mut cached_results = Vec::new();
    let mut misses = Vec::new();
    for item in &readable.items {
        if let Some(translated) = db.tm_get(&item.source, source_lang, target_lang)? {
            cached_results.push(TranslationResultItem { id: item.id.clone(), translated });
        } else {
            misses.push(item.clone());
        }
    }
    let input = TranslationInput {
        items: misses.iter().map(translation_input_item).collect(),
        terms: terms.terms.clone(),
    };
    write_json(&paths.translation_input_json, &input)?;
    let provider_config = translate_config_from_env(source_lang, target_lang, model)?;
    let mut translation_report = TranslationReport {
        ok: true,
        provider: provider_name(&provider_config.provider).to_string(),
        requested: input.items.len(),
        cached: cached_results.len(),
        ..TranslationReport::default()
    };
    let source_lookup: BTreeMap<String, String> = readable.items.iter().map(|item| (item.id.clone(), item.source.clone())).collect();
    let mut results = TranslationResults { items: cached_results };
    let mut source_by_miss_id = BTreeMap::new();
    if !input.items.is_empty() {
        source_by_miss_id = input.items.iter().map(|item| (item.id.clone(), item.text.clone())).collect();
        let part_outputs = translate_parallel_parts(paths, &input, &misses, &provider_config)?;
        let mut miss_results = TranslationResults::default();
        let mut degraded_errors = Vec::new();

        for part_output in part_outputs {
            degraded_errors.extend(part_output.degraded_errors);
            translation_report.chunks.extend(part_output.report.chunks);
            miss_results.items.extend(part_output.results.items);
        }
        results.items.extend(miss_results.items.clone());

        if !degraded_errors.is_empty() {
            write_json(&paths.job_root.join("state/translation-error.json"), &ReportIssue {
                id: None,
                stage: Some("translation".to_string()),
                code: "TRANSLATION_CHUNK_FAILED".to_string(),
                severity: "error".to_string(),
                message: format!(
                    "OpenAI translation skipped for {} degraded chunk(s) with OPENAI_CHUNK_SIZE={}: {}",
                    degraded_errors.len(),
                    env_usize_or_default("OPENAI_CHUNK_SIZE", 100),
                    degraded_errors.join("; ")
                ),
                recoverable: true,
            })?;
        }

        let overall = validate_translation_results(&input, &miss_results);
        translation_report.missing_ids = overall.0;
        translation_report.unknown_ids = overall.1;
        translation_report.duplicate_ids = overall.2;
        translation_report.fallback = miss_results.items.iter().filter(|item| source_by_miss_id.get(&item.id).is_some_and(|source| source == &item.translated)).count();
        translation_report.translated = miss_results.items.len().saturating_sub(translation_report.fallback);
        translation_report.ok = degraded_errors.is_empty()
            && translation_report.missing_ids.is_empty()
            && translation_report.unknown_ids.is_empty()
            && translation_report.duplicate_ids.is_empty();
    }
    apply_term_policy(paths, &source_lookup, &terms, &mut results)?;
    for item in &results.items {
        if let Some(source_text) = source_by_miss_id.get(&item.id) {
            if source_text != &item.translated {
                db.tm_put(source_text, &item.translated, source_lang, target_lang, model)?;
            }
        }
    }
    write_json(&paths.translation_report_json, &translation_report)?;
    write_json(&paths.translation_results_json, &results)
}

fn translate_parallel_parts(
    paths: &Paths,
    input: &TranslationInput,
    misses: &[ReadableItem],
    provider_config: &pdf_translate_openai::TranslateConfig,
) -> Result<Vec<TranslationPartOutput>> {
    let partitions = partition_translation_items(misses);
    let total_parts = partitions.len();
    progress_line(format!("[translate] parallel parts={} items={}", total_parts, input.items.len()));
    let (sender, receiver) = mpsc::channel();
    thread::scope(|scope| {
        for (index, items) in partitions.into_iter().enumerate() {
            let sender = sender.clone();
            let job_root = paths.job_root.clone();
            let terms = input.terms.clone();
            let config = provider_config.clone();
            scope.spawn(move || {
                let result = translate_part(&job_root, index + 1, total_parts, items, terms, config).map_err(|err| error_chain(&err));
                let _ = sender.send(result);
            });
        }
    });
    drop(sender);

    let mut outputs = Vec::new();
    for received in receiver {
        match received {
            Ok(output) => outputs.push(output),
            Err(message) => return Err(anyhow!(message)),
        }
    }
    outputs.sort_by_key(|output| output.part);
    Ok(outputs)
}

fn translate_part(
    job_root: &Path,
    part: usize,
    total_parts: usize,
    readable_items: Vec<ReadableItem>,
    terms: Vec<JobTerm>,
    provider_config: pdf_translate_openai::TranslateConfig,
) -> Result<TranslationPartOutput> {
    let part_started = Instant::now();
    let part_input = TranslationInput {
        items: readable_items
            .iter()
            .map(translation_input_item)
            .collect(),
        terms,
    };
    write_json(&job_root.join(format!("state/translation-input-part-{part:04}.json")), &part_input)?;
    progress_line(format!("[translate] part {part}/{total_parts} items={}", part_input.items.len()));

    let chunk_size = env_usize_or_default("OPENAI_CHUNK_SIZE", 100);
    let chunk_count = part_input.items.len().div_ceil(chunk_size);
    let source_by_id: BTreeMap<String, String> = part_input.items.iter().map(|item| (item.id.clone(), item.text.clone())).collect();
    let mut part_report = TranslationReport {
        ok: true,
        provider: provider_name(&provider_config.provider).to_string(),
        requested: part_input.items.len(),
        ..TranslationReport::default()
    };
    let mut part_results = TranslationResults::default();
    let mut degraded_errors = Vec::new();

    for (chunk_index, chunk) in part_input.items.chunks(chunk_size).enumerate() {
        let chunk_started = Instant::now();
        progress_line(format!("[translate] part {part}/{total_parts} chunk {}/{} items={}", chunk_index + 1, chunk_count, chunk.len()));
        let chunk_input = TranslationInput {
            items: chunk.to_vec(),
            terms: part_input.terms.clone(),
        };
        write_json(&job_root.join(format!("state/translation-input-part-{part:04}-chunk-{:04}.json", chunk_index + 1)), &chunk_input)?;
        let mut chunk_report = TranslationChunkReport {
            part,
            total_parts,
            chunk: chunk_index + 1,
            total_chunks: chunk_count,
            requested: chunk.len(),
            ..TranslationChunkReport::default()
        };
        let fresh = match pdf_translate_openai::translate_with_config(&chunk_input, &provider_config) {
            Ok(value) => {
                let validation = validate_translation_chunk(&chunk_input, &value);
                chunk_report.returned = value.items.len();
                chunk_report.missing_ids = validation.0;
                chunk_report.unknown_ids = validation.1;
                chunk_report.duplicate_ids = validation.2;
                if chunk_report.missing_ids.is_empty() && chunk_report.unknown_ids.is_empty() && chunk_report.duplicate_ids.is_empty() {
                    chunk_report.status = "ok".to_string();
                    value
                } else if allow_degraded_tools() {
                    chunk_report.status = "degraded".to_string();
                    let mut items_by_id: BTreeMap<String, TranslationResultItem> = value.items.into_iter().map(|item| (item.id.clone(), item)).collect();
                    for item in chunk {
                        items_by_id.entry(item.id.clone()).or_insert_with(|| TranslationResultItem { id: item.id.clone(), translated: item.text.clone() });
                    }
                    chunk_report.fallback = chunk_report.missing_ids.len();
                    TranslationResults { items: items_by_id.into_values().collect() }
                } else {
                    return Err(anyhow!("translation part {part}/{total_parts} chunk {}/{} completeness validation failed", chunk_index + 1, chunk_count));
                }
            }
            Err(err) if allow_degraded_tools() => {
                let message = error_chain(&err);
                degraded_errors.push(format!("part {part}/{total_parts} chunk {}/{} failed: {message}", chunk_index + 1, chunk_count));
                chunk_report.status = "fallback".to_string();
                chunk_report.error = Some(message);
                chunk_report.fallback = chunk.len();
                TranslationResults {
                    items: chunk
                        .iter()
                        .map(|item| TranslationResultItem { id: item.id.clone(), translated: item.text.clone() })
                        .collect(),
                }
            }
            Err(err) => return Err(err).with_context(|| format!("translate part {part}/{total_parts} chunk {}/{}", chunk_index + 1, chunk_count)),
        };

        write_json(&job_root.join(format!("state/translation-chunk-report-part-{part:04}-{:04}.json", chunk_index + 1)), &chunk_report)?;
        progress_line(format!(
            "[translate] part {part}/{total_parts} chunk {}/{} status={} returned={} fallback={} elapsed={}s",
            chunk_index + 1,
            chunk_count,
            chunk_report.status,
            chunk_report.returned,
            chunk_report.fallback,
            chunk_started.elapsed().as_secs()
        ));
        part_report.chunks.push(chunk_report);
        part_results.items.extend(fresh.items);
    }

    let validation = validate_translation_results(&part_input, &part_results);
    part_report.missing_ids = validation.0;
    part_report.unknown_ids = validation.1;
    part_report.duplicate_ids = validation.2;
    part_report.fallback = part_results.items.iter().filter(|item| source_by_id.get(&item.id).is_some_and(|source| source == &item.translated)).count();
    part_report.translated = part_results.items.len().saturating_sub(part_report.fallback);
    let layout_issues = validate_layout_fit(&part_input, &part_results);
    if !layout_issues.is_empty() {
        let strict = env_or_default("LAYOUT_FIT_MODE", "report-only") == "strict";
        if strict {
            part_report.ok = false;
        }
        part_report.issues.extend(layout_issues);
    }
    part_report.ok = degraded_errors.is_empty()
        && part_report.missing_ids.is_empty()
        && part_report.unknown_ids.is_empty()
        && part_report.duplicate_ids.is_empty()
        && (part_report.issues.is_empty() || env_or_default("LAYOUT_FIT_MODE", "report-only") != "strict");
    write_json(&job_root.join(format!("state/translation-results-part-{part:04}.json")), &part_results)?;
    write_json(&job_root.join(format!("state/translation-report-part-{part:04}.json")), &part_report)?;
    progress_line(format!(
        "[translate] part {part}/{total_parts} status={} translated={} fallback={} elapsed={}s",
        if part_report.ok { "ok" } else { "degraded" },
        part_report.translated,
        part_report.fallback,
        part_started.elapsed().as_secs()
    ));
    Ok(TranslationPartOutput { part, results: part_results, report: part_report, degraded_errors })
}

fn partition_translation_items(items: &[ReadableItem]) -> Vec<Vec<ReadableItem>> {
    if items.is_empty() {
        return Vec::new();
    }
    let max_page = items.iter().map(|item| item.page).max().unwrap_or(1).max(1);
    let requested = env_usize_or_default("TRANSLATION_PARALLELISM", default_translation_parallelism(max_page));
    let worker_count = requested.max(1).min(items.len()).min(max_page as usize).max(1);
    let pages_per_worker = (max_page as usize).div_ceil(worker_count).max(1);
    let mut partitions = vec![Vec::new(); worker_count];
    for item in items {
        let page_index = item.page.saturating_sub(1) as usize;
        let worker = (page_index / pages_per_worker).min(worker_count - 1);
        partitions[worker].push(item.clone());
    }
    partitions.into_iter().filter(|partition| !partition.is_empty()).collect()
}

fn default_translation_parallelism(page_count: u32) -> usize {
    if page_count < 20 {
        3
    } else if page_count < 50 {
        5
    } else {
        10
    }
}

fn translation_input_item(item: &ReadableItem) -> TranslationInputItem {
    TranslationInputItem {
        id: item.id.clone(),
        text: item.source.clone(),
        layout_limit: layout_limit_for_item(item),
    }
}

fn layout_limit_for_item(item: &ReadableItem) -> Option<LayoutLimit> {
    if !env_bool_or_default("LAYOUT_FIT_ENABLED", true) {
        return None;
    }
    let font_size = item.layout.font_size.or_else(|| Some(env_f64_or_default("LAYOUT_DEFAULT_FONT_SIZE", 10.0)))?;
    let source_units = item.layout.source_visual_units.unwrap_or_else(|| visual_units(&item.source));
    let spacing_units = item.layout.spacing_visual_units.unwrap_or(0.0);
    let spacing_credit = env_f64_or_default("LAYOUT_SPACING_CREDIT_RATIO", 0.25).min(1.0);
    let safety_ratio = env_f64_or_default("LAYOUT_SAFETY_RATIO", 0.90).min(1.0);
    let max_visual_units = ((source_units + spacing_units * spacing_credit) * safety_ratio).max(1.0);
    Some(LayoutLimit {
        max_visual_units,
        max_hangul_chars: max_visual_units.floor().max(1.0) as usize,
        source_visual_units: source_units,
        spacing_visual_units: spacing_units,
        font_size,
        safety_ratio,
    })
}

fn validate_layout_fit(input: &TranslationInput, results: &TranslationResults) -> Vec<ReportIssue> {
    let limit_by_id: BTreeMap<String, LayoutLimit> = input
        .items
        .iter()
        .filter_map(|item| item.layout_limit.clone().map(|limit| (item.id.clone(), limit)))
        .collect();
    results
        .items
        .iter()
        .filter_map(|item| {
            let limit = limit_by_id.get(&item.id)?;
            let translated_units = visual_units(&item.translated);
            if translated_units <= limit.max_visual_units {
                return None;
            }
            Some(ReportIssue {
                id: Some(item.id.clone()),
                stage: Some("layout-fit".to_string()),
                code: "LAYOUT_VISUAL_WIDTH_OVERFLOW".to_string(),
                severity: if env_or_default("LAYOUT_FIT_MODE", "report-only") == "strict" { "error" } else { "warning" }.to_string(),
                message: format!(
                    "translated visual units {:.2} exceed allowed {:.2}; maxHangulChars={} sourceUnits={:.2} spacingUnits={:.2}",
                    translated_units,
                    limit.max_visual_units,
                    limit.max_hangul_chars,
                    limit.source_visual_units,
                    limit.spacing_visual_units
                ),
                recoverable: true,
            })
        })
        .collect()
}

fn visual_units(text: &str) -> f64 {
    let mut units = 0.0;
    let mut previous_space = false;
    for ch in text.chars() {
        if ch.is_whitespace() {
            units += if previous_space {
                env_f64_or_default("LAYOUT_WEIGHT_REPEATED_SPACE", 0.12)
            } else {
                env_f64_or_default("LAYOUT_WEIGHT_SPACE", 0.28)
            };
            previous_space = true;
        } else {
            units += char_visual_weight(ch);
            previous_space = false;
        }
    }
    units
}

fn char_visual_weight(ch: char) -> f64 {
    if is_hangul(ch) {
        env_f64_or_default("LAYOUT_WEIGHT_HANGUL", 1.0)
    } else if is_cjk(ch) {
        env_f64_or_default("LAYOUT_WEIGHT_CJK", 1.0)
    } else if ch.is_ascii_alphanumeric() {
        env_f64_or_default("LAYOUT_WEIGHT_ASCII", 0.55)
    } else if ch.is_ascii_punctuation() {
        env_f64_or_default("LAYOUT_WEIGHT_PUNCT", 0.35)
    } else {
        env_f64_or_default("LAYOUT_WEIGHT_OTHER", 0.80)
    }
}

fn is_hangul(ch: char) -> bool {
    matches!(ch as u32, 0xAC00..=0xD7AF | 0x1100..=0x11FF | 0x3130..=0x318F)
}

fn is_cjk(ch: char) -> bool {
    matches!(ch as u32, 0x3400..=0x4DBF | 0x4E00..=0x9FFF | 0xF900..=0xFAFF)
}

fn apply_term_policy(paths: &Paths, source_lookup: &BTreeMap<String, String>, terms: &JobTerms, results: &mut TranslationResults) -> Result<()> {
    let enforcement = env_or_default("TERM_ENFORCEMENT", "report-only");
    if enforcement != "off" {
        for item in &mut results.items {
            let Some(source) = source_lookup.get(&item.id) else { continue; };
            for term in &terms.terms {
                if !source.contains(&term.term) {
                    continue;
                }
                if term.mode.eq_ignore_ascii_case("fixed") {
                    if let Some(target) = &term.translation {
                        item.translated = item.translated.replace(&term.term, target);
                    }
                }
            }
        }
    }
    let mut report = TermApplicationReport { ok: true, checked_items: results.items.len(), violations: Vec::new() };
    for item in &results.items {
        let Some(source) = source_lookup.get(&item.id) else { continue; };
        for term in &terms.terms {
            if !source.contains(&term.term) {
                continue;
            }
            if term.mode.eq_ignore_ascii_case("preserve") && !item.translated.contains(&term.term) {
                report.ok = false;
                report.violations.push(TermViolation {
                    id: item.id.clone(),
                    term: term.term.clone(),
                    mode: term.mode.clone(),
                    expected: term.term.clone(),
                    actual: item.translated.clone(),
                });
            } else if term.mode.eq_ignore_ascii_case("fixed") {
                let expected = term.translation.clone().unwrap_or_else(|| term.term.clone());
                if !item.translated.contains(&expected) {
                    report.ok = false;
                    report.violations.push(TermViolation {
                        id: item.id.clone(),
                        term: term.term.clone(),
                        mode: term.mode.clone(),
                        expected,
                        actual: item.translated.clone(),
                    });
                }
            }
        }
    }
    if enforcement == "strict" && !report.ok {
        write_json(&paths.term_application_report_json, &report)?;
        return Err(anyhow!("term application validation failed with {} violation(s)", report.violations.len()));
    }
    write_json(&paths.term_application_report_json, &report)
}

fn convert_pdf_input(paths: &Paths) -> Result<()> {
    let raw = read_json::<RawPdfTextState>(&paths.raw_json)?;
    let translations = read_json::<TranslationResults>(&paths.translation_results_json)?;
    let map: BTreeMap<String, String> = translations.items.into_iter().map(|item| (item.id, item.translated)).collect();
    let font_cmaps = font_cmaps_by_object_ref(&paths.source_pdf)?;
    let mut output = PdfInputTextState::default();
    let mut encode_report = EncodeReport { ok: true, ..EncodeReport::default() };
    for page in raw.pages {
        for content in page.contents {
            for mut run in content.text_runs {
                let Some(translated) = map.get(&run.id).cloned() else { continue; };
                let decoded_original = run.text_payload.decoded_original.clone().or_else(|| pdf_cmap::decode_pdf_operand(&run.text_payload.encoded_original).0);
                let (method, status, replacement_encoded, issues) = if decoded_original.as_deref() == Some(translated.as_str()) {
                    (
                        "reuse-original-encoded".to_string(),
                        "ok".to_string(),
                        Some(run.text_payload.encoded_original.clone()),
                        Vec::new(),
                    )
                } else {
                    match pdf_cmap::encode_replacement_like(&run.text_payload.encoded_original, &translated) {
                        Ok(value) => ("original-font-cmap".to_string(), "ok".to_string(), Some(value), Vec::new()),
                        Err(err) => {
                            let cmap_encoded = run
                                .restore_options
                                .font_state
                                .font_object_ref
                                .as_ref()
                                .and_then(|font_ref| font_cmaps.get(font_ref))
                                .and_then(|cmap| pdf_cmap::encode_with_cmap(&translated, cmap).ok());
                            if let Some(value) = cmap_encoded {
                                ("to-unicode-reverse-cmap".to_string(), "ok".to_string(), Some(value), Vec::new())
                            } else {
                                let fallback = font_fallback_encode_issue(&paths.root, &run, &translated, &err.to_string());
                                (fallback.0, "failed".to_string(), None, vec![fallback.1])
                            }
                        }
                    }
                };
                run.text_payload.decoded_original = decoded_original;
                run.text_payload.decoded_translated = Some(translated);
                run.text_payload.replacement_encoded = replacement_encoded;
                encode_report.total += 1;
                *encode_report.methods.entry(method.clone()).or_insert(0) += 1;
                if status == "ok" {
                    encode_report.ok_count += 1;
                } else {
                    encode_report.failed_count += 1;
                    encode_report.ok = false;
                    for issue in &issues {
                        encode_report.issues.push(ReportIssue {
                            id: Some(run.id.clone()),
                            stage: Some("encode".to_string()),
                            code: issue_code_from_message(issue),
                            severity: "error".to_string(),
                            message: issue.clone(),
                            recoverable: true,
                        });
                    }
                }
                output.text_runs.push(PdfInputTextRun {
                    id: run.id,
                    restore_options: run.restore_options,
                    text_payload: run.text_payload,
                    encode: EncodeStatus { method, status, issues },
                });
            }
        }
    }
    write_json(&paths.encode_report_json, &encode_report)?;
    write_json(&paths.pdf_input_json, &output)
}

fn font_fallback_encode_issue(root: &Path, run: &RawTextRun, translated: &str, encode_error: &str) -> (String, String) {
    let mode = env_or_default("FONT_FALLBACK_MODE", "off").trim().to_ascii_lowercase();
    if mode == "off" {
        return ("original-font-cmap".to_string(), encode_error.to_string());
    }
    let configured_fonts = fallback_font_paths(root);
    let missing_fonts = configured_fonts
        .iter()
        .filter(|path| !path.exists())
        .map(|path| relative(path, root))
        .collect::<Vec<_>>();
    if configured_fonts.is_empty() || !missing_fonts.is_empty() {
        return (
            format!("fallback-font-{mode}"),
            format!(
                "FONT_FALLBACK_FONT_MISSING: FONT_FALLBACK_MODE={mode} needs FONT_REGULAR, FONT_BOLD, or FONT_FALLBACK to point to existing project-local font files; missing={}",
                if missing_fonts.is_empty() { "all".to_string() } else { missing_fonts.join(",") }
            ),
        );
    }
    let source_font = run
        .restore_options
        .font_state
        .base_font
        .clone()
        .or_else(|| run.restore_options.font_state.resource_name.clone())
        .unwrap_or_else(|| "unknown".to_string());
    (
        format!("fallback-font-{mode}"),
        format!(
            "FONT_FALLBACK_EMBED_UNSUPPORTED: FONT_FALLBACK_MODE={mode} is configured, but v9 preserves extracted text state/operator/font/CMap and does not inject a new font resource for run {} sourceFont={} translatedChars={}",
            run.id,
            source_font,
            translated.chars().count()
        ),
    )
}

fn issue_code_from_message(message: &str) -> String {
    message
        .split_once(':')
        .map(|(code, _)| code)
        .filter(|code| code.chars().all(|ch| ch.is_ascii_uppercase() || ch == '_'))
        .unwrap_or("ENCODE_UNSUPPORTED")
        .to_string()
}

fn fallback_font_paths(root: &Path) -> Vec<PathBuf> {
    ["FONT_REGULAR", "FONT_BOLD", "FONT_FALLBACK"]
        .into_iter()
        .filter_map(|name| std::env::var(name).ok().filter(|value| !value.trim().is_empty()).map(|value| project_relative_path(root, &value)))
        .collect()
}

fn font_cmaps_by_object_ref(source_pdf: &Path) -> Result<BTreeMap<String, pdf_cmap::CMap>> {
    let pdf = pdf_core::LoadedPdf::open(source_pdf)?;
    let mut cmaps = BTreeMap::new();
    for stream in pdf.content_streams()? {
        for info in stream.font_resources.values() {
            let Some(object_ref) = &info.object_ref else { continue; };
            let Some(bytes) = &info.to_unicode_cmap else { continue; };
            if let Ok(cmap) = pdf_cmap::parse_to_unicode_cmap(bytes) {
                cmaps.insert(object_ref.clone(), cmap);
            }
        }
    }
    Ok(cmaps)
}

fn rebuild(paths: &Paths) -> Result<()> {
    let input = read_json::<PdfInputTextState>(&paths.pdf_input_json)?;
    let report = pdf_rebuild::rebuild_pdf(&paths.source_pdf, &input, &paths.rebuilt_pdf)?;
    write_json(&paths.rebuild_report_json, &report)?;
    if report.ok {
        return Ok(());
    }
    if allow_degraded_tools() {
        if paths.rebuilt_pdf.exists() {
            progress_line(format!("[rebuild] partial PDF written replaced={} failed={}", report.replaced, report.failed.len()));
        } else {
            if let Some(parent) = paths.rebuilt_pdf.parent() {
                fs::create_dir_all(parent)?;
            }
            fs::copy(&paths.source_pdf, &paths.rebuilt_pdf)?;
            progress_line("[rebuild] no replacements were writable; source PDF copied as fallback");
        }
        return Ok(());
    }
    Err(anyhow!("rebuild failed with {} issue(s)", report.failed.len()))
}

fn validate_output(paths: &Paths) -> Result<()> {
    if let Err(err) = pdf_qpdf::ensure_qpdf() {
        if allow_degraded_tools() {
            write_json(&paths.validation_report_json, &ValidationReport {
                ok: false,
                command: "qpdf --check".to_string(),
                exit_code: None,
                stdout: String::new(),
                stderr: format!("qpdf validation skipped in degraded mode: {err}"),
            })?;
            if paths.rebuilt_pdf.exists() {
                write_structure_report(paths)?;
                write_feature_reports(paths)?;
            }
            return Ok(());
        }
        return Err(err);
    }
    let report = pdf_qpdf::check_pdf(&paths.rebuilt_pdf)?;
    write_json(&paths.validation_report_json, &report)?;
    write_structure_report(paths)?;
    write_feature_reports(paths)?;
    if report.ok { Ok(()) } else { Err(anyhow!("qpdf validation failed")) }
}

fn publish(paths: &Paths) -> Result<()> {
    let summary = classify_current_run(paths)?;
    let target = if summary.degraded { &paths.rejected_pdf } else { &paths.output_pdf };
    let stale = if summary.degraded { &paths.output_pdf } else { &paths.rejected_pdf };
    fs::create_dir_all(target.parent().unwrap())?;
    if target.exists() {
        fs::remove_file(target)?;
    }
    if stale.exists() {
        fs::remove_file(stale)?;
    }
    fs::copy(&paths.rebuilt_pdf, target)?;
    progress_line(format!("[publish] {} -> {}", if summary.degraded { "rejected" } else { "validated" }, relative(target, &paths.root)));
    publish_report_bundle(paths)?;
    Ok(())
}

fn write_run_summary(paths: &Paths) -> Result<RunSummary> {
    let pdf_input = read_json::<PdfInputTextState>(&paths.pdf_input_json)?;
    let rebuild = read_json::<RebuildReport>(&paths.rebuild_report_json)?;
    let validation = read_json::<ValidationReport>(&paths.validation_report_json).unwrap_or_default();
    let translation_report = read_json::<TranslationReport>(&paths.translation_report_json).unwrap_or_default();
    let translation_error = paths.job_root.join("state/translation-error.json").exists();

    let text_runs = pdf_input.text_runs.len();
    let changed_text_runs = pdf_input
        .text_runs
        .iter()
        .filter(|run| run.text_payload.decoded_original != run.text_payload.decoded_translated)
        .count();
    let unchanged_text_runs = text_runs.saturating_sub(changed_text_runs);
    let encode_ok = pdf_input.text_runs.iter().filter(|run| run.encode.status == "ok").count();
    let encode_failed = pdf_input.text_runs.iter().filter(|run| run.encode.status != "ok").count();
    let rebuild_failed = rebuild.failed.len();
    let source_sha256 = sha256_file(&paths.source_pdf)?;
    let validated_sha256 = if paths.output_pdf.exists() { Some(sha256_file(&paths.output_pdf)?) } else { None };
    let rejected_sha256 = if paths.rejected_pdf.exists() { Some(sha256_file(&paths.rejected_pdf)?) } else { None };

    let mut notes = Vec::new();
    if translation_error {
        notes.push("OpenAI translation failed or was skipped; unchanged text may have been reused".to_string());
    }
    if encode_failed > 0 {
        notes.push(format!("{encode_failed} text run(s) could not be encoded with the original font/CMap"));
    }
    if !rebuild.ok {
        notes.push(format!("rebuild report is not ok; degraded mode may have copied the source PDF"));
    }
    if !validation.ok {
        notes.push("qpdf validation did not pass or was skipped".to_string());
    }
    if validated_sha256.as_deref() == Some(source_sha256.as_str()) || rejected_sha256.as_deref() == Some(source_sha256.as_str()) {
        notes.push("output PDF hash equals source PDF hash".to_string());
    }

    if !translation_report.ok {
        notes.push("translation report has missing, duplicate, unknown, or fallback items".to_string());
    }
    let fallback_used = translation_error
        || translation_report.fallback > 0
        || validated_sha256.as_deref() == Some(source_sha256.as_str())
        || rejected_sha256.as_deref() == Some(source_sha256.as_str());
    let degraded = fallback_used || encode_failed > 0 || !rebuild.ok || !validation.ok || !translation_report.ok;
    let classification = if !rebuild.ok || !validation.ok || encode_failed > 0 {
        "failed"
    } else if fallback_used {
        "fallback"
    } else if changed_text_runs > 0 {
        "translated"
    } else {
        "partial"
    };
    let output_path = if degraded { &paths.rejected_pdf } else { &paths.output_pdf };
    let output_sha256 = if degraded { rejected_sha256 } else { validated_sha256 };
    let summary = RunSummary {
        job: paths.job.clone(),
        source_pdf: relative(&paths.source_pdf, &paths.root),
        output_pdf: relative(output_path, &paths.root),
        classification: classification.to_string(),
        fallback_used,
        validated_pdf: (!degraded && paths.output_pdf.exists()).then(|| relative(&paths.output_pdf, &paths.root)),
        rejected_pdf: (degraded && paths.rejected_pdf.exists()).then(|| relative(&paths.rejected_pdf, &paths.root)),
        source_sha256,
        output_sha256,
        degraded,
        translation_error,
        text_runs,
        changed_text_runs,
        unchanged_text_runs,
        encode_ok,
        encode_failed,
        rebuild_ok: rebuild.ok,
        rebuild_replaced: rebuild.replaced,
        rebuild_failed,
        validation_ok: validation.ok,
        notes,
    };
    write_json(&paths.job_root.join("state/run-summary.json"), &summary)?;
    Ok(summary)
}

fn paths_for_job(job: &str, input: Option<&Path>) -> Result<Paths> {
    let root = project_root()?;
    let runtime = runtime_paths(&root);
    let job_root = runtime.work_dir.join(job);
    let source_name = input
        .and_then(|p| p.file_name())
        .and_then(|value| value.to_str())
        .map(ToOwned::to_owned)
        .or_else(|| source_name_from_job_state(&job_root))
        .unwrap_or_else(|| "source.pdf".to_string());
    let paths = Paths {
        root: root.clone(),
        job: job.to_string(),
        job_root: job_root.clone(),
        source_pdf: job_root.join("source/source.pdf"),
        qdf_pdf: job_root.join("qpdf/source.qdf.pdf"),
        raw_json: job_root.join("state/raw-pdf-text-state.json"),
        readable_json: job_root.join("state/readable-text-state.json"),
        candidates_json: job_root.join("state/proper-noun-candidates.json"),
        terms_json: job_root.join("state/job-terms.json"),
        translation_input_json: job_root.join("state/translation-input.json"),
        translation_results_json: job_root.join("state/translation-results.json"),
        pdf_input_json: job_root.join("state/pdf-input-text-state.json"),
        rebuild_report_json: job_root.join("state/rebuild-report.json"),
        validation_report_json: job_root.join("state/validation-report.json"),
        term_application_report_json: job_root.join("state/term-application-report.json"),
        encode_report_json: job_root.join("state/encode-report.json"),
        translation_report_json: job_root.join("state/translation-report.json"),
        raw_completeness_report_json: job_root.join("state/raw-completeness-report.json"),
        qdf_reference_report_json: job_root.join("state/qdf-reference-report.json"),
        ocr_report_json: job_root.join("state/ocr-report.json"),
        font_report_json: job_root.join("state/font-report.json"),
        render_report_json: job_root.join("state/render-report.json"),
        structure_report_json: job_root.join("state/structure-report.json"),
        rebuilt_pdf: job_root.join("pdf/rebuilt.pdf"),
        output_pdf: runtime.output_dir.join("validated").join(format!("{}_V9.pdf", Path::new(&source_name).file_stem().unwrap_or_default().to_string_lossy())),
        rejected_pdf: runtime.output_dir.join("rejected").join(format!("{}_V9.pdf", Path::new(&source_name).file_stem().unwrap_or_default().to_string_lossy())),
        report_bundle_dir: runtime.output_dir.join("reports").join(job),
        state_db: runtime.work_dir.join("db/state.sqlite"),
        tm_db: project_relative_path(&root, &env_or_default("TM_DB_PATH", "work/tm.sqlite")),
        terms_db: project_relative_path(&root, &env_or_default("TERMS_DB_PATH", "work/terms.sqlite")),
    };
    Ok(paths)
}

fn source_name_from_job_state(job_root: &Path) -> Option<String> {
    let source = read_json::<PdfSource>(&job_root.join("state/pdf-source.json")).ok()?;
    if !source.name.trim().is_empty() {
        return Some(source.name);
    }
    Path::new(&source.path).file_name().and_then(|value| value.to_str()).map(ToOwned::to_owned)
}

fn create_job_dirs(paths: &Paths) -> Result<()> {
    for dir in ["source", "qpdf", "state", "pdf", "reports"] {
        fs::create_dir_all(paths.job_root.join(dir))?;
    }
    fs::create_dir_all(paths.output_pdf.parent().unwrap())?;
    fs::create_dir_all(paths.rejected_pdf.parent().unwrap())?;
    fs::create_dir_all(&paths.report_bundle_dir)?;
    fs::create_dir_all(paths.state_db.parent().unwrap())?;
    if let Some(parent) = paths.tm_db.parent() {
        fs::create_dir_all(parent)?;
    }
    if let Some(parent) = paths.terms_db.parent() {
        fs::create_dir_all(parent)?;
    }
    Ok(())
}

struct RuntimePaths {
    input_dir: PathBuf,
    output_dir: PathBuf,
    work_dir: PathBuf,
}

fn runtime_paths(root: &Path) -> RuntimePaths {
    RuntimePaths {
        input_dir: project_relative_path(root, &env_or_default("INPUT_DIR", "input")),
        output_dir: project_relative_path(root, &env_or_default("OUTPUT_DIR", "output")),
        work_dir: project_relative_path(root, &env_or_default("WORK_DIR", "work")),
    }
}

fn raw_completeness_report(raw: &RawPdfTextState) -> RawCompletenessReport {
    let mut report = RawCompletenessReport { ok: true, pages: raw.pages.len(), ..RawCompletenessReport::default() };
    for page in &raw.pages {
        report.content_streams += page.contents.len();
        for content in &page.contents {
            report.text_runs += content.text_runs.len();
            for run in &content.text_runs {
                if run.text_payload.decoded_original.is_none() {
                    report.decoded_missing += 1;
                    report.issues.push(ReportIssue {
                        id: Some(run.id.clone()),
                        stage: Some("raw-extraction".to_string()),
                        code: "DECODED_ORIGINAL_MISSING".to_string(),
                        severity: "warning".to_string(),
                        message: "decodedOriginal is missing".to_string(),
                        recoverable: true,
                    });
                }
                if run.restore_options.font_state.resource_name.is_none() {
                    report.font_resource_missing += 1;
                }
                if run.restore_options.font_state.to_unicode_ref.is_none() {
                    report.to_unicode_missing += 1;
                }
            }
        }
    }
    report.ok = report.decoded_missing == 0 && report.text_runs > 0;
    report
}

fn write_qdf_reference_report(paths: &Paths, raw: &RawPdfTextState) -> Result<()> {
    let stream_xrefs = raw
        .pages
        .iter()
        .flat_map(|page| page.contents.iter().map(|content| content.stream_xref))
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect::<Vec<_>>();
    let report = QdfReferenceReport {
        ok: paths.qdf_pdf.exists(),
        qdf_pdf: relative(&paths.qdf_pdf, &paths.root),
        raw_extraction_basis: "source.pdf byte ranges; qdf is debug/reference only".to_string(),
        stream_xrefs,
    };
    write_json(&paths.qdf_reference_report_json, &report)
}

fn layout_info(source: &str, text_state: &TextState) -> LayoutInfo {
    let matrix = text_state.text_matrix;
    let estimated_width = text_state.font_size.map(|font_size| {
        let scale = text_state.horizontal_scaling / 100.0;
        source.chars().count() as f64 * font_size * 0.5 * scale
    });
    let bbox = match (matrix, estimated_width, text_state.font_size) {
        (Some(matrix), Some(width), Some(height)) => Some([matrix[4], matrix[5], matrix[4] + width, matrix[5] + height]),
        _ => None,
    };
    LayoutInfo { matrix, bbox, estimated_width }
}

fn write_feature_reports(paths: &Paths) -> Result<()> {
    write_ocr_report(paths)?;

    let font_mode = env_or_default("FONT_FALLBACK_MODE", "off");
    let fallback_fonts = fallback_font_paths(&paths.root);
    let font_paths_ok = fallback_fonts.iter().all(|path| path.exists());
    let font_report = FeatureReport {
        ok: font_mode == "off" || (font_paths_ok && !fallback_fonts.is_empty()),
        mode: font_mode,
        status: if fallback_fonts.is_empty() { "skipped" } else if font_paths_ok { "configured-policy-only" } else { "missing-font-file" }.to_string(),
        message: "fallback font settings are applied during encode failure handling; v9 does not inject new font resources and will report FONT_FALLBACK_* issues instead of silently substituting text".to_string(),
    };
    write_json(&paths.font_report_json, &font_report)?;

    let render_mode = env_or_default("RENDER_MODE", "off");
    let render_backend = find_project_tool(&paths.root, &[
        "tools/poppler/bin/pdftoppm.exe",
        "tools/poppler/bin/pdftoppm",
        "tools/mupdf/mutool.exe",
        "tools/mupdf/mutool",
        "tools/bin/pdftoppm.exe",
        "tools/bin/pdftoppm",
        "tools/bin/mutool.exe",
        "tools/bin/mutool",
    ]);
    let render_report = if render_mode == "off" {
        FeatureReport { ok: true, mode: format!("off scale={}", env_or_default("RENDER_SCALE", "1.5")), status: "skipped".to_string(), message: "RENDER_MODE=off".to_string() }
    } else if let Some(backend) = render_backend {
        render_validation_report(paths, &backend, &render_mode)?
    } else {
        FeatureReport { ok: false, mode: format!("{} scale={}", render_mode, env_or_default("RENDER_SCALE", "1.5")), status: "backend-missing".to_string(), message: "put pdftoppm or mutool under tools/poppler, tools/mupdf, or tools/bin for render validation".to_string() }
    };
    write_json(&paths.render_report_json, &render_report)
}

fn write_ocr_report(paths: &Paths) -> Result<()> {
    let ocr_mode = env_or_default("OCR_MODE", "off");
    if ocr_mode == "off" {
        return write_json(&paths.ocr_report_json, &OcrReport {
            ok: true,
            mode: ocr_mode,
            status: "skipped".to_string(),
            provider: "none".to_string(),
            pages_requested: Vec::new(),
            pages_completed: 0,
            text_items: Vec::new(),
            issues: Vec::new(),
        });
    }

    let endpoint = std::env::var("AZURE_VISION_ENDPOINT").ok().filter(|value| !value.trim().is_empty());
    let key = std::env::var("AZURE_VISION_KEY").ok().filter(|value| !value.trim().is_empty());
    if endpoint.is_none() || key.is_none() {
        return write_json(&paths.ocr_report_json, &OcrReport {
            ok: false,
            mode: ocr_mode,
            status: "not-configured".to_string(),
            provider: "Azure AI Vision Read".to_string(),
            pages_requested: Vec::new(),
            pages_completed: 0,
            text_items: Vec::new(),
            issues: vec![ReportIssue {
                id: None,
                stage: Some("ocr".to_string()),
                code: "OCR_AZURE_CONFIG_MISSING".to_string(),
                severity: "error".to_string(),
                message: "OCR requires AZURE_VISION_ENDPOINT and AZURE_VISION_KEY; secret values are not written to reports".to_string(),
                recoverable: true,
            }],
        });
    }

    let Some(backend) = find_project_tool(&paths.root, &[
        "tools/poppler/bin/pdftoppm.exe",
        "tools/poppler/bin/pdftoppm",
        "tools/mupdf/mutool.exe",
        "tools/mupdf/mutool",
        "tools/bin/pdftoppm.exe",
        "tools/bin/pdftoppm",
        "tools/bin/mutool.exe",
        "tools/bin/mutool",
    ]) else {
        return write_json(&paths.ocr_report_json, &OcrReport {
            ok: false,
            mode: ocr_mode,
            status: "renderer-missing".to_string(),
            provider: "Azure AI Vision Read".to_string(),
            pages_requested: Vec::new(),
            pages_completed: 0,
            text_items: Vec::new(),
            issues: vec![ReportIssue {
                id: None,
                stage: Some("ocr".to_string()),
                code: "OCR_RENDERER_MISSING".to_string(),
                severity: "error".to_string(),
                message: "OCR requires project-local pdftoppm or mutool to render PDF pages before Azure Vision Read is called".to_string(),
                recoverable: true,
            }],
        });
    };

    let pages = ocr_pages(paths)?;
    let mut report = OcrReport {
        ok: true,
        mode: ocr_mode.clone(),
        status: "completed".to_string(),
        provider: "Azure AI Vision Read".to_string(),
        pages_requested: pages.clone(),
        pages_completed: 0,
        text_items: Vec::new(),
        issues: Vec::new(),
    };
    let endpoint = endpoint.unwrap();
    let key = key.unwrap();
    let client = Client::builder().timeout(Duration::from_secs(env_u64_or_default("OCR_TIMEOUT_SECS", 120))).build()?;
    let ocr_dir = paths.job_root.join("reports/ocr");
    fs::create_dir_all(&ocr_dir)?;

    for page in pages {
        let image = ocr_dir.join(format!("page-{page}.png"));
        if let Err(err) = render_page(&backend, &paths.source_pdf, &image, page) {
            report.ok = false;
            report.issues.push(ocr_issue(Some(format!("page-{page}")), "OCR_RENDER_FAILED", error_chain(&err)));
            continue;
        }
        match azure_read_image(&client, &endpoint, &key, &image) {
            Ok(items) => {
                report.pages_completed += 1;
                report.text_items.extend(items.into_iter().map(|mut item| {
                    item.page = page;
                    item
                }));
            }
            Err(err) => {
                report.ok = false;
                report.issues.push(ocr_issue(Some(format!("page-{page}")), "OCR_AZURE_READ_FAILED", error_chain(&err)));
            }
        }
    }
    if !report.ok {
        report.status = "failed".to_string();
    } else if report.text_items.is_empty() {
        report.status = "completed-empty".to_string();
    }
    write_json(&paths.ocr_report_json, &report)
}

fn ocr_pages(paths: &Paths) -> Result<Vec<u32>> {
    let page_count = pdf_core::LoadedPdf::open(&paths.source_pdf)?.page_count() as u32;
    let configured = env_or_default("OCR_PAGES", "1");
    if configured.eq_ignore_ascii_case("all") {
        return Ok((1..=page_count).collect());
    }
    let mut pages = Vec::new();
    for part in configured.split(',') {
        let part = part.trim();
        if part.is_empty() {
            continue;
        }
        let page = part.parse::<u32>().with_context(|| format!("invalid OCR_PAGES value: {part}"))?;
        if page == 0 || page > page_count {
            return Err(anyhow!("OCR page {page} is outside source page range 1..={page_count}"));
        }
        pages.push(page);
    }
    pages.sort_unstable();
    pages.dedup();
    if pages.is_empty() {
        pages.push(1);
    }
    Ok(pages)
}

fn azure_read_image(client: &Client, endpoint: &str, key: &str, image_path: &Path) -> Result<Vec<OcrTextItem>> {
    let endpoint = endpoint.trim_end_matches('/');
    let url = format!("{endpoint}/vision/v3.2/read/analyze");
    let image = fs::read(image_path).with_context(|| format!("read OCR image {}", image_path.display()))?;
    let response = client
        .post(url)
        .header("Ocp-Apim-Subscription-Key", key)
        .header("Content-Type", "application/octet-stream")
        .body(image)
        .send()
        .context("send Azure Vision Read request")?;
    if !response.status().is_success() {
        return Err(anyhow!("Azure Vision Read request failed with HTTP {}", response.status()));
    }
    let operation_location = response
        .headers()
        .get("operation-location")
        .and_then(|value| value.to_str().ok())
        .ok_or_else(|| anyhow!("Azure Vision Read response did not include operation-location header"))?
        .to_string();

    let retry_max = env_usize_or_default("OCR_RETRY_MAX", 20);
    let delay_ms = env_u64_or_default("OCR_RETRY_BASE_MS", 1000);
    for _ in 0..retry_max {
        std::thread::sleep(Duration::from_millis(delay_ms));
        let response = client
            .get(&operation_location)
            .header("Ocp-Apim-Subscription-Key", key)
            .send()
            .context("poll Azure Vision Read result")?;
        let result = parse_azure_read_response(response)?;
        match result.status.as_str() {
            "succeeded" => return Ok(azure_lines_to_items(result)),
            "failed" => return Err(anyhow!("Azure Vision Read operation failed")),
            _ => continue,
        }
    }
    Err(anyhow!("Azure Vision Read operation did not finish before OCR_RETRY_MAX"))
}

fn parse_azure_read_response(response: Response) -> Result<AzureReadResult> {
    if !response.status().is_success() {
        return Err(anyhow!("Azure Vision Read poll failed with HTTP {}", response.status()));
    }
    Ok(response.json::<AzureReadResult>().context("parse Azure Vision Read result")?)
}

fn azure_lines_to_items(result: AzureReadResult) -> Vec<OcrTextItem> {
    result
        .analyze_result
        .map(|analyze| analyze.read_results)
        .unwrap_or_default()
        .into_iter()
        .flat_map(|page| page.lines)
        .map(|line| OcrTextItem { page: 0, text: line.text, bounding_box: line.bounding_box })
        .collect()
}

fn ocr_issue(id: Option<String>, code: &str, message: impl Into<String>) -> ReportIssue {
    ReportIssue {
        id,
        stage: Some("ocr".to_string()),
        code: code.to_string(),
        severity: "error".to_string(),
        message: message.into(),
        recoverable: true,
    }
}

fn find_project_tool(root: &Path, relative_candidates: &[&str]) -> Option<PathBuf> {
    relative_candidates
        .iter()
        .map(|candidate| root.join(candidate))
        .find(|path| path.exists())
}

fn render_validation_report(paths: &Paths, backend: &Path, render_mode: &str) -> Result<FeatureReport> {
    if !paths.rebuilt_pdf.exists() {
        return Ok(FeatureReport {
            ok: true,
            mode: format!("{} scale={}", render_mode, env_or_default("RENDER_SCALE", "1.5")),
            status: "backend-detected".to_string(),
            message: format!("render backend detected at {}; rebuilt PDF is not available yet", relative(backend, &paths.root)),
        });
    }
    let render_dir = paths.job_root.join("reports/render");
    fs::create_dir_all(&render_dir)?;
    let source_image = render_dir.join("source-page-1.png");
    let output_image = render_dir.join("rebuilt-page-1.png");
    render_first_page(backend, &paths.source_pdf, &source_image)?;
    render_first_page(backend, &paths.rebuilt_pdf, &output_image)?;
    let source_hash = sha256_file(&source_image)?;
    let output_hash = sha256_file(&output_image)?;
    let status = if source_hash == output_hash { "render-identical" } else { "render-different" };
    Ok(FeatureReport {
        ok: true,
        mode: format!("{} scale={}", render_mode, env_or_default("RENDER_SCALE", "1.5")),
        status: status.to_string(),
        message: format!("backend={} sourcePage1Sha256={} rebuiltPage1Sha256={}", relative(backend, &paths.root), source_hash, output_hash),
    })
}

fn render_first_page(backend: &Path, input_pdf: &Path, output_png: &Path) -> Result<()> {
    render_page(backend, input_pdf, output_png, 1)
}

fn render_page(backend: &Path, input_pdf: &Path, output_png: &Path, page: u32) -> Result<()> {
    let backend_name = backend.file_name().and_then(|value| value.to_str()).unwrap_or_default().to_ascii_lowercase();
    let scale = env_or_default("RENDER_SCALE", "1.5").parse::<f64>().unwrap_or(1.5);
    let dpi = (72.0 * scale).round().max(1.0).to_string();
    if let Some(parent) = output_png.parent() {
        fs::create_dir_all(parent)?;
    }
    let output = if backend_name.contains("pdftoppm") {
        let prefix = output_png.with_extension("");
        Command::new(backend)
            .args(["-f", &page.to_string(), "-l", &page.to_string(), "-singlefile", "-png", "-r", &dpi])
            .arg(input_pdf)
            .arg(&prefix)
            .output()
            .with_context(|| format!("run renderer {}", backend.display()))?
    } else {
        Command::new(backend)
            .args(["draw", "-o"])
            .arg(output_png)
            .args(["-r", &dpi])
            .arg(input_pdf)
                .arg(page.to_string())
            .output()
            .with_context(|| format!("run renderer {}", backend.display()))?
    };
    if output.status.success() && output_png.exists() {
        Ok(())
    } else {
        Err(anyhow!("render failed: {}", String::from_utf8_lossy(&output.stderr)))
    }
}

fn write_structure_report(paths: &Paths) -> Result<()> {
    let source_pdf = pdf_core::LoadedPdf::open(&paths.source_pdf)?;
    let output_pages = if paths.rebuilt_pdf.exists() { pdf_core::LoadedPdf::open(&paths.rebuilt_pdf)?.page_count() } else { 0 };
    let source_sha256 = sha256_file(&paths.source_pdf)?;
    let output_sha256 = if paths.rebuilt_pdf.exists() { Some(sha256_file(&paths.rebuilt_pdf)?) } else { None };
    let mut report = StructureReport {
        ok: true,
        source_pages: source_pdf.page_count(),
        output_pages,
        source_sha256,
        output_sha256,
        issues: Vec::new(),
    };
    if report.output_pages == 0 {
        report.ok = false;
        report.issues.push(structure_issue("STRUCTURE_OUTPUT_MISSING", "rebuilt PDF does not exist or has no pages"));
    }
    if report.source_pages != report.output_pages {
        report.ok = false;
        report.issues.push(structure_issue("STRUCTURE_PAGE_COUNT_MISMATCH", format!("source pages {} != output pages {}", report.source_pages, report.output_pages)));
    }
    write_json(&paths.structure_report_json, &report)
}

fn structure_issue(code: &str, message: impl Into<String>) -> ReportIssue {
    ReportIssue {
        id: None,
        stage: Some("structure-validation".to_string()),
        code: code.to_string(),
        severity: "error".to_string(),
        message: message.into(),
        recoverable: true,
    }
}

fn translate_config_from_env(source_lang: &str, target_lang: &str, model: &str) -> Result<pdf_translate_openai::TranslateConfig> {
    let azure_endpoint = std::env::var("AZURE_OPENAI_ENDPOINT").ok().filter(|value| !value.trim().is_empty());
    let azure_deployment = std::env::var("AZURE_OPENAI_DEPLOYMENT").ok().filter(|value| !value.trim().is_empty());
    let use_azure = azure_endpoint.is_some() && azure_deployment.is_some();
    let api_key = if use_azure {
        std::env::var("AZURE_OPENAI_API_KEY").or_else(|_| std::env::var("OPENAI_API_KEY")).context("AZURE_OPENAI_API_KEY or OPENAI_API_KEY is required for Azure OpenAI")?
    } else {
        std::env::var("OPENAI_API_KEY").context("OPENAI_API_KEY is required for OpenAI translation")?
    };
    Ok(pdf_translate_openai::TranslateConfig {
        provider: if use_azure { pdf_translate_openai::LlmProvider::AzureOpenAi } else { pdf_translate_openai::LlmProvider::OpenAi },
        api_key,
        model: Some(model.to_string()),
        azure_endpoint,
        azure_deployment,
        azure_api_version: std::env::var("AZURE_OPENAI_API_VERSION").ok().filter(|value| !value.trim().is_empty()),
        source_lang: source_lang.to_string(),
        target_lang: target_lang.to_string(),
        retry_max: env_usize_or_default("OPENAI_RETRY_MAX", 3),
        retry_base_ms: env_u64_or_default("OPENAI_RETRY_BASE_MS", 1000),
        timeout_secs: env_u64_or_default("OPENAI_TIMEOUT_SECS", 120),
    })
}

fn provider_name(provider: &pdf_translate_openai::LlmProvider) -> &'static str {
    match provider {
        pdf_translate_openai::LlmProvider::OpenAi => "OpenAI",
        pdf_translate_openai::LlmProvider::AzureOpenAi => "Azure OpenAI",
    }
}

fn validate_translation_chunk(input: &TranslationInput, results: &TranslationResults) -> (Vec<String>, Vec<String>, Vec<String>) {
    validate_translation_results(input, results)
}

fn validate_translation_results(input: &TranslationInput, results: &TranslationResults) -> (Vec<String>, Vec<String>, Vec<String>) {
    let requested: BTreeSet<String> = input.items.iter().map(|item| item.id.clone()).collect();
    let mut seen = BTreeSet::new();
    let mut duplicate = BTreeSet::new();
    let mut unknown = BTreeSet::new();
    for item in &results.items {
        if !requested.contains(&item.id) {
            unknown.insert(item.id.clone());
        }
        if !seen.insert(item.id.clone()) {
            duplicate.insert(item.id.clone());
        }
    }
    let missing = requested.difference(&seen).cloned().collect();
    (missing, unknown.into_iter().collect(), duplicate.into_iter().collect())
}

fn classify_current_run(paths: &Paths) -> Result<RunSummary> {
    write_run_summary(paths)
}

fn publish_report_bundle(paths: &Paths) -> Result<()> {
    fs::create_dir_all(&paths.report_bundle_dir)?;
    for path in [
        paths.job_root.join("state/run-summary.json"),
        paths.job_root.join("state/qpdf-check.json"),
        paths.raw_completeness_report_json.clone(),
        paths.qdf_reference_report_json.clone(),
        paths.ocr_report_json.clone(),
        paths.font_report_json.clone(),
        paths.render_report_json.clone(),
        paths.translation_report_json.clone(),
        paths.encode_report_json.clone(),
        paths.rebuild_report_json.clone(),
        paths.validation_report_json.clone(),
        paths.structure_report_json.clone(),
        paths.term_application_report_json.clone(),
    ] {
        if path.exists() {
            let target = paths.report_bundle_dir.join(path.file_name().unwrap_or_default());
            fs::copy(path, target)?;
        }
    }
    Ok(())
}

fn cleanup_work_if_requested(paths: &Paths, summary: &RunSummary) -> Result<()> {
    let keep_work = !matches!(env_or_default("KEEP_WORK", "true").trim().to_ascii_lowercase().as_str(), "0" | "false" | "no" | "off");
    if keep_work || summary.degraded || summary.classification != "translated" {
        return Ok(());
    }
    for dir in [paths.job_root.join("qpdf"), paths.job_root.join("pdf"), paths.job_root.join("source")] {
        if dir.exists() {
            fs::remove_dir_all(dir)?;
        }
    }
    Ok(())
}

fn archive_input(path: &Path, classification: &str) -> Result<()> {
    let mode = env_or_default("INPUT_ARCHIVE_MODE", "off");
    if mode == "off" || !path.exists() {
        return Ok(());
    }
    let Some(input_dir) = path.parent().and_then(|parent| if parent.file_name().is_some_and(|name| name == "ready") { parent.parent() } else { Some(parent) }) else {
        return Ok(());
    };
    let target_dir = if matches!(classification, "translated" | "partial") { input_dir.join("done") } else { input_dir.join("failed") };
    fs::create_dir_all(&target_dir)?;
    let target = target_dir.join(path.file_name().unwrap_or_default());
    if mode == "move" {
        fs::rename(path, target)?;
    } else if mode == "copy" {
        fs::copy(path, target)?;
    }
    Ok(())
}

fn doctor() -> Result<()> {
    let root = project_root()?;
    let runtime = runtime_paths(&root);
    let mut issues = Vec::new();
    let qpdf_ok = match pdf_qpdf::ensure_qpdf() {
        Ok(()) => true,
        Err(err) => {
            issues.push(format!("qpdf: {err}"));
            false
        }
    };
    let provider = if std::env::var("AZURE_OPENAI_ENDPOINT").ok().filter(|value| !value.trim().is_empty()).is_some()
        && std::env::var("AZURE_OPENAI_DEPLOYMENT").ok().filter(|value| !value.trim().is_empty()).is_some()
    {
        "Azure OpenAI".to_string()
    } else {
        "OpenAI".to_string()
    };
    let glossary_path = project_relative_path(&root, &env_or_default("GLOSSARY_PATH", "glossary.csv"));
    let glossary_ok = pdf_terms::load_glossary_csv(&glossary_path).is_ok();
    if !glossary_ok {
        issues.push(format!("glossary CSV cannot be read: {}", glossary_path.display()));
    }
    let state_db_ok = StateDb::open(&runtime.work_dir.join("db/state.sqlite")).is_ok();
    let tm_db_ok = StateDb::open(&project_relative_path(&root, &env_or_default("TM_DB_PATH", "work/tm.sqlite"))).is_ok();
    let report = DoctorReport {
        ok: qpdf_ok && glossary_ok && state_db_ok && tm_db_ok,
        root: relative(&root, &root),
        qpdf_ok,
        provider,
        input_dir: relative(&runtime.input_dir, &root),
        output_dir: relative(&runtime.output_dir, &root),
        work_dir: relative(&runtime.work_dir, &root),
        glossary_ok,
        state_db_ok,
        tm_db_ok,
        issues,
    };
    write_json(&runtime.work_dir.join("doctor-report.json"), &report)?;
    println!("doctor ok={} report={}", report.ok, relative(&runtime.work_dir.join("doctor-report.json"), &root));
    Ok(())
}

fn status() -> Result<()> {
    let root = project_root()?;
    let runtime = runtime_paths(&root);
    if !runtime.work_dir.is_dir() {
        println!("no work directory: {}", runtime.work_dir.display());
        return Ok(());
    }
    for entry in fs::read_dir(&runtime.work_dir)? {
        let path = entry?.path();
        let summary_path = path.join("state/run-summary.json");
        if summary_path.is_file() {
            let summary = read_json::<RunSummary>(&summary_path)?;
            println!("{} {} changed={} output={}", summary.job, summary.classification, summary.changed_text_runs, summary.output_pdf);
        }
    }
    Ok(())
}

fn inspect(job: &str) -> Result<()> {
    let paths = paths_for_job(job, None)?;
    let summary_path = paths.job_root.join("state/run-summary.json");
    if summary_path.is_file() {
        let summary = read_json::<RunSummary>(&summary_path)?;
        println!("{}", serde_json::to_string_pretty(&summary)?);
        return Ok(());
    }
    Err(anyhow!("run summary not found for job {job}"))
}

fn project_root() -> Result<PathBuf> {
    let current = std::env::current_dir()?;
    find_project_root(current).ok_or_else(|| anyhow!("could not find pdf-translate-v9 project root from current directory"))
}

fn find_project_root(mut path: PathBuf) -> Option<PathBuf> {
    loop {
        if path.join("Cargo.toml").is_file() && path.join("crates").is_dir() {
            return Some(path);
        }
        if !path.pop() {
            return None;
        }
    }
}

fn sanitize_job_id(value: &str) -> String {
    value.chars()
        .map(|ch| if ch.is_ascii_alphanumeric() { ch.to_ascii_lowercase() } else { '-' })
        .collect::<String>()
        .split('-')
        .filter(|part| !part.is_empty())
        .collect::<Vec<_>>()
        .join("-")
}

fn read_json<T: serde::de::DeserializeOwned>(path: &Path) -> Result<T> {
    let text = fs::read_to_string(path).with_context(|| format!("read {}", path.display()))?;
    Ok(serde_json::from_str(&text).with_context(|| format!("parse {}", path.display()))?)
}

fn write_json<T: serde::Serialize>(path: &Path, value: &T) -> Result<()> {
    pdf_reports::write_json(path, value)
}

fn error_chain(err: &anyhow::Error) -> String {
    err.chain().map(|cause| cause.to_string()).collect::<Vec<_>>().join("; caused by: ")
}

fn sha256_file(path: &Path) -> Result<String> {
    let bytes = fs::read(path).with_context(|| format!("read {}", path.display()))?;
    Ok(hex::encode(Sha256::digest(&bytes)))
}

fn project_relative_path(root: &Path, value: &str) -> PathBuf {
    let path = PathBuf::from(value);
    if path.is_absolute() { path } else { root.join(path) }
}

fn relative(path: &Path, root: &Path) -> String {
    path.strip_prefix(root).unwrap_or(path).to_string_lossy().replace('\\', "/")
}
