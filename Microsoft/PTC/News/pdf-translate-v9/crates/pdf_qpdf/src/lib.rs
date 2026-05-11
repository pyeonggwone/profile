use anyhow::{anyhow, Context, Result};
use pdf_models::ValidationReport;
use std::collections::BTreeSet;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};

enum QpdfArg {
    Raw(String),
    Path(PathBuf),
}

impl QpdfArg {
    fn raw(value: &str) -> Self {
        Self::Raw(value.to_string())
    }

    fn path(value: &Path) -> Self {
        Self::Path(value.to_path_buf())
    }
}

pub fn ensure_qpdf() -> Result<()> {
    let (binary, output, _) = execute_qpdf(&[QpdfArg::raw("--version")])?;
    if output.status.success() {
        Ok(())
    } else {
        Err(anyhow!(
            "qpdf exists but failed through {binary}: {}",
            String::from_utf8_lossy(&output.stderr)
        ))
    }
}

pub fn create_qdf(source: &Path, output: &Path) -> Result<ValidationReport> {
    run_qpdf(&[
        QpdfArg::raw("--qdf"),
        QpdfArg::raw("--object-streams=disable"),
        QpdfArg::path(source),
        QpdfArg::path(output),
    ])
}

pub fn check_pdf(path: &Path) -> Result<ValidationReport> {
    run_qpdf(&[QpdfArg::raw("--check"), QpdfArg::path(path)])
}

fn run_qpdf(args: &[QpdfArg]) -> Result<ValidationReport> {
    let display_args = display_args(args)?;
    let (binary, output, resolved_args) = execute_qpdf(args)
        .with_context(|| format!("failed to execute qpdf {}", display_args.join(" ")))?;
    let command = format!("{binary} {}", resolved_args.join(" "));
    Ok(ValidationReport {
        ok: output.status.success(),
        command,
        exit_code: output.status.code(),
        stdout: String::from_utf8_lossy(&output.stdout).to_string(),
        stderr: String::from_utf8_lossy(&output.stderr).to_string(),
    })
}

fn execute_qpdf(args: &[QpdfArg]) -> Result<(String, Output, Vec<String>)> {
    let candidates = qpdf_candidates();
    let mut errors = Vec::new();
    for candidate in candidates {
        let resolved_args = resolve_args_for_binary(&candidate, args)?;
        match Command::new(&candidate).args(&resolved_args).output() {
            Ok(output) => return Ok((candidate, output, resolved_args)),
            Err(err) => errors.push(format!("{candidate}: {err}")),
        }
    }
    if errors.is_empty() {
        errors = expected_qpdf_candidates()
            .into_iter()
            .map(|candidate| format!("{candidate}: not found"))
            .collect();
    }
    Err(anyhow!(
        "qpdf is required but no project-local executable candidate could be run. Put qpdf under tools/qpdf/bin inside this project. Tried: {}",
        errors.join("; ")
    ))
}

fn qpdf_candidates() -> Vec<String> {
    let mut candidates = Vec::new();
    let root = project_root();
    if let Ok(value) = std::env::var("QPDF_BIN") {
        if !value.trim().is_empty() {
            push_qpdf_bin_value(&mut candidates, root.as_deref(), &value);
        }
    }
    if let Some(root) = root.as_deref() {
        push_project_qpdf_candidates(&mut candidates, root);
    }
    unique_existing_order(candidates)
}

fn expected_qpdf_candidates() -> Vec<String> {
    let root = project_root();
    if let Some(root) = root.as_deref() {
        return project_qpdf_candidate_paths(root)
            .into_iter()
            .filter_map(|path| path.to_str().map(|value| value.to_string()))
            .collect();
    }
    vec![
        "tools/qpdf/bin/qpdf".to_string(),
        "tools/qpdf/qpdf".to_string(),
        "tools/qpdf/bin/qpdf.exe".to_string(),
        "tools/qpdf/qpdf.exe".to_string(),
        "tools/bin/qpdf".to_string(),
        "tools/bin/qpdf.exe".to_string(),
    ]
}

fn push_qpdf_bin_value(candidates: &mut Vec<String>, root: Option<&Path>, value: &str) {
    let path = Path::new(value);
    if path.is_absolute() {
        push_if_file(candidates, path);
    } else if let Some(root) = root {
        push_if_file(candidates, &root.join(path));
    }
}

fn push_project_qpdf_candidates(candidates: &mut Vec<String>, root: &Path) {
    for path in project_qpdf_candidate_paths(root) {
        push_if_file(candidates, &path);
    }
}

fn project_qpdf_candidate_paths(root: &Path) -> Vec<PathBuf> {
    [
        "tools/qpdf/bin/qpdf",
        "tools/qpdf/qpdf",
        "tools/qpdf/bin/qpdf.exe",
        "tools/qpdf/qpdf.exe",
        "tools/bin/qpdf",
        "tools/bin/qpdf.exe",
    ]
    .into_iter()
    .map(|path| root.join(path))
    .collect()
}

fn push_if_file(candidates: &mut Vec<String>, path: &Path) {
    if path.is_file() {
        if let Some(value) = path.to_str() {
            candidates.push(value.to_string());
        }
    }
}

fn unique_existing_order(candidates: Vec<String>) -> Vec<String> {
    let mut seen = BTreeSet::new();
    candidates
        .into_iter()
        .filter(|value| seen.insert(value.to_ascii_lowercase()))
        .collect()
}

fn project_root() -> Option<PathBuf> {
    if let Ok(value) = std::env::var("PDF_TRANSLATE_ROOT") {
        let path = PathBuf::from(value);
        if path.exists() {
            return Some(path);
        }
    }
    let current = std::env::current_dir().ok()?;
    find_project_root(current)
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

fn resolve_args_for_binary(binary: &str, args: &[QpdfArg]) -> Result<Vec<String>> {
    args.iter()
        .map(|arg| match arg {
            QpdfArg::Raw(value) => Ok(value.clone()),
            QpdfArg::Path(path) => path_for_binary(binary, path),
        })
        .collect()
}

fn display_args(args: &[QpdfArg]) -> Result<Vec<String>> {
    resolve_args_for_binary("qpdf", args)
}

fn path_for_binary(binary: &str, path: &Path) -> Result<String> {
    let value = path
        .to_str()
        .ok_or_else(|| anyhow!("path is not UTF-8: {}", path.display()))?;
    if binary.to_ascii_lowercase().ends_with(".exe") {
        if let Some(windows_path) = wsl_mnt_path_to_windows(value) {
            return Ok(windows_path);
        }
    }
    Ok(value.to_string())
}

fn wsl_mnt_path_to_windows(path: &str) -> Option<String> {
    let rest = path.strip_prefix("/mnt/")?;
    let mut parts = rest.splitn(2, '/');
    let drive = parts.next()?;
    let tail = parts.next().unwrap_or_default();
    if drive.len() != 1 || !drive.as_bytes()[0].is_ascii_alphabetic() {
        return None;
    }
    Some(format!(
        "{}:\\{}",
        drive.to_ascii_uppercase(),
        tail.replace('/', "\\")
    ))
}

