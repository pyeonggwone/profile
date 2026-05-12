from __future__ import annotations

import hashlib
import importlib.util
import shutil
from pathlib import Path

from .config import Config
from .encode import build_pdf_input_state
from .extract import extract_raw_text_state
from .jsonio import read_json, write_json
from .models import JobState, PdfSource, TranslationResultItem, TranslationResults, pdf_input_from_dict
from .paths import JobPaths, build_paths
from .progress import progress
from .qpdf import find_qpdf, qdf_reference
from .readable import build_translation_input, convert_raw_to_readable
from .rebuild import rebuild_pdf
from .state_db import StateDb
from .terms import extract_candidates, load_glossary
from .translate import translate
from .validation import validate_pdf


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_inputs(config: Config, input_path: Path | None) -> list[Path]:
    if input_path is None:
        ready = config.input_dir / "ready"
        root = ready if ready.exists() and any(ready.glob("*.pdf")) else config.input_dir
        return sorted(root.glob("*.pdf"))
    path = input_path if input_path.is_absolute() else config.root / input_path
    if path.is_dir():
        return sorted(path.glob("*.pdf"))
    return [path]


def _record_artifact(db: StateDb, paths: JobPaths, kind: str, path: Path) -> None:
    db.add_artifact(paths.job, kind, path.relative_to(paths.config.root) if path.is_relative_to(paths.config.root) else path)


def run_one(config: Config, source: Path) -> dict[str, object]:
    paths = build_paths(config, source)
    db = StateDb(config.state_db_path)
    try:
        progress(f"[job] start {paths.job} source={source.name}")
        source_hash = sha256_file(source)
        paths.source_pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, paths.source_pdf)
        job_state = JobState(paths.job, PdfSource(source.name, source.stat().st_size, source_hash, str(paths.source_pdf.relative_to(config.root))))
        write_json(paths.job_root / "state" / "job.json", job_state)
        db.upsert_job(paths.job, str(source), source_hash, "running")
        db.set_step(paths.job, "01_init_job", "completed")
        _record_artifact(db, paths, "job", paths.job_root / "state" / "job.json")
        progress(f"[job] {paths.job} 01_init_job completed")

        progress(f"[job] {paths.job} 02_qpdf_reference start")
        qdf_report = qdf_reference(config, paths.source_pdf, paths.qdf_pdf)
        write_json(paths.qdf_reference_report_json, qdf_report)
        if not qdf_report.ok and config.strict_tools and not config.allow_degraded:
            raise RuntimeError(qdf_report.stderr or "qpdf reference failed")
        db.set_step(paths.job, "02_qpdf_reference", "completed" if qdf_report.ok else "degraded", qdf_report.stderr)
        progress(f"[job] {paths.job} 02_qpdf_reference {'completed' if qdf_report.ok else 'degraded'}")

        progress(f"[job] {paths.job} 03_extract_raw_pdf_text_state start")
        raw, raw_report = extract_raw_text_state(paths.source_pdf)
        write_json(paths.raw_json, raw)
        write_json(paths.raw_completeness_report_json, raw_report)
        db.set_step(paths.job, "03_extract_raw_pdf_text_state", "completed")
        raw_run_count = sum(len(content.textRuns) for page in raw.pages for content in page.contents)
        progress(f"[job] {paths.job} 03_extract_raw_pdf_text_state completed pages={len(raw.pages)} runs={raw_run_count}")

        progress(f"[job] {paths.job} 04_convert_raw_to_readable_text_state start")
        readable = convert_raw_to_readable(raw)
        write_json(paths.readable_json, readable)
        db.set_step(paths.job, "04_convert_raw_to_readable_text_state", "completed")
        progress(f"[job] {paths.job} 04_convert_raw_to_readable_text_state completed items={len(readable.items)}")

        progress(f"[job] {paths.job} 05_extract_and_apply_job_terms start")
        candidates = {"candidates": extract_candidates(readable)}
        terms = load_glossary(config.glossary_path)
        write_json(paths.candidates_json, candidates)
        write_json(paths.terms_json, {"terms": terms})
        db.set_step(paths.job, "05_extract_and_apply_job_terms", "completed")
        progress(f"[job] {paths.job} 05_extract_and_apply_job_terms completed candidates={len(candidates['candidates'])} terms={len(terms)}")

        progress(f"[job] {paths.job} 06_translate_readable_text_state start")
        translation_input = build_translation_input(readable, terms)
        write_json(paths.translation_input_json, translation_input)
        translations, translation_report = translate(translation_input, config, paths.job_root)
        write_json(paths.translation_results_json, translations)
        write_json(paths.translation_report_json, translation_report)
        if translation_report.issues:
            write_json(paths.translation_error_json, translation_report.issues[0])
        db.set_step(paths.job, "06_translate_readable_text_state", "completed" if translation_report.ok else "degraded")
        progress(f"[job] {paths.job} 06_translate_readable_text_state {'completed' if translation_report.ok else 'degraded'} translated={translation_report.translated} fallback={translation_report.fallback} chunks={len(translation_report.chunks)}")

        progress(f"[job] {paths.job} 07_convert_translation_to_pdf_input_state start")
        pdf_input, encode_report = build_pdf_input_state(raw, translations)
        write_json(paths.pdf_input_json, pdf_input)
        write_json(paths.encode_report_json, encode_report)
        db.set_step(paths.job, "07_convert_translation_to_pdf_input_state", "completed" if encode_report.ok else "degraded")
        progress(f"[job] {paths.job} 07_convert_translation_to_pdf_input_state {'completed' if encode_report.ok else 'degraded'} ok={encode_report.okCount} failed={encode_report.failedCount}")

        progress(f"[job] {paths.job} 08_rebuild_pdf_with_extracted_options start")
        rebuild_report = rebuild_pdf(paths.source_pdf, pdf_input, paths, config)
        write_json(paths.rebuild_report_json, rebuild_report)
        db.set_step(paths.job, "08_rebuild_pdf_with_extracted_options", "completed" if rebuild_report.ok else "degraded")
        progress(f"[job] {paths.job} 08_rebuild_pdf_with_extracted_options {'completed' if rebuild_report.ok else 'degraded'} replaced={rebuild_report.replaced} failed={len(rebuild_report.failed)}")

        progress(f"[job] {paths.job} 09_qpdf_validate_output start")
        validation_report = validate_pdf(config, paths.rebuilt_pdf)
        write_json(paths.validation_report_json, validation_report)
        db.set_step(paths.job, "09_qpdf_validate_output", "completed" if validation_report.ok else "failed")
        progress(f"[job] {paths.job} 09_qpdf_validate_output {'completed' if validation_report.ok else 'failed'}")

        progress(f"[job] {paths.job} 10_publish_output start")
        publish_target = paths.validated_pdf if validation_report.ok and rebuild_report.ok else paths.rejected_pdf
        publish_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(paths.rebuilt_pdf, publish_target)
        paths.report_bundle_dir.mkdir(parents=True, exist_ok=True)
        for report_path in paths.job_root.glob("reports/*.json"):
            shutil.copy2(report_path, paths.report_bundle_dir / report_path.name)
        summary = {
            "job": paths.job,
            "sourcePdf": str(paths.source_pdf.relative_to(config.root)),
            "outputPdf": str(publish_target.relative_to(config.root)),
            "classification": "translated" if validation_report.ok and rebuild_report.ok else "fallback",
            "fallbackUsed": not rebuild_report.ok,
            "validatedPdf": str(paths.validated_pdf.relative_to(config.root)) if publish_target == paths.validated_pdf else None,
            "rejectedPdf": str(paths.rejected_pdf.relative_to(config.root)) if publish_target == paths.rejected_pdf else None,
            "sourceSha256": source_hash,
            "outputSha256": sha256_file(publish_target),
            "degraded": not rebuild_report.ok or not translation_report.ok or not encode_report.ok,
            "translationError": not translation_report.ok,
            "textRuns": encode_report.total,
            "changedTextRuns": sum(1 for item in translations.items if item.translated),
            "unchangedTextRuns": 0,
            "encodeOk": encode_report.okCount,
            "encodeFailed": encode_report.failedCount,
            "rebuildOk": rebuild_report.ok,
            "rebuildReplaced": rebuild_report.replaced,
            "rebuildFailed": len(rebuild_report.failed),
            "textlessBasePdf": str(paths.textless_base_pdf.relative_to(config.root)),
            "clonePdfminerPdf": str(paths.clone_pdfminer_pdf.relative_to(config.root)),
            "clonePdfplumberPdf": str(paths.clone_pdfplumber_pdf.relative_to(config.root)),
            "translatedRenderPdf": str(paths.translated_render_pdf.relative_to(config.root)),
            "validationOk": validation_report.ok,
            "notes": [issue.message for issue in rebuild_report.failed],
        }
        write_json(paths.job_root / "state" / "run-summary.json", summary)
        write_json(paths.report_bundle_dir / "run-summary.json", summary)
        db.set_step(paths.job, "10_publish_output", "completed")
        db.upsert_job(paths.job, str(source), source_hash, "completed")
        progress(f"[job] completed {paths.job} output={publish_target.relative_to(config.root)}")
        return summary
    finally:
        db.close()


def run_batch(config: Config, input_path: Path | None = None) -> list[dict[str, object]]:
    config.input_dir.mkdir(parents=True, exist_ok=True)
    config.output_dir.joinpath("validated").mkdir(parents=True, exist_ok=True)
    config.output_dir.joinpath("rejected").mkdir(parents=True, exist_ok=True)
    config.output_dir.joinpath("reports").mkdir(parents=True, exist_ok=True)
    config.work_dir.mkdir(parents=True, exist_ok=True)
    sources = discover_inputs(config, input_path)
    progress(f"[batch] inputs={len(sources)}")
    summaries = []
    for index, source in enumerate(sources, start=1):
        progress(f"[batch] file {index}/{len(sources)} {source.name}")
        summaries.append(run_one(config, source))
    progress(f"[batch] completed inputs={len(summaries)}")
    return summaries


def _translation_results_from_dict(data: dict[str, object]) -> TranslationResults:
    return TranslationResults([TranslationResultItem(str(item["id"]), str(item["translated"])) for item in data.get("items", [])])


def _needs_text_compose_refresh(pdf_input) -> bool:
    return not any(run.restoreOptions.textState.textMatrix for run in pdf_input.textRuns)


def _publish_finalize_output(config: Config, paths: JobPaths, rebuild_ok: bool, validation_ok: bool) -> Path:
    target = paths.validated_pdf if rebuild_ok and validation_ok else paths.rejected_pdf
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(paths.rebuilt_pdf, target)
    paths.report_bundle_dir.mkdir(parents=True, exist_ok=True)
    for report_path in paths.job_root.glob("reports/*.json"):
        shutil.copy2(report_path, paths.report_bundle_dir / report_path.name)
    progress(f"[finalize] published {target.relative_to(config.root)}")
    return target


def finalize(config: Config, job: str) -> dict[str, object]:
    paths = build_paths(config, job)
    source_pdf = paths.source_pdf
    pdf_input = pdf_input_from_dict(read_json(paths.pdf_input_json))

    if _needs_text_compose_refresh(pdf_input) and paths.translation_results_json.exists():
        progress(f"[finalize] {paths.job} refreshing raw extraction for text composition coordinates")
        raw, raw_report = extract_raw_text_state(source_pdf)
        translations = _translation_results_from_dict(read_json(paths.translation_results_json))
        pdf_input, encode_report = build_pdf_input_state(raw, translations)
        write_json(paths.raw_json, raw)
        write_json(paths.raw_completeness_report_json, raw_report)
        write_json(paths.pdf_input_json, pdf_input)
        write_json(paths.encode_report_json, encode_report)
        progress(f"[finalize] {paths.job} text compose encode ok={encode_report.okCount} failed={encode_report.failedCount}")

    rebuild_report = rebuild_pdf(source_pdf, pdf_input, paths, config)
    write_json(paths.rebuild_report_json, rebuild_report)
    validation_report = validate_pdf(config, paths.rebuilt_pdf)
    write_json(paths.validation_report_json, validation_report)
    output_pdf = _publish_finalize_output(config, paths, rebuild_report.ok, validation_report.ok)
    summary = {
        "job": job,
        "outputPdf": str(output_pdf.relative_to(config.root)),
        "sourceSha256": sha256_file(source_pdf),
        "outputSha256": sha256_file(output_pdf),
        "rebuildOk": rebuild_report.ok,
        "rebuildReplaced": rebuild_report.replaced,
        "rebuildFailed": len(rebuild_report.failed),
        "textlessBasePdf": str(paths.textless_base_pdf.relative_to(config.root)),
        "clonePdfminerPdf": str(paths.clone_pdfminer_pdf.relative_to(config.root)),
        "clonePdfplumberPdf": str(paths.clone_pdfplumber_pdf.relative_to(config.root)),
        "translatedRenderPdf": str(paths.translated_render_pdf.relative_to(config.root)),
        "validationOk": validation_report.ok,
        "classification": "translated" if rebuild_report.ok and validation_report.ok else "fallback",
        "notes": [issue.message for issue in rebuild_report.failed],
    }
    write_json(paths.job_root / "state" / "finalize-summary.json", summary)
    write_json(paths.report_bundle_dir / "finalize-summary.json", summary)
    return summary


def doctor(config: Config) -> dict[str, object]:
    qpdf = find_qpdf(config)
    text_font = next((path for path in [config.font_regular, config.font_fallback, config.font_bold, config.root.parent / "pdf-translate-v9" / "fonts" / "malgun.ttf"] if path and path.exists()), None)
    reportlab_ok = importlib.util.find_spec("reportlab") is not None
    issues = []
    if qpdf is None:
        issues.append("project-local qpdf not found")
    if not reportlab_ok:
        issues.append("reportlab is not installed; run: python -m pip install -e .")
    if text_font is None:
        issues.append("text render font not found; copy fonts from v9 or set FONT_REGULAR/FONT_FALLBACK")
    return {
        "ok": qpdf is not None and reportlab_ok and text_font is not None,
        "root": str(config.root),
        "packageSource": str(Path(__file__).resolve().parents[1]),
        "features": {
            "progressLog": True,
            "parallelTranslation": True,
            "textlessBaseRebuild": True,
            "pdfminerOriginalClone": True,
            "pdfplumberOriginalClone": True,
            "translatedTextCompose": True,
        },
        "qpdfOk": qpdf is not None,
        "qpdf": str(qpdf) if qpdf else None,
        "provider": config.openai_provider,
        "renderMode": config.pdf_translation_render_mode,
        "reportlabOk": reportlab_ok,
        "textFontOk": text_font is not None,
        "textFont": str(text_font) if text_font else None,
        "inputDir": str(config.input_dir),
        "outputDir": str(config.output_dir),
        "workDir": str(config.work_dir),
        "glossaryOk": config.glossary_path.exists(),
        "issues": issues,
    }