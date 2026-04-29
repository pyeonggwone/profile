"""STEP 오케스트레이터. 각 STEP 은 파일 경로만 주고받는다."""
from __future__ import annotations

import json
from pathlib import Path

from ppt_translate.apply.inplace import apply_translations
from ppt_translate.config import settings
from ppt_translate.extract.shapes import extract_segments
from ppt_translate.translate.llm import translate_segments


def run_extract(pptx_path: Path, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    segments = extract_segments(pptx_path)
    out_path.write_text(json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def run_translate(segments_path: Path, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    segments = json.loads(segments_path.read_text(encoding="utf-8"))
    translated = translate_segments(segments)
    out_path.write_text(json.dumps(translated, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def run_apply(pptx_path: Path, translated_path: Path, out_path: Path | None) -> Path:
    out_path = out_path or pptx_path.with_stem(f"{pptx_path.stem}_{settings.target_lang.upper()}")
    translated = json.loads(translated_path.read_text(encoding="utf-8"))
    apply_translations(pptx_path, translated, out_path)
    return out_path


def run_full(pptx_path: Path, out_path: Path | None) -> Path:
    work = settings.work_dir / pptx_path.stem
    seg = run_extract(pptx_path, work / "segments.json")
    tr = run_translate(seg, work / "translated.json")
    return run_apply(pptx_path, tr, out_path)
