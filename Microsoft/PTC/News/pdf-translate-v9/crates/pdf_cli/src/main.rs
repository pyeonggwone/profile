use anyhow::{anyhow, Context, Result};
use clap::{Parser, Subcommand};
use pdf_models::*;
use pdf_state_db::StateDb;
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

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
    rebuilt_pdf: PathBuf,
    output_pdf: PathBuf,
    state_db: PathBuf,
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

fn run_requested_input(input: Option<&Path>, source_lang: &str, target_lang: &str, model: &str) -> Result<()> {
    let root = project_root()?;
    let target = input.map(PathBuf::from).unwrap_or_else(|| root.join("input"));
    if target.is_file() {
        return run_pipeline(&target, source_lang, target_lang, model);
    }
    if target.exists() && !target.is_dir() {
        return Err(anyhow!("input path is neither a PDF file nor a directory: {}", target.display()));
    }
    run_directory(&target, source_lang, target_lang, model)
}

fn run_directory(input_dir: &Path, source_lang: &str, target_lang: &str, model: &str) -> Result<()> {
    fs::create_dir_all(input_dir).with_context(|| format!("create input directory {}", input_dir.display()))?;
    let mut pdfs = Vec::new();
    for entry in fs::read_dir(input_dir).with_context(|| format!("read input directory {}", input_dir.display()))? {
        let path = entry?.path();
        if path.is_file() && path.extension().and_then(|value| value.to_str()).is_some_and(|ext| ext.eq_ignore_ascii_case("pdf")) {
            pdfs.push(path);
        }
    }
    pdfs.sort_by(|left, right| left.file_name().cmp(&right.file_name()));
    if pdfs.is_empty() {
        return Err(anyhow!("no PDF files found in {}", input_dir.display()));
    }

    let mut failed = Vec::new();
    for pdf in pdfs {
        match run_pipeline(&pdf, source_lang, target_lang, model) {
            Ok(()) => println!("completed {}", pdf.display()),
            Err(err) => {
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

fn run_pipeline(input: &Path, source_lang: &str, target_lang: &str, model: &str) -> Result<()> {
    let paths = init_job(input)?;
    let db = StateDb::open(&paths.state_db)?;
    let source = read_json::<PdfSource>(&paths.job_root.join("state/pdf-source.json"))?;
    db.upsert_job(&paths.job, &source.path, &source.sha256, "running")?;

    step(&db, &paths.job, "02_qpdf_reference", || qpdf_reference(&paths))?;
    step(&db, &paths.job, "03_extract_raw_pdf_text_state", || extract_raw(&paths))?;
    step(&db, &paths.job, "04_convert_raw_to_readable_text_state", || convert_readable(&paths))?;
    step(&db, &paths.job, "05_extract_and_apply_job_terms", || extract_terms(&paths))?;
    step(&db, &paths.job, "06_translate_readable_text_state", || translate(&paths, source_lang, target_lang, model))?;
    step(&db, &paths.job, "07_convert_translation_to_pdf_input_state", || convert_pdf_input(&paths))?;
    step(&db, &paths.job, "08_rebuild_pdf_with_extracted_options", || rebuild(&paths))?;
    step(&db, &paths.job, "09_qpdf_validate_output", || validate_output(&paths))?;
    step(&db, &paths.job, "10_publish_output", || publish(&paths))?;
    db.upsert_job(&paths.job, &source.path, &source.sha256, "completed")?;
    Ok(())
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
                        source,
                        restore_options_ref: RestoreOptionsRef {
                            stream_xref: run.restore_options.stream_xref,
                            operator: run.restore_options.operator,
                        },
                        decode: DecodeStatus { method, confidence: if issues.is_empty() { "high" } else { "low" }.to_string(), issues },
                        layout: LayoutInfo { matrix: run.restore_options.text_state.text_matrix },
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
    let terms = pdf_terms::default_job_terms(&candidates);
    write_json(&paths.candidates_json, &candidates)?;
    write_json(&paths.terms_json, &terms)
}

fn translate(paths: &Paths, source_lang: &str, target_lang: &str, model: &str) -> Result<()> {
    let readable = read_json::<ReadableTextState>(&paths.readable_json)?;
    let terms = read_json::<JobTerms>(&paths.terms_json).unwrap_or_default();
    let db = StateDb::open(&paths.state_db)?;
    let mut cached_results = Vec::new();
    let mut misses = Vec::new();
    for item in &readable.items {
        if let Some(translated) = db.tm_get(&item.source, source_lang, target_lang)? {
            cached_results.push(TranslationResultItem { id: item.id.clone(), translated });
        } else {
            misses.push(TranslationInputItem { id: item.id.clone(), text: item.source.clone() });
        }
    }
    let input = TranslationInput {
        items: misses,
        terms: terms.terms,
    };
    write_json(&paths.translation_input_json, &input)?;
    let mut results = TranslationResults { items: cached_results };
    if !input.items.is_empty() {
        let api_key = std::env::var("OPENAI_API_KEY").context("OPENAI_API_KEY is required for translation misses")?;
        let fresh = pdf_translate_openai::translate(&input, &pdf_translate_openai::OpenAiConfig {
            api_key,
            model: model.to_string(),
            source_lang: source_lang.to_string(),
            target_lang: target_lang.to_string(),
        })?;
        let source_by_id: BTreeMap<String, String> = input.items.iter().map(|item| (item.id.clone(), item.text.clone())).collect();
        for item in fresh.items {
            if let Some(source_text) = source_by_id.get(&item.id) {
                db.tm_put(source_text, &item.translated, source_lang, target_lang, model)?;
            }
            results.items.push(item);
        }
    }
    write_json(&paths.translation_results_json, &results)
}

fn convert_pdf_input(paths: &Paths) -> Result<()> {
    let raw = read_json::<RawPdfTextState>(&paths.raw_json)?;
    let translations = read_json::<TranslationResults>(&paths.translation_results_json)?;
    let map: BTreeMap<String, String> = translations.items.into_iter().map(|item| (item.id, item.translated)).collect();
    let mut output = PdfInputTextState::default();
    for page in raw.pages {
        for content in page.contents {
            for mut run in content.text_runs {
                let Some(translated) = map.get(&run.id).cloned() else { continue; };
                let replacement = pdf_cmap::encode_replacement_like(&run.text_payload.encoded_original, &translated);
                let (status, replacement_encoded, issues) = match replacement {
                    Ok(value) => ("ok".to_string(), Some(value), Vec::new()),
                    Err(err) => ("failed".to_string(), None, vec![err.to_string()]),
                };
                let decoded_original = run.text_payload.decoded_original.clone().or_else(|| pdf_cmap::decode_pdf_operand(&run.text_payload.encoded_original).0);
                run.text_payload.decoded_original = decoded_original;
                run.text_payload.decoded_translated = Some(translated);
                run.text_payload.replacement_encoded = replacement_encoded;
                output.text_runs.push(PdfInputTextRun {
                    id: run.id,
                    restore_options: run.restore_options,
                    text_payload: run.text_payload,
                    encode: EncodeStatus { method: "original-font-cmap".to_string(), status, issues },
                });
            }
        }
    }
    write_json(&paths.pdf_input_json, &output)
}

fn rebuild(paths: &Paths) -> Result<()> {
    let input = read_json::<PdfInputTextState>(&paths.pdf_input_json)?;
    let report = match pdf_rebuild::rebuild_pdf(&paths.source_pdf, &input, &paths.rebuilt_pdf) {
        Ok(report) => report,
        Err(err) => {
            let report = RebuildReport { ok: false, replaced: 0, failed: vec![ReportIssue { id: None, message: err.to_string() }] };
            write_json(&paths.rebuild_report_json, &report)?;
            return Err(err);
        }
    };
    write_json(&paths.rebuild_report_json, &report)
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
            return Ok(());
        }
        return Err(err);
    }
    let report = pdf_qpdf::check_pdf(&paths.rebuilt_pdf)?;
    write_json(&paths.validation_report_json, &report)?;
    if report.ok { Ok(()) } else { Err(anyhow!("qpdf validation failed")) }
}

fn publish(paths: &Paths) -> Result<()> {
    fs::create_dir_all(paths.output_pdf.parent().unwrap())?;
    fs::copy(&paths.rebuilt_pdf, &paths.output_pdf)?;
    Ok(())
}

fn paths_for_job(job: &str, input: Option<&Path>) -> Result<Paths> {
    let root = project_root()?;
    let job_root = root.join("work").join(job);
    let source_name = input
        .and_then(|p| p.file_name())
        .and_then(|v| v.to_str())
        .unwrap_or("source.pdf");
    Ok(Paths {
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
        rebuilt_pdf: job_root.join("pdf/rebuilt.pdf"),
        output_pdf: root.join("output/validated").join(format!("{}_V9.pdf", Path::new(source_name).file_stem().unwrap_or_default().to_string_lossy())),
        state_db: root.join("work/db/state.sqlite"),
    })
}

fn create_job_dirs(paths: &Paths) -> Result<()> {
    for dir in ["source", "qpdf", "state", "pdf", "reports"] {
        fs::create_dir_all(paths.job_root.join(dir))?;
    }
    fs::create_dir_all(paths.root.join("output/validated"))?;
    fs::create_dir_all(paths.root.join("work/db"))?;
    Ok(())
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

fn relative(path: &Path, root: &Path) -> String {
    path.strip_prefix(root).unwrap_or(path).to_string_lossy().replace('\\', "/")
}
