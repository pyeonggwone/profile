use anyhow::{anyhow, Context, Result};
use pdf_models::{JobTerm, JobTerms, ProperNounCandidates, ReadableTextState};
use regex::Regex;
use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

pub fn extract_candidates(readable: &ReadableTextState) -> ProperNounCandidates {
    let re = Regex::new(r"\b[A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*)*\b").unwrap();
    let mut values = BTreeSet::new();
    for item in &readable.items {
        for m in re.find_iter(&item.source) {
            let value = m.as_str().trim();
            if value.len() > 1 {
                values.insert(value.to_string());
            }
        }
    }
    ProperNounCandidates {
        candidates: values.into_iter().collect(),
    }
}

pub fn default_job_terms(candidates: &ProperNounCandidates) -> JobTerms {
    JobTerms {
        terms: candidates
            .candidates
            .iter()
            .map(|term| JobTerm {
                term: term.clone(),
                translation: None,
                mode: "preserve".to_string(),
            })
            .collect(),
    }
}

pub fn load_glossary_csv(path: &Path) -> Result<JobTerms> {
    if !path.exists() {
        return Ok(JobTerms::default());
    }
    let mut reader = csv::ReaderBuilder::new()
        .trim(csv::Trim::All)
        .from_path(path)
        .with_context(|| format!("open glossary CSV {}", path.display()))?;
    let headers = reader.headers().context("read glossary CSV headers")?.clone();
    let term_index = header_index(&headers, &["term", "source", "source_term"])?;
    let translation_index = optional_header_index(&headers, &["translation", "target", "target_term"]);
    let mode_index = optional_header_index(&headers, &["mode"]);

    let mut terms = Vec::new();
    for (row_number, record) in reader.records().enumerate() {
        let record = record.with_context(|| format!("read glossary CSV row {}", row_number + 2))?;
        let term = record.get(term_index).unwrap_or_default().trim();
        if term.is_empty() {
            continue;
        }
        let translation = translation_index
            .and_then(|index| record.get(index))
            .map(str::trim)
            .filter(|value| !value.is_empty())
            .map(ToOwned::to_owned);
        let mode = mode_index
            .and_then(|index| record.get(index))
            .map(str::trim)
            .filter(|value| !value.is_empty())
            .map(ToOwned::to_owned)
            .unwrap_or_else(|| if translation.is_some() { "fixed".to_string() } else { "preserve".to_string() });
        terms.push(JobTerm { term: term.to_string(), translation, mode });
    }
    Ok(JobTerms { terms })
}

pub fn merge_job_terms(auto_terms: JobTerms, glossary_terms: JobTerms) -> JobTerms {
    let mut merged = BTreeMap::new();
    for term in auto_terms.terms {
        merged.insert(term.term.clone(), term);
    }
    for term in glossary_terms.terms {
        merged.insert(term.term.clone(), term);
    }
    JobTerms { terms: merged.into_values().collect() }
}

fn header_index(headers: &csv::StringRecord, names: &[&str]) -> Result<usize> {
    optional_header_index(headers, names).ok_or_else(|| anyhow!("glossary CSV must include one of these headers: {}", names.join(", ")))
}

fn optional_header_index(headers: &csv::StringRecord, names: &[&str]) -> Option<usize> {
    headers.iter().position(|header| names.iter().any(|name| header.eq_ignore_ascii_case(name)))
}
