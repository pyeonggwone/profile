from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .config import Config


def slugify(name: str) -> str:
    stem = Path(name).stem.lower()
    stem = re.sub(r"[^a-z0-9가-힣]+", "-", stem).strip("-")
    return stem or "job"


@dataclass
class JobPaths:
    config: Config
    job: str
    job_root: Path
    source_pdf: Path
    qdf_pdf: Path
    raw_json: Path
    readable_json: Path
    candidates_json: Path
    terms_json: Path
    translation_input_json: Path
    translation_results_json: Path
    translation_error_json: Path
    pdf_input_json: Path
    rebuild_report_json: Path
    validation_report_json: Path
    raw_completeness_report_json: Path
    qdf_reference_report_json: Path
    encode_report_json: Path
    translation_report_json: Path
    structure_report_json: Path
    textless_base_pdf: Path
    clone_pdfminer_pdf: Path
    clone_pdfplumber_pdf: Path
    translated_render_pdf: Path
    rebuilt_pdf: Path
    validated_pdf: Path
    rejected_pdf: Path
    report_bundle_dir: Path


def build_paths(config: Config, source: Path | str) -> JobPaths:
    job = slugify(str(source))
    job_root = config.work_dir / "jobs" / job
    state = job_root / "state"
    reports = job_root / "reports"
    source_name = Path(source).name
    output_name = f"{Path(source_name).stem}_V10.pdf"
    return JobPaths(
        config=config,
        job=job,
        job_root=job_root,
        source_pdf=job_root / "source" / "source.pdf",
        qdf_pdf=job_root / "qpdf" / "source.qdf.pdf",
        raw_json=state / "raw-pdf-text-state.json",
        readable_json=state / "readable-text-state.json",
        candidates_json=state / "proper-noun-candidates.json",
        terms_json=state / "job-terms.json",
        translation_input_json=state / "translation-input.json",
        translation_results_json=state / "translation-results.json",
        translation_error_json=state / "translation-error.json",
        pdf_input_json=state / "pdf-input-text-state.json",
        rebuild_report_json=reports / "rebuild-report.json",
        validation_report_json=reports / "validation-report.json",
        raw_completeness_report_json=reports / "raw-completeness-report.json",
        qdf_reference_report_json=reports / "qdf-reference-report.json",
        encode_report_json=reports / "encode-report.json",
        translation_report_json=reports / "translation-report.json",
        structure_report_json=reports / "structure-report.json",
        textless_base_pdf=job_root / "pdf" / "textless-base.pdf",
        clone_pdfminer_pdf=job_root / "pdf" / "clone-pdfminer.pdf",
        clone_pdfplumber_pdf=job_root / "pdf" / "clone-pdfplumber.pdf",
        translated_render_pdf=job_root / "pdf" / "translated.pdf",
        rebuilt_pdf=job_root / "pdf" / "rebuilt.pdf",
        validated_pdf=config.output_dir / "validated" / output_name,
        rejected_pdf=config.output_dir / "rejected" / output_name,
        report_bundle_dir=config.output_dir / "reports" / job,
    )