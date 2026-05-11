use pdf_models::{JobTerm, JobTerms, ProperNounCandidates, ReadableTextState};
use regex::Regex;
use std::collections::BTreeSet;

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
