use std::path::PathBuf;

use anyhow::{Context, Result};
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "pdftr", about = "pdf-translate-v3 PDF inspection / edit / roundtrip CLI")]
struct Cli {
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand)]
enum Cmd {
    /// Print PDF version, page count, /Info dictionary and warnings.
    Inspect {
        path: PathBuf,
        #[arg(long)]
        json: bool,
    },
    /// Extract per-page text runs.
    Text {
        path: PathBuf,
        #[arg(long)]
        json: bool,
    },
    /// Build a render plan as JSON for a given page (1-based).
    RenderPlan { path: PathBuf, page: u32 },
    /// Apply a JSON edit operation file as an incremental update.
    /// `--edits` should be a JSON array of `EditOperation` objects.
    Edit {
        input: PathBuf,
        output: PathBuf,
        #[arg(long)]
        edits: PathBuf,
    },
    /// Verify roundtrip: read -> incremental update with no operations
    /// -> ensure the output prefix matches the input bytes.
    Roundtrip { path: PathBuf },
}

fn main() -> Result<()> {
    let cli = Cli::parse();
    match cli.cmd {
        Cmd::Inspect { path, json } => inspect(path, json),
        Cmd::Text { path, json } => text(path, json),
        Cmd::RenderPlan { path, page } => render_plan(path, page),
        Cmd::Edit {
            input,
            output,
            edits,
        } => edit(input, output, edits),
        Cmd::Roundtrip { path } => roundtrip(path),
    }
}

fn read_pdf(path: &PathBuf) -> Result<pdf_reader::ParsedPdf> {
    let bytes = std::fs::read(path).with_context(|| format!("read {path:?}"))?;
    pdf_reader::ParsedPdf::from_bytes(bytes).map_err(Into::into)
}

fn inspect(path: PathBuf, json: bool) -> Result<()> {
    let doc = read_pdf(&path)?;
    let summary = pdf_analysis::summary::summarize(&doc)?;
    if json {
        println!("{}", serde_json::to_string_pretty(&summary)?);
    } else {
        println!("PDF version : {}", summary.pdf_version);
        println!("Pages       : {}", summary.page_count);
        println!("Encrypted   : {}", summary.encrypted);
        if let Some(t) = &summary.title {
            println!("Title       : {t}");
        }
        if let Some(a) = &summary.author {
            println!("Author      : {a}");
        }
        if let Some(p) = &summary.producer {
            println!("Producer    : {p}");
        }
        if !summary.warnings.is_empty() {
            println!("Warnings    :");
            for w in &summary.warnings {
                println!("  - {w}");
            }
        }
    }
    Ok(())
}

fn text(path: PathBuf, json: bool) -> Result<()> {
    let doc = read_pdf(&path)?;
    let pages = pdf_analysis::extract_text(&doc)?;
    if json {
        println!("{}", serde_json::to_string_pretty(&pages)?);
    } else {
        for p in &pages {
            println!("--- page {} ({}x{}) ---", p.page, p.width, p.height);
            for run in &p.runs {
                println!("  [{:>7.2},{:>7.2}] {}", run.x, run.y, run.text);
            }
        }
    }
    Ok(())
}

fn render_plan(path: PathBuf, page: u32) -> Result<()> {
    let doc = read_pdf(&path)?;
    let plans = pdf_render_plan::build_render_plan(&doc)?;
    let plan = plans
        .into_iter()
        .find(|p| p.page == page)
        .ok_or_else(|| anyhow::anyhow!("page {page} not found"))?;
    println!("{}", serde_json::to_string_pretty(&plan)?);
    Ok(())
}

fn edit(input: PathBuf, output: PathBuf, edits_path: PathBuf) -> Result<()> {
    let doc = read_pdf(&input)?;
    let edits_bytes = std::fs::read(&edits_path).with_context(|| format!("read {edits_path:?}"))?;
    let edits: Vec<pdf_incremental::EditOperation> =
        serde_json::from_slice(&edits_bytes).context("parse edit JSON")?;
    let writer = pdf_incremental::IncrementalWriter::new(&doc);
    let update = writer.build(&edits)?;
    std::fs::write(&output, &update.bytes).with_context(|| format!("write {output:?}"))?;
    println!(
        "wrote {} bytes ({} new objects) to {:?}",
        update.bytes.len(),
        update.new_objects.len(),
        output
    );
    Ok(())
}

fn roundtrip(path: PathBuf) -> Result<()> {
    let bytes = std::fs::read(&path)?;
    let doc = pdf_reader::ParsedPdf::from_bytes(bytes.clone())?;
    let writer = pdf_incremental::IncrementalWriter::new(&doc);
    let update = writer.build(&[])?;
    if update.bytes.len() < bytes.len() {
        anyhow::bail!(
            "incremental output ({}) is shorter than original ({})",
            update.bytes.len(),
            bytes.len()
        );
    }
    let prefix = &update.bytes[..bytes.len()];
    if prefix != bytes.as_slice() {
        anyhow::bail!("original prefix changed during incremental update");
    }
    // Reopen
    let _ = pdf_reader::ParsedPdf::from_bytes(update.bytes)?;
    println!("roundtrip OK: {} bytes preserved", bytes.len());
    Ok(())
}
