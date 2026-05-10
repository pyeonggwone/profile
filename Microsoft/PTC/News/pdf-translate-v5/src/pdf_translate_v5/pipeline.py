from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
STEP_ORDER = [
    "01_init_job",
    "02_validate_source_pdf",
    "03_extract_object_manifest",
    "04_render_source_pages",
    "05_extract_text_bbox",
    "06_analyze_fonts",
    "07_detect_tables",
    "08_extract_image_text",
    "09_build_segments",
    "10_translate_segments",
    "11_shape_text",
    "12_layout_text",
    "13_build_draft_pdf",
    "14_restore_pdf_objects",
    "15_optimize_pdf",
    "16_validate_output_pdf",
    "17_render_diff",
    "18_publish_output",
]


class StepError(RuntimeError):
    def __init__(self, step: str, message: str, recoverable: bool = False):
        super().__init__(message)
        self.step = step
        self.recoverable = recoverable


@dataclass
class Config:
    source_lang: str
    target_lang: str
    input_dir: Path
    output_dir: Path
    work_dir: Path
    glossary_path: Path
    tm_db_path: Path
    translation_mode: str
    openai_api_key: str
    openai_model: str
    azure_openai_api_key: str
    azure_openai_endpoint: str
    azure_openai_api_version: str
    azure_openai_deployment: str
    ocr_mode: str
    azure_vision_endpoint: str
    azure_vision_key: str
    font_regular: str
    font_bold: str
    font_fallback: str
    render_scale: float
    render_diff_warn_mean: float
    render_diff_fail_mean: float
    strict_tools: bool
    allow_degraded: bool
    keep_work: bool


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def bool_value(value: str | None, fallback: bool) -> bool:
    if value is None or value == "":
        return fallback
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def float_value(value: str | None, fallback: float) -> float:
    try:
        return float(value) if value not in {None, ""} else fallback
    except Exception:
        return fallback


def load_config(args: argparse.Namespace) -> Config:
    env_file_values = read_env_file(ROOT / ".env")

    def env(key: str, fallback: str = "") -> str:
        return os.environ.get(key) or env_file_values.get(key) or fallback

    source_lang = args.in_lang or env("SOURCE_LANG", "en")
    target_lang = args.out_lang or env("TARGET_LANG", "kr")
    work_dir = ROOT / env("WORK_DIR", "work")
    return Config(
        source_lang=source_lang,
        target_lang=target_lang,
        input_dir=ROOT / env("INPUT_DIR", "input"),
        output_dir=ROOT / env("OUTPUT_DIR", "output"),
        work_dir=work_dir,
        glossary_path=ROOT / env("GLOSSARY_PATH", "glossary.csv"),
        tm_db_path=ROOT / env("TM_DB_PATH", str(work_dir / "tm.sqlite")),
        translation_mode=(args.translation_mode or env("TRANSLATION_MODE", "copy")).lower(),
        openai_api_key=env("OPENAI_API_KEY"),
        openai_model=env("OPENAI_MODEL", "gpt-4.1-mini"),
        azure_openai_api_key=env("AZURE_OPENAI_API_KEY"),
        azure_openai_endpoint=env("AZURE_OPENAI_ENDPOINT"),
        azure_openai_api_version=env("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
        azure_openai_deployment=env("AZURE_OPENAI_DEPLOYMENT"),
        ocr_mode=(args.ocr or env("OCR_MODE", "off")).lower(),
        azure_vision_endpoint=env("AZURE_VISION_ENDPOINT"),
        azure_vision_key=env("AZURE_VISION_KEY"),
        font_regular=env("FONT_REGULAR", "/mnt/c/Windows/Fonts/malgun.ttf"),
        font_bold=env("FONT_BOLD", "/mnt/c/Windows/Fonts/malgunbd.ttf"),
        font_fallback=env("FONT_FALLBACK", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        render_scale=float_value(env("RENDER_SCALE"), 1.5),
        render_diff_warn_mean=float_value(env("RENDER_DIFF_WARN_MEAN"), 20.0),
        render_diff_fail_mean=float_value(env("RENDER_DIFF_FAIL_MEAN"), 60.0),
        strict_tools=args.strict or bool_value(env("STRICT_TOOLS"), False),
        allow_degraded=(not args.strict) and bool_value(env("ALLOW_DEGRADED"), True),
        keep_work=args.keep_work or bool_value(env("KEEP_WORK"), True),
    )


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, value: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path, fallback: Any = None) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def command_path(name: str) -> str:
    return shutil.which(name) or ""


def ensure_system_site_packages() -> list[str]:
    version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    candidates = [
        Path("/usr/lib64") / version / "site-packages",
        Path("/usr/lib") / version / "site-packages",
    ]
    added = []
    for candidate in candidates:
        value = str(candidate)
        if candidate.exists() and value not in sys.path:
            sys.path.append(value)
            added.append(value)
    return added


def module_available(name: str) -> bool:
    if importlib.util.find_spec(name) is not None:
        return True
    if name in {"cairo", "gi"}:
        ensure_system_site_packages()
        return importlib.util.find_spec(name) is not None
    return False


def estimate_text_width(text: str, font_size: float) -> float:
    total = 0.0
    for character in text:
        if character.isspace():
            total += font_size * 0.33
        elif unicodedata.east_asian_width(character) in {"F", "W"}:
            total += font_size
        else:
            total += font_size * 0.58
    return total


def wrap_text_by_width(text: str, max_width: float, font_size: float) -> list[str]:
    if not text:
        return [""]
    lines: list[str] = []
    current = ""
    for token in re.findall(r"\S+\s*|\s+", text):
        candidate = current + token
        if current and estimate_text_width(candidate.rstrip(), font_size) > max_width:
            lines.append(current.rstrip())
            current = token.lstrip()
        else:
            current = candidate
        while current and estimate_text_width(current.rstrip(), font_size) > max_width and len(current) > 1:
            split_at = max(1, int(len(current) * max_width / max(estimate_text_width(current, font_size), 1.0)))
            lines.append(current[:split_at].rstrip())
            current = current[split_at:].lstrip()
    if current or not lines:
        lines.append(current.rstrip())
    return lines or [text]


def run_command(command: list[str], timeout: int = 120) -> dict[str, Any]:
    started = time.time()
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        return {
            "command": command,
            "exitCode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "durationMs": int((time.time() - started) * 1000),
        }
    except Exception as exc:
        return {
            "command": command,
            "exitCode": -1,
            "stdout": "",
            "stderr": str(exc),
            "durationMs": int((time.time() - started) * 1000),
        }


def safe_stem(path: Path) -> str:
    value = path.stem.strip() or "pdf"
    value = re.sub(r"[\\/:*?\"<>|\s]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:96] or "pdf"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def bbox_area(bbox: dict[str, Any] | None) -> float:
    if not bbox:
        return 0.0
    return max(0.0, float(bbox.get("width") or 0)) * max(0.0, float(bbox.get("height") or 0))


def bbox_overlap_ratio(left_bbox: dict[str, Any] | None, right_bbox: dict[str, Any] | None) -> float:
    if not left_bbox or not right_bbox:
        return 0.0
    left_left = float(left_bbox.get("left", left_bbox.get("x", 0)) or 0)
    left_top = float(left_bbox.get("top", left_bbox.get("y", 0)) or 0)
    left_right = float(left_bbox.get("right", left_left + float(left_bbox.get("width") or 0)) or 0)
    left_bottom = float(left_bbox.get("bottom", left_top + float(left_bbox.get("height") or 0)) or 0)
    right_left = float(right_bbox.get("left", right_bbox.get("x", 0)) or 0)
    right_top = float(right_bbox.get("top", right_bbox.get("y", 0)) or 0)
    right_right = float(right_bbox.get("right", right_left + float(right_bbox.get("width") or 0)) or 0)
    right_bottom = float(right_bbox.get("bottom", right_top + float(right_bbox.get("height") or 0)) or 0)
    overlap_width = max(0.0, min(left_right, right_right) - max(left_left, right_left))
    overlap_height = max(0.0, min(left_bottom, right_bottom) - max(left_top, right_top))
    overlap_area = overlap_width * overlap_height
    smallest_area = min(bbox_area(left_bbox), bbox_area(right_bbox))
    return overlap_area / smallest_area if smallest_area else 0.0


def bbox_union(items: list[dict[str, Any]]) -> dict[str, float]:
    left = min(float(item.get("left", item.get("x", 0)) or 0) for item in items)
    top = min(float(item.get("top", item.get("y", 0)) or 0) for item in items)
    right = max(float(item.get("right", float(item.get("x", 0) or 0) + float(item.get("width", 0) or 0)) or 0) for item in items)
    bottom = max(float(item.get("bottom", float(item.get("y", 0) or 0) + float(item.get("height", 0) or 0)) or 0) for item in items)
    return {"x": left, "y": top, "width": max(0.0, right - left), "height": max(0.0, bottom - top), "left": left, "top": top, "right": right, "bottom": bottom}


def join_pdf_text(left: str, right: str) -> str:
    if not left:
        return right
    if not right:
        return left
    if right[0] in ",.;:%)]}" or left[-1] in "([{/#$":
        return left + right
    if left[-1].isspace() or right[0].isspace():
        return left + right
    return left + " " + right


def is_translatable_text(value: str) -> bool:
    text = normalize_text(value)
    if len(text) < 3:
        return False
    letters = re.findall(r"[A-Za-z]", text)
    if len(letters) < 2:
        return False
    if re.fullmatch(r"[A-Z0-9_#./:,()\-\s]+", text) and len(text.split()) <= 3:
        return False
    return True


def tool_report() -> dict[str, Any]:
    commands = {
        "qpdf": "qpdf",
        "poppler_pdffonts": "pdffonts",
        "ghostscript": "gs",
        "java": "java",
        "node": "node",
        "sqlite3": "sqlite3",
    }
    modules = [
        "pikepdf",
        "pdfplumber",
        "reportlab",
        "pypdfium2",
        "fitz",
        "PIL",
        "numpy",
        "cv2",
        "openai",
        "uharfbuzz",
        "paddleocr",
        "cairo",
        "gi",
    ]
    command_results = {}
    for label, binary in commands.items():
        path = command_path(binary)
        command_results[label] = {"binary": binary, "path": path, "available": bool(path)}
    module_results = {name: {"available": module_available(name)} for name in modules}
    return {
        "recordedAt": now_iso(),
        "commands": command_results,
        "pythonModules": module_results,
    }


class Pipeline:
    def __init__(self, config: Config, source_pdf: Path):
        self.config = config
        self.source_pdf = source_pdf.resolve()
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.job_id = f"{safe_stem(source_pdf)}-{stamp}"
        self.job_dir = config.work_dir / self.job_id
        self.state_dir = self.job_dir / "state"
        self.pages_dir = self.job_dir / "pages"
        self.objects_dir = self.job_dir / "objects"
        self.layout_dir = self.job_dir / "layout"
        self.pdf_dir = self.job_dir / "pdf"
        self.reports_dir = self.job_dir / "reports"
        self.artifacts_path = self.state_dir / "artifacts.json"
        self.job_path = self.state_dir / "job.json"
        self._hb_font_cache: dict[str, tuple[Any, Any, int]] = {}

    def log(self, message: str) -> None:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

    def initialize_dirs(self) -> None:
        for path in [self.state_dir, self.pages_dir / "source", self.pages_dir / "output", self.objects_dir, self.layout_dir, self.pdf_dir, self.reports_dir]:
            ensure_dir(path)

    def artifacts(self) -> dict[str, str]:
        return read_json(self.artifacts_path, {}) or {}

    def set_artifact(self, key: str, path: Path) -> None:
        artifacts = self.artifacts()
        artifacts[key] = str(path.relative_to(self.job_dir) if path.is_relative_to(self.job_dir) else path)
        write_json(self.artifacts_path, artifacts)

    def update_job(self, **updates: Any) -> None:
        state = read_json(self.job_path, {}) or {}
        state.update(updates)
        state["updatedAt"] = now_iso()
        write_json(self.job_path, state)

    def write_error(self, step: str, message: str, recoverable: bool = False, severity: str = "fatal") -> None:
        write_json(self.state_dir / "error.json", {
            "step": step,
            "severity": severity,
            "message": message,
            "recoverable": recoverable,
            "recordedAt": now_iso(),
        })

    def warn_or_fail(self, step: str, message: str) -> dict[str, Any]:
        if self.config.strict_tools or not self.config.allow_degraded:
            raise StepError(step, message)
        return {"status": "degraded", "message": message, "recordedAt": now_iso()}

    def run(self) -> None:
        for step_name in STEP_ORDER:
            self.log(f"START {step_name}")
            self.update_job(status="running", currentStep=step_name)
            try:
                getattr(self, step_name)()
            except StepError as exc:
                self.write_error(exc.step, str(exc), recoverable=exc.recoverable)
                self.update_job(status="failed", failedStep=exc.step)
                raise
            except Exception as exc:
                self.write_error(step_name, str(exc), recoverable=False)
                self.update_job(status="failed", failedStep=step_name)
                raise
            self.log(f"DONE  {step_name}")
        self.update_job(status="completed", currentStep="completed", completedAt=now_iso())

    def step_report(self, name: str, value: dict[str, Any]) -> None:
        path = self.state_dir / f"{name}.json"
        write_json(path, value)
        self.set_artifact(name, path)

    def _pdf_page_sizes(self) -> list[dict[str, Any]]:
        text_layout = read_json(self.state_dir / "text-bbox.json", {}) or {}
        pages = text_layout.get("pages") or []
        if pages:
            return [{"page": page.get("page"), "width": page.get("width"), "height": page.get("height")} for page in pages]
        try:
            import fitz  # type: ignore
            with fitz.open(self.source_pdf) as document:
                return [
                    {"page": index + 1, "width": float(page.rect.width), "height": float(page.rect.height)}
                    for index, page in enumerate(document)
                ]
        except Exception:
            return [{"page": 1, "width": 612.0, "height": 792.0}]

    def _render_with_pymupdf(self, pdf_path: Path, output_dir: Path, label: str) -> dict[str, Any]:
        import fitz  # type: ignore
        ensure_dir(output_dir)
        pages = []
        with fitz.open(pdf_path) as document:
            for index, page in enumerate(document):
                image_path = output_dir / f"page-{index + 1:04d}.png"
                matrix = fitz.Matrix(self.config.render_scale, self.config.render_scale)
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                pixmap.save(image_path)
                pages.append({
                    "page": index + 1,
                    "image": str(image_path.relative_to(self.job_dir)),
                    "width": pixmap.width,
                    "height": pixmap.height,
                })
        return {"engine": "pymupdf", "label": label, "pages": pages}

    def _render_with_pdfium(self, pdf_path: Path, output_dir: Path, label: str) -> dict[str, Any]:
        import pypdfium2 as pdfium  # type: ignore
        ensure_dir(output_dir)
        pages = []
        document = pdfium.PdfDocument(str(pdf_path))
        for index in range(len(document)):
            page = document[index]
            bitmap = page.render(scale=self.config.render_scale)
            image = bitmap.to_pil()
            image_path = output_dir / f"page-{index + 1:04d}.png"
            image.save(image_path)
            pages.append({
                "page": index + 1,
                "image": str(image_path.relative_to(self.job_dir)),
                "width": image.width,
                "height": image.height,
            })
            page.close()
        document.close()
        return {"engine": "pdfium", "label": label, "pages": pages}

    def _extract_text_with_pymupdf(self) -> dict[str, Any]:
        import fitz  # type: ignore
        pages = []
        flags = fitz.TEXT_PRESERVE_LIGATURES | fitz.TEXT_PRESERVE_WHITESPACE
        with fitz.open(self.source_pdf) as document:
            for page_index, page in enumerate(document):
                page_data = page.get_text("dict", flags=flags)
                runs = []
                for block_index, block in enumerate(page_data.get("blocks", [])):
                    if block.get("type") != 0:
                        continue
                    for line_index, line in enumerate(block.get("lines", [])):
                        for span_index, span in enumerate(line.get("spans", [])):
                            text = str(span.get("text") or "")
                            if not text.strip():
                                continue
                            bbox = span.get("bbox") or [0, 0, 0, 0]
                            color_number = int(span.get("color") or 0)
                            runs.append({
                                "id": f"p{page_index + 1:04d}-r{len(runs):05d}",
                                "text": text,
                                "bbox": {
                                    "x": float(bbox[0]),
                                    "y": float(bbox[1]),
                                    "width": float(max(0, bbox[2] - bbox[0])),
                                    "height": float(max(0, bbox[3] - bbox[1])),
                                    "left": float(bbox[0]),
                                    "top": float(bbox[1]),
                                    "right": float(bbox[2]),
                                    "bottom": float(bbox[3]),
                                },
                                "style": {
                                    "fontSize": float(span.get("size") or 10),
                                    "font": span.get("font") or "",
                                    "color": [
                                        ((color_number >> 16) & 255) / 255,
                                        ((color_number >> 8) & 255) / 255,
                                        (color_number & 255) / 255,
                                    ],
                                },
                                "block": block_index,
                                "line": line_index,
                                "span": span_index,
                            })
                pages.append({
                    "page": page_index + 1,
                    "width": float(page.rect.width),
                    "height": float(page.rect.height),
                    "runs": runs,
                })
        return {"engine": "pymupdf-adapter", "pages": pages}

    def _extract_text_with_pdfium(self) -> dict[str, Any]:
        import pypdfium2 as pdfium  # type: ignore
        document = pdfium.PdfDocument(str(self.source_pdf))
        pages = []
        try:
            for page_index in range(len(document)):
                page = document[page_index]
                text_page = page.get_textpage()
                try:
                    page_width, page_height = page.get_size()
                    runs = []
                    for rect_index in range(text_page.count_rects()):
                        left, bottom, right, top = text_page.get_rect(rect_index)
                        text = text_page.get_text_bounded(left, bottom, right, top).replace("\r", "\n").strip()
                        if not text:
                            continue
                        bbox = {
                            "x": float(left),
                            "y": float(page_height - top),
                            "width": float(max(0.0, right - left)),
                            "height": float(max(0.0, top - bottom)),
                            "left": float(left),
                            "top": float(page_height - top),
                            "right": float(right),
                            "bottom": float(page_height - bottom),
                        }
                        runs.append({
                            "id": f"p{page_index + 1:04d}-r{len(runs):05d}",
                            "text": text,
                            "bbox": bbox,
                            "style": {
                                "fontSize": max(4.0, float(bbox["height"]) * 0.86),
                                "font": "",
                                "color": [0.0, 0.0, 0.0],
                            },
                            "block": rect_index,
                            "line": rect_index,
                            "span": 0,
                        })
                    pages.append({"page": page_index + 1, "width": float(page_width), "height": float(page_height), "runs": runs})
                finally:
                    text_page.close()
                    page.close()
        finally:
            document.close()
        style_report: dict[str, Any] = {"status": "unavailable"}
        if module_available("fitz"):
            try:
                style_source = self._extract_text_with_pymupdf()
                style_by_page = {int(page.get("page") or 1): page.get("runs") or [] for page in style_source.get("pages") or []}
                enriched = 0
                for page in pages:
                    candidates = style_by_page.get(int(page.get("page") or 1), [])
                    for run in page.get("runs") or []:
                        source_text = normalize_text(str(run.get("text") or ""))
                        source_bbox = run.get("bbox") or {}
                        best_candidate = None
                        best_score = None
                        for candidate in candidates:
                            candidate_text = normalize_text(str(candidate.get("text") or ""))
                            if source_text and candidate_text and source_text not in candidate_text and candidate_text not in source_text:
                                continue
                            candidate_bbox = candidate.get("bbox") or {}
                            score = abs(float(source_bbox.get("x") or 0) - float(candidate_bbox.get("x") or 0)) + abs(float(source_bbox.get("y") or 0) - float(candidate_bbox.get("y") or 0))
                            if best_score is None or score < best_score:
                                best_candidate = candidate
                                best_score = score
                        if best_candidate:
                            run["style"] = best_candidate.get("style") or run.get("style")
                            run["styleSource"] = "pymupdf"
                            enriched += 1
                style_report = {"status": "ok", "tool": "PyMuPDF", "enrichedRuns": enriched}
            except Exception as exc:
                style_report = {"status": "degraded", "tool": "PyMuPDF", "message": str(exc)}
        return {"engine": "pdfium", "status": "ok", "styleReport": style_report, "pages": pages}

    def _load_glossary(self) -> list[dict[str, str]]:
        if not self.config.glossary_path.exists():
            return []
        with self.config.glossary_path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]

    def _init_tm(self) -> None:
        ensure_dir(self.config.tm_db_path.parent)
        with sqlite3.connect(self.config.tm_db_path) as database:
            database.execute(
                "CREATE TABLE IF NOT EXISTS tm (src_hash TEXT PRIMARY KEY, src TEXT NOT NULL, tgt TEXT NOT NULL, model TEXT, source_lang TEXT, target_lang TEXT, created_at TEXT NOT NULL)"
            )
            database.commit()

    def _tm_get(self, source: str) -> str | None:
        key = sha256_text(f"{self.config.source_lang}\n{self.config.target_lang}\n{source}")
        with sqlite3.connect(self.config.tm_db_path) as database:
            row = database.execute("SELECT tgt FROM tm WHERE src_hash = ?", (key,)).fetchone()
        return row[0] if row else None

    def _tm_put(self, source: str, target: str, model: str) -> None:
        key = sha256_text(f"{self.config.source_lang}\n{self.config.target_lang}\n{source}")
        with sqlite3.connect(self.config.tm_db_path) as database:
            database.execute(
                "INSERT OR REPLACE INTO tm (src_hash, src, tgt, model, source_lang, target_lang, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (key, source, target, model, self.config.source_lang, self.config.target_lang, now_iso()),
            )
            database.commit()

    def _tm_key(self, source: str) -> str:
        return sha256_text(f"{self.config.source_lang}\n{self.config.target_lang}\n{source}")

    def _tm_get_many(self, sources: list[str]) -> dict[str, str]:
        if not sources:
            return {}
        key_to_source = {self._tm_key(source): source for source in sources}
        hits: dict[str, str] = {}
        with sqlite3.connect(self.config.tm_db_path) as database:
            for key, target in database.execute("SELECT src_hash, tgt FROM tm"):
                source = key_to_source.get(key)
                if source is not None:
                    hits[source] = target
        return hits

    def _tm_put_many(self, rows: list[tuple[str, str, str]]) -> None:
        if not rows:
            return
        with sqlite3.connect(self.config.tm_db_path) as database:
            database.executemany(
                "INSERT OR REPLACE INTO tm (src_hash, src, tgt, model, source_lang, target_lang, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [(self._tm_key(source), source, target, model, self.config.source_lang, self.config.target_lang, now_iso()) for source, target, model in rows],
            )
            database.commit()

    def _parse_llm_json_object(self, content: str) -> dict[str, str]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        parsed = json.loads(cleaned or "{}")
        if not isinstance(parsed, dict):
            raise ValueError("translation response must be a JSON object")
        return {str(key): str(value) for key, value in parsed.items()}

    def _translation_messages(self, items: list[dict[str, Any]]) -> list[dict[str, str]]:
        payload = [{"id": item["id"], "text": item["source"]} for item in items]
        glossary = self._load_glossary()
        glossary_text = "\n".join(
            f"- {row.get('term', '')} => {row.get('translation', '')} protected={row.get('protected', '')}"
            for row in glossary
            if row.get("term")
        ) or "(none)"
        return [
            {
                "role": "system",
                "content": f"Translate from {self.config.source_lang} to {self.config.target_lang}. Return only a JSON object mapping id to translated text. Preserve protected glossary terms exactly. Glossary:\n{glossary_text}",
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]

    def _translate_openai_batch(self, items: list[dict[str, Any]]) -> dict[str, str]:
        from openai import OpenAI  # type: ignore
        client = OpenAI(api_key=self.config.openai_api_key, timeout=45.0, max_retries=0)
        response = client.chat.completions.create(
            model=self.config.openai_model,
            temperature=0,
            messages=self._translation_messages(items),
        )
        content = response.choices[0].message.content or "{}"
        return self._parse_llm_json_object(content)

    def _translate_azure_openai_batch(self, items: list[dict[str, Any]]) -> dict[str, str]:
        from openai import AzureOpenAI  # type: ignore
        client = AzureOpenAI(
            api_key=self.config.azure_openai_api_key,
            azure_endpoint=self.config.azure_openai_endpoint,
            api_version=self.config.azure_openai_api_version,
            timeout=45.0,
            max_retries=0,
        )
        response = client.chat.completions.create(
            model=self.config.azure_openai_deployment,
            temperature=0,
            messages=self._translation_messages(items),
        )
        content = response.choices[0].message.content or "{}"
        return self._parse_llm_json_object(content)

    def _merge_text_runs(self, runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        sorted_runs = sorted((run for run in runs if normalize_text(str(run.get("text") or ""))), key=lambda run: (float((run.get("bbox") or {}).get("top") or 0), float((run.get("bbox") or {}).get("left") or 0)))
        lines: list[list[dict[str, Any]]] = []
        for run in sorted_runs:
            bbox = run.get("bbox") or {}
            top = float(bbox.get("top", bbox.get("y", 0)) or 0)
            height = max(1.0, float(bbox.get("height") or 1))
            placed = False
            for line in lines:
                line_bbox = bbox_union([item.get("bbox") or {} for item in line])
                line_top = float(line_bbox.get("top") or 0)
                line_height = max(1.0, float(line_bbox.get("height") or height))
                if abs(top - line_top) <= max(2.0, min(height, line_height) * 0.75):
                    line.append(run)
                    placed = True
                    break
            if not placed:
                lines.append([run])

        merged = []
        for line_index, line in enumerate(lines):
            ordered = sorted(line, key=lambda run: float((run.get("bbox") or {}).get("left", (run.get("bbox") or {}).get("x", 0)) or 0))
            current: list[dict[str, Any]] = []
            current_text = ""
            for run in ordered:
                bbox = run.get("bbox") or {}
                if not current:
                    current = [run]
                    current_text = str(run.get("text") or "").strip()
                    continue
                previous_bbox = current[-1].get("bbox") or {}
                previous_right = float(previous_bbox.get("right", float(previous_bbox.get("x", 0) or 0) + float(previous_bbox.get("width", 0) or 0)) or 0)
                gap = float(bbox.get("left", bbox.get("x", 0)) or 0) - previous_right
                font_size = max(6.0, float((run.get("style") or {}).get("fontSize") or bbox.get("height") or 10))
                if gap <= max(18.0, font_size * 2.4):
                    current.append(run)
                    current_text = join_pdf_text(current_text, str(run.get("text") or "").strip())
                else:
                    merged.append(self._merged_text_run(current, current_text, line_index))
                    current = [run]
                    current_text = str(run.get("text") or "").strip()
            if current:
                merged.append(self._merged_text_run(current, current_text, line_index))
        return merged

    def _merged_text_run(self, runs: list[dict[str, Any]], text: str, line_index: int) -> dict[str, Any]:
        bbox = bbox_union([run.get("bbox") or {} for run in runs])
        first = runs[0]
        style = dict(first.get("style") or {})
        style["fontSize"] = max(float((run.get("style") or {}).get("fontSize") or 0) for run in runs) or style.get("fontSize") or 10
        return {"id": first.get("id"), "text": normalize_text(text), "bbox": bbox, "style": style, "line": line_index, "sourceRunCount": len(runs)}

    def _page_image_records(self) -> list[dict[str, Any]]:
        render = read_json(self.state_dir / "render-source.json", {}) or {}
        page_sizes = {int(item["page"]): item for item in self._pdf_page_sizes() if item.get("page")}
        records = []
        for page in render.get("pages") or []:
            page_number = int(page.get("page") or 1)
            page_info = page_sizes.get(page_number, {"width": 612.0, "height": 792.0})
            image_path = self.job_dir / str(page.get("image") or "")
            pixel_width = float(page.get("width") or 0)
            pixel_height = float(page.get("height") or 0)
            page_width = float(page_info.get("width") or 612.0)
            page_height = float(page_info.get("height") or 792.0)
            scale_x = pixel_width / page_width if page_width else self.config.render_scale
            scale_y = pixel_height / page_height if page_height else self.config.render_scale
            records.append({
                "page": page_number,
                "imagePath": image_path,
                "pageWidth": page_width,
                "pageHeight": page_height,
                "scaleX": scale_x or self.config.render_scale,
                "scaleY": scale_y or self.config.render_scale,
            })
        return records

    def _polygon_to_bbox(self, points: Any, scale_x: float, scale_y: float) -> dict[str, float]:
        normalized = []
        if isinstance(points, list):
            for point in points:
                if isinstance(point, dict):
                    normalized.append((float(point.get("x") or 0), float(point.get("y") or 0)))
                elif isinstance(point, (list, tuple)) and len(point) >= 2:
                    normalized.append((float(point[0] or 0), float(point[1] or 0)))
        if not normalized:
            return {"x": 0.0, "y": 0.0, "width": 0.0, "height": 0.0, "left": 0.0, "top": 0.0, "right": 0.0, "bottom": 0.0}
        xs = [point[0] / scale_x for point in normalized]
        ys = [point[1] / scale_y for point in normalized]
        left = min(xs)
        top = min(ys)
        right = max(xs)
        bottom = max(ys)
        return {"x": left, "y": top, "width": max(0.0, right - left), "height": max(0.0, bottom - top), "left": left, "top": top, "right": right, "bottom": bottom}

    def _extract_ocr_with_paddleocr(self) -> dict[str, Any]:
        from paddleocr import PaddleOCR  # type: ignore
        language = "korean" if self.config.source_lang.lower() in {"ko", "kr", "korean"} else "en"
        ocr = PaddleOCR(use_angle_cls=True, lang=language, show_log=False)
        items = []
        for page in self._page_image_records():
            if not page["imagePath"].exists():
                continue
            result = ocr.ocr(str(page["imagePath"]), cls=True) or []
            lines = result[0] if result and isinstance(result[0], list) else result
            for line_index, line in enumerate(lines or []):
                if not isinstance(line, (list, tuple)) or len(line) < 2:
                    continue
                box, text_info = line[0], line[1]
                text = str(text_info[0] if isinstance(text_info, (list, tuple)) and text_info else "")
                score = float(text_info[1]) if isinstance(text_info, (list, tuple)) and len(text_info) > 1 else None
                if not text.strip():
                    continue
                items.append({
                    "id": f"p{page['page']:04d}-ocr{line_index:05d}",
                    "page": page["page"],
                    "pageWidth": page["pageWidth"],
                    "pageHeight": page["pageHeight"],
                    "text": text,
                    "bbox": self._polygon_to_bbox(box, page["scaleX"], page["scaleY"]),
                    "score": score,
                    "origin": "ocr-image",
                })
        return {"tool": "PaddleOCR", "status": "ok", "items": items, "total": len(items), "recordedAt": now_iso()}

    def _extract_ocr_with_azure_vision(self) -> dict[str, Any]:
        endpoint = self.config.azure_vision_endpoint.rstrip("/")
        query = urllib.parse.urlencode({"api-version": "2024-02-01", "features": "read"})
        url = f"{endpoint}/computervision/imageanalysis:analyze?{query}"
        headers = {"Ocp-Apim-Subscription-Key": self.config.azure_vision_key, "Content-Type": "image/png"}
        items = []
        for page in self._page_image_records():
            if not page["imagePath"].exists():
                continue
            request = urllib.request.Request(url, data=page["imagePath"].read_bytes(), headers=headers, method="POST")
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read().decode("utf-8"))
            read_result = payload.get("readResult") or {}
            line_index = 0
            for block in read_result.get("blocks") or []:
                for line in block.get("lines") or []:
                    text = str(line.get("text") or "")
                    if not text.strip():
                        continue
                    points = line.get("boundingPolygon") or line.get("boundingBox") or []
                    items.append({
                        "id": f"p{page['page']:04d}-ocr{line_index:05d}",
                        "page": page["page"],
                        "pageWidth": page["pageWidth"],
                        "pageHeight": page["pageHeight"],
                        "text": text,
                        "bbox": self._polygon_to_bbox(points, page["scaleX"], page["scaleY"]),
                        "origin": "ocr-image",
                    })
                    line_index += 1
        return {"tool": "Azure AI Vision", "status": "ok", "items": items, "total": len(items), "recordedAt": now_iso()}

    def _restore_pdf_objects_with_pikepdf(self, draft: Path, enriched: Path) -> dict[str, Any]:
        import pikepdf  # type: ignore
        restored = {"docInfo": 0, "rootEntries": [], "pageAnnotations": 0}
        with pikepdf.open(self.source_pdf) as source_pdf, pikepdf.open(draft) as output_pdf:
            for key, value in source_pdf.docinfo.items():
                output_pdf.docinfo[key] = value
                restored["docInfo"] += 1
            for key in ["/Lang", "/MarkInfo", "/ViewerPreferences", "/PageLabels"]:
                if key in source_pdf.Root:
                    output_pdf.Root[key] = output_pdf.copy_foreign(source_pdf.Root[key])
                    restored["rootEntries"].append(key)
            page_count = min(len(source_pdf.pages), len(output_pdf.pages))
            for index in range(page_count):
                source_page = source_pdf.pages[index]
                output_page = output_pdf.pages[index]
                if "/Annots" in source_page.obj:
                    output_page.obj["/Annots"] = output_pdf.copy_foreign(source_page.obj["/Annots"])
                    try:
                        restored["pageAnnotations"] += len(source_page.obj["/Annots"])
                    except Exception:
                        restored["pageAnnotations"] += 1
            output_pdf.save(enriched)
        return {"status": "ok", "tool": "pikepdf", "restored": restored, "output": str(enriched.relative_to(self.job_dir))}

    def _select_font_path(self, style: dict[str, Any] | None = None) -> str:
        style_font = str((style or {}).get("font") or "").lower()
        candidates = []
        if "bold" in style_font:
            candidates.append(self.config.font_bold)
        candidates.extend([self.config.font_regular, self.config.font_fallback, self.config.font_bold])
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return candidate
        return ""

    def _shape_text_with_harfbuzz(self, text: str, font_path: str, font_size: float) -> list[dict[str, Any]]:
        import uharfbuzz as hb  # type: ignore
        if font_path not in self._hb_font_cache:
            font_data = Path(font_path).read_bytes()
            face = hb.Face(font_data)
            font = hb.Font(face)
            upem = face.upem or 1000
            font.scale = (upem, upem)
            self._hb_font_cache[font_path] = (face, font, upem)
        _, font, upem = self._hb_font_cache[font_path]
        shaped_lines = []
        for line_index, line_text in enumerate(text.splitlines() or [text]):
            buffer = hb.Buffer()
            buffer.add_str(line_text)
            buffer.guess_segment_properties()
            hb.shape(font, buffer, {})
            glyphs = []
            cursor_x = 0.0
            cursor_y = 0.0
            for info, position in zip(buffer.glyph_infos, buffer.glyph_positions):
                x_advance = float(position.x_advance) / upem * font_size
                y_advance = float(position.y_advance) / upem * font_size
                glyphs.append({
                    "glyphId": int(info.codepoint),
                    "cluster": int(info.cluster),
                    "xAdvance": x_advance,
                    "yAdvance": y_advance,
                    "xOffset": float(position.x_offset) / upem * font_size,
                    "yOffset": float(position.y_offset) / upem * font_size,
                    "x": cursor_x,
                    "y": cursor_y,
                })
                cursor_x += x_advance
                cursor_y += y_advance
            shaped_lines.append({"line": line_index, "text": line_text, "glyphs": glyphs, "advanceWidth": cursor_x})
        return shaped_lines

    def _make_output_path(self) -> Path:
        suffix = self.config.target_lang.upper()
        return self.config.output_dir / f"{safe_stem(self.source_pdf)}_{suffix}.pdf"

    def _copy_file(self, source: Path, target: Path) -> None:
        ensure_dir(target.parent)
        shutil.copyfile(source, target)

    def _source_page_backgrounds(self) -> dict[int, dict[str, Any]]:
        return {int(record["page"]): record for record in self._page_image_records() if record.get("imagePath") and Path(record["imagePath"]).exists()}

    def _text_rect(self, bbox: dict[str, Any]) -> tuple[float, float, float, float]:
        x = float(bbox.get("x", bbox.get("left", 0)) or 0)
        y = float(bbox.get("y", bbox.get("top", 0)) or 0)
        width = max(1.0, float(bbox.get("width", float(bbox.get("right", x) or x) - x) or 1))
        height = max(1.0, float(bbox.get("height", float(bbox.get("bottom", y) or y) - y) or 1))
        return x, y, width, height

    def _cover_source_text_cairo(self, context: Any, items: list[dict[str, Any]]) -> None:
        context.save()
        context.set_source_rgb(1, 1, 1)
        for item in items:
            x, y, width, height = self._text_rect(item.get("bbox") or {})
            context.rectangle(x, y, width, height)
            context.fill()
        context.restore()

    def _draw_cairo_page_background(self, context: Any, cairo: Any, background: dict[str, Any] | None, page_width: float, page_height: float) -> bool:
        if not background:
            return False
        image_path = Path(background.get("imagePath") or "")
        if not image_path.exists():
            return False
        image = cairo.ImageSurface.create_from_png(str(image_path))
        context.save()
        context.scale(page_width / max(1, image.get_width()), page_height / max(1, image.get_height()))
        context.set_source_surface(image, 0, 0)
        context.paint()
        context.restore()
        return True

    def _build_pdf_with_reportlab(self, target: Path) -> dict[str, Any]:
        from reportlab.pdfbase import pdfmetrics  # type: ignore
        from reportlab.pdfbase.ttfonts import TTFont  # type: ignore
        from reportlab.pdfgen import canvas  # type: ignore

        layout = read_json(self.state_dir / "positioned-layout.json", {}) or {}
        pages = layout.get("pages") or []
        if not pages:
            pages = [{"page": item["page"], "width": item["width"], "height": item["height"], "items": []} for item in self._pdf_page_sizes()]

        font_name = "V5Regular"
        if self.config.font_regular and Path(self.config.font_regular).exists():
            pdfmetrics.registerFont(TTFont(font_name, self.config.font_regular))
        else:
            font_name = "Helvetica"

        backgrounds = self._source_page_backgrounds()
        ensure_dir(target.parent)
        first_page = pages[0]
        pdf_canvas = canvas.Canvas(str(target), pagesize=(float(first_page.get("width") or 612), float(first_page.get("height") or 792)))
        for page_index, page in enumerate(pages):
            page_width = float(page.get("width") or 612)
            page_height = float(page.get("height") or 792)
            if page_index > 0:
                pdf_canvas.setPageSize((page_width, page_height))
            background = backgrounds.get(int(page.get("page") or page_index + 1))
            if background:
                pdf_canvas.drawImage(str(background["imagePath"]), 0, 0, width=page_width, height=page_height, preserveAspectRatio=False, mask="auto")
            else:
                pdf_canvas.setFillColorRGB(1, 1, 1)
                pdf_canvas.rect(0, 0, page_width, page_height, fill=1, stroke=0)
            pdf_canvas.setFillColorRGB(1, 1, 1)
            for item in page.get("items") or []:
                x, y_top, width, height = self._text_rect(item.get("bbox") or {})
                pdf_canvas.rect(x, page_height - y_top - height, width, height, fill=1, stroke=0)
            for item in page.get("items") or []:
                bbox = item.get("bbox") or {}
                style = item.get("style") or {}
                text = str(item.get("text") or "")
                font_size = max(4.0, float(style.get("fontSize") or 10))
                x, y_top, width, height = self._text_rect(bbox)
                y = page_height - y_top - font_size
                pdf_canvas.saveState()
                clip_path = pdf_canvas.beginPath()
                clip_path.rect(x, page_height - y_top - height, width, height)
                pdf_canvas.clipPath(clip_path, stroke=0, fill=0)
                pdf_canvas.setFont(font_name, font_size)
                color = style.get("color") or [0, 0, 0]
                try:
                    pdf_canvas.setFillColorRGB(float(color[0]), float(color[1]), float(color[2]))
                except Exception:
                    pdf_canvas.setFillColorRGB(0, 0, 0)
                for line_index, line in enumerate(text.splitlines() or [text]):
                    pdf_canvas.drawString(x, y - line_index * font_size * 1.2, line)
                pdf_canvas.restoreState()
            pdf_canvas.showPage()
        pdf_canvas.save()
        return {"engine": "reportlab", "background": "rendered-source-pages", "sourceTextErasure": "bbox-whiteout", "output": str(target.relative_to(self.job_dir))}

    def _load_pango_cairo(self) -> tuple[Any, Any, Any]:
        ensure_system_site_packages()
        import cairo  # type: ignore
        import gi  # type: ignore

        gi.require_version("Pango", "1.0")
        gi.require_version("PangoCairo", "1.0")
        from gi.repository import Pango, PangoCairo  # type: ignore

        return cairo, Pango, PangoCairo

    def _pango_font_description(self, Pango: Any, style: dict[str, Any], font_size: float) -> Any:
        source_font = str(style.get("font") or "")
        family = "Noto Sans CJK KR"
        if source_font and source_font.lower() not in {"helvetica", "times", "courier"}:
            family = source_font
        description = Pango.FontDescription(family)
        description.set_size(int(font_size * Pango.SCALE))
        if "bold" in source_font.lower():
            description.set_weight(Pango.Weight.BOLD)
        return description

    def _layout_with_pango(self, text: str, bbox: dict[str, Any], style: dict[str, Any], page_height: float, modules: tuple[Any, Any, Any]) -> dict[str, Any]:
        cairo, Pango, PangoCairo = modules
        base_font_size = max(4.0, float(style.get("fontSize") or 10))
        width = max(12.0, float(bbox.get("width") or 160))
        original_height = max(4.0, float(bbox.get("height") or base_font_size * 1.25))
        y = max(0.0, float(bbox.get("y", bbox.get("top", 0)) or 0))
        max_height = max(4.0, min(original_height, page_height - y))
        best: tuple[float, Any, int, int] | None = None
        font_size = base_font_size
        while font_size >= 4.0:
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, max(1, int(width) + 8), max(1, int(max_height) + 32))
            context = cairo.Context(surface)
            layout = PangoCairo.create_layout(context)
            layout.set_font_description(self._pango_font_description(Pango, style, font_size))
            layout.set_width(int(width * Pango.SCALE))
            layout.set_wrap(Pango.WrapMode.WORD_CHAR)
            layout.set_spacing(int(font_size * 0.08 * Pango.SCALE))
            layout.set_text(text, -1)
            pixel_width, pixel_height = layout.get_pixel_size()
            best = (font_size, layout, pixel_width, pixel_height)
            if pixel_height <= max_height + 0.5:
                break
            font_size -= 0.5
        assert best is not None
        font_size, layout, pixel_width, pixel_height = best
        encoded = text.encode("utf-8")
        lines = []
        for line_index in range(layout.get_line_count()):
            line = layout.get_line_readonly(line_index)
            line_text = encoded[line.start_index:line.start_index + line.length].decode("utf-8", "ignore").rstrip()
            _ink, logical = line.get_pixel_extents()
            lines.append({"line": line_index, "text": line_text, "x": float(logical.x), "y": float(logical.y), "width": float(logical.width), "height": float(logical.height)})
        laid_out_bbox = dict(bbox)
        laid_out_bbox["height"] = max_height
        laid_out_bbox["bottom"] = y + max_height
        laid_out_bbox["right"] = float(bbox.get("x", bbox.get("left", 0)) or 0) + width
        return {
            "text": "\n".join(line["text"] for line in lines),
            "bbox": laid_out_bbox,
            "fontSize": font_size,
            "layoutEngine": "pango",
            "lineMetrics": lines,
            "measuredWidth": float(pixel_width),
            "measuredHeight": float(pixel_height),
            "overflow": bool(pixel_height > max_height + 0.5),
        }

    def _layout_with_custom_wrapper(self, text: str, bbox: dict[str, Any], style: dict[str, Any], page_height: float) -> dict[str, Any]:
        font_size = max(4.0, float(style.get("fontSize") or 10))
        width = max(12.0, float(bbox.get("width") or 160))
        y = max(0.0, float(bbox.get("y", bbox.get("top", 0)) or 0))
        max_height = max(4.0, min(max(4.0, float(bbox.get("height") or font_size * 1.25)), page_height - y))
        wrapped_lines = wrap_text_by_width(text, width, font_size)
        measured_height = len(wrapped_lines) * font_size * 1.2
        while font_size > 4.0 and measured_height > max_height + 0.5:
            font_size -= 0.5
            wrapped_lines = wrap_text_by_width(text, width, font_size)
            measured_height = len(wrapped_lines) * font_size * 1.2
        laid_out_bbox = dict(bbox)
        laid_out_bbox["height"] = max_height
        laid_out_bbox["bottom"] = y + max_height
        laid_out_bbox["right"] = float(bbox.get("x", bbox.get("left", 0)) or 0) + width
        return {
            "text": "\n".join(wrapped_lines),
            "bbox": laid_out_bbox,
            "fontSize": font_size,
            "layoutEngine": "custom-width-wrapper",
            "lineMetrics": [
                {"line": index, "text": line, "x": 0.0, "y": index * font_size * 1.2, "width": estimate_text_width(line, font_size), "height": font_size * 1.2}
                for index, line in enumerate(wrapped_lines)
            ],
            "measuredWidth": max((estimate_text_width(line, font_size) for line in wrapped_lines), default=0.0),
            "measuredHeight": measured_height,
            "overflow": bool(measured_height > max_height + 0.5),
        }

    def _build_pdf_with_cairo(self, target: Path) -> dict[str, Any]:
        cairo, Pango, PangoCairo = self._load_pango_cairo()
        layout_state = read_json(self.state_dir / "positioned-layout.json", {}) or {}
        pages = layout_state.get("pages") or []
        if not pages:
            pages = [{"page": item["page"], "width": item["width"], "height": item["height"], "items": []} for item in self._pdf_page_sizes()]
        ensure_dir(target.parent)
        first_page = pages[0]
        backgrounds = self._source_page_backgrounds()
        surface = cairo.PDFSurface(str(target), float(first_page.get("width") or 612), float(first_page.get("height") or 792))
        context = cairo.Context(surface)
        for page_index, page in enumerate(pages):
            page_width = float(page.get("width") or 612)
            page_height = float(page.get("height") or 792)
            if page_index > 0:
                surface.set_size(page_width, page_height)
            if not self._draw_cairo_page_background(context, cairo, backgrounds.get(int(page.get("page") or page_index + 1)), page_width, page_height):
                context.save()
                context.set_source_rgb(1, 1, 1)
                context.paint()
                context.restore()
            self._cover_source_text_cairo(context, page.get("items") or [])
            for item in page.get("items") or []:
                bbox = item.get("bbox") or {}
                style = item.get("style") or {}
                color = style.get("color") or [0, 0, 0]
                font_size = max(4.0, float(style.get("fontSize") or 10))
                x, y, width, height = self._text_rect(bbox)
                context.save()
                context.rectangle(x, y, width, height)
                context.clip()
                try:
                    context.set_source_rgb(float(color[0]), float(color[1]), float(color[2]))
                except Exception:
                    context.set_source_rgb(0, 0, 0)
                context.move_to(x, y)
                pango_layout = PangoCairo.create_layout(context)
                pango_layout.set_font_description(self._pango_font_description(Pango, style, font_size))
                pango_layout.set_width(int(width * Pango.SCALE))
                pango_layout.set_wrap(Pango.WrapMode.WORD_CHAR)
                pango_layout.set_spacing(int(font_size * 0.08 * Pango.SCALE))
                pango_layout.set_text(str(item.get("text") or ""), -1)
                PangoCairo.show_layout(context, pango_layout)
                context.restore()
            context.show_page()
        surface.finish()
        return {"engine": "cairo", "textLayout": "Pango", "background": "rendered-source-pages", "sourceTextErasure": "bbox-whiteout", "output": str(target.relative_to(self.job_dir))}

    def _build_pdf_with_pymupdf(self, target: Path) -> dict[str, Any]:
        import fitz  # type: ignore
        layout = read_json(self.state_dir / "positioned-layout.json", {}) or {}
        page_defs = layout.get("pages") or [{"page": item["page"], "width": item["width"], "height": item["height"], "items": []} for item in self._pdf_page_sizes()]
        document = fitz.open()
        font_args: dict[str, Any] = {}
        font_name = "helv"
        if self.config.font_regular and Path(self.config.font_regular).exists():
            font_args["fontfile"] = self.config.font_regular
            font_name = "V5Regular"
        backgrounds = self._source_page_backgrounds()
        for page_def in page_defs:
            page_width = float(page_def.get("width") or 612)
            page_height = float(page_def.get("height") or 792)
            page = document.new_page(width=page_width, height=page_height)
            background = backgrounds.get(int(page_def.get("page") or len(document)))
            if background:
                page.insert_image(fitz.Rect(0, 0, page_width, page_height), filename=str(background["imagePath"]))
            for item in page_def.get("items") or []:
                bbox = item.get("bbox") or {}
                x, y, width, height = self._text_rect(bbox)
                page.draw_rect(fitz.Rect(x, y, x + width, y + height), color=None, fill=(1, 1, 1), overlay=True)
            for item in page_def.get("items") or []:
                bbox = item.get("bbox") or {}
                style = item.get("style") or {}
                color = style.get("color") or [0, 0, 0]
                x, y, width, height = self._text_rect(bbox)
                rect = fitz.Rect(
                    x,
                    y,
                    x + max(24.0, width),
                    y + max(10.0, height),
                )
                page.insert_textbox(
                    rect,
                    str(item.get("text") or ""),
                    fontsize=max(4.0, float(style.get("fontSize") or 10)),
                    fontname=font_name,
                    color=tuple(float(value) for value in color[:3]),
                    **font_args,
                )
        ensure_dir(target.parent)
        subset = getattr(document, "subset_fonts", None)
        if callable(subset):
            try:
                subset()
            except Exception:
                pass
        document.save(target, garbage=4, deflate=True, clean=True)
        document.close()
        return {"engine": "pymupdf-degraded", "background": "rendered-source-pages", "sourceTextErasure": "bbox-whiteout", "output": str(target.relative_to(self.job_dir))}

    def _render_pdf(self, pdf_path: Path, output_dir: Path, label: str) -> dict[str, Any]:
        if module_available("pypdfium2"):
            return self._render_with_pdfium(pdf_path, output_dir, label)
        if module_available("fitz") and self.config.allow_degraded:
            return self._render_with_pymupdf(pdf_path, output_dir, label)
        raise StepError("render", "PDFium is unavailable and PyMuPDF degraded rendering is disabled")

    def step_01_init_job(self) -> None:
        self.initialize_dirs()
        write_json(self.job_path, {
            "jobId": self.job_id,
            "sourcePdf": str(self.source_pdf),
            "sourceLang": self.config.source_lang,
            "targetLang": self.config.target_lang,
            "status": "created",
            "currentStep": "01_init_job",
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
        })
        write_json(self.artifacts_path, {"sourcePdf": str(self.source_pdf)})
        self.step_report("init", {"status": "ok", "jobDir": str(self.job_dir), "recordedAt": now_iso()})

    def step_02_validate_source_pdf(self) -> None:
        report: dict[str, Any]
        if command_path("qpdf"):
            result = run_command(["qpdf", "--check", str(self.source_pdf)], timeout=120)
            report = {"tool": "qpdf", "status": "ok" if result["exitCode"] == 0 else "failed", "result": result}
            if result["exitCode"] != 0:
                write_json(self.state_dir / "validation.json", report)
                raise StepError("02_validate_source_pdf", "QPDF validation failed")
        elif module_available("pikepdf") and self.config.allow_degraded:
            import pikepdf  # type: ignore
            with pikepdf.open(self.source_pdf) as document:
                report = {"tool": "pikepdf-degraded", "status": "degraded", "pageCount": len(document.pages), "objectCount": len(document.objects)}
        elif module_available("fitz") and self.config.allow_degraded:
            import fitz  # type: ignore
            with fitz.open(self.source_pdf) as document:
                report = {"tool": "pymupdf-degraded", "status": "degraded", "pageCount": document.page_count}
        else:
            raise StepError("02_validate_source_pdf", "QPDF is not installed")
        path = self.state_dir / "validation.json"
        write_json(path, report)
        self.set_artifact("validation", path)

    def step_03_extract_object_manifest(self) -> None:
        if module_available("pikepdf"):
            import pikepdf  # type: ignore
            with pikepdf.open(self.source_pdf) as pdf:
                manifest = {
                    "tool": "pikepdf",
                    "status": "ok",
                    "pageCount": len(pdf.pages),
                    "objectCount": len(pdf.objects),
                    "docInfo": {str(key): str(value) for key, value in dict(pdf.docinfo).items()},
                    "images": [],
                    "annotations": [],
                    "links": [],
                    "outlines": [],
                    "recordedAt": now_iso(),
                }
        elif module_available("fitz") and self.config.allow_degraded:
            import fitz  # type: ignore
            images = []
            with fitz.open(self.source_pdf) as document:
                for page_index, page in enumerate(document):
                    for image_index, image in enumerate(page.get_images(full=True)):
                        images.append({"page": page_index + 1, "index": image_index, "xref": image[0], "width": image[2], "height": image[3]})
                manifest = {"tool": "pymupdf-degraded", "status": "degraded", "pageCount": document.page_count, "images": images, "recordedAt": now_iso()}
        else:
            manifest = self.warn_or_fail("03_extract_object_manifest", "pikepdf is not installed")
        path = self.state_dir / "object-manifest.json"
        write_json(path, manifest)
        self.set_artifact("objectManifest", path)

    def step_04_render_source_pages(self) -> None:
        report = self._render_pdf(self.source_pdf, self.pages_dir / "source", "source")
        path = self.state_dir / "render-source.json"
        write_json(path, report)
        self.set_artifact("renderSource", path)

    def step_05_extract_text_bbox(self) -> None:
        if module_available("pypdfium2"):
            report = self._extract_text_with_pdfium()
        elif module_available("fitz") and self.config.allow_degraded:
            report = self._extract_text_with_pymupdf()
            report["preferredEngine"] = "PDFium"
            report["status"] = "degraded"
            report["note"] = "PDFium is the target bbox engine; PyMuPDF adapter was used because PDFium is unavailable."
        else:
            raise StepError("05_extract_text_bbox", "Text bbox extraction requires PDFium or PyMuPDF degraded adapter")
        path = self.state_dir / "text-bbox.json"
        write_json(path, report)
        self.set_artifact("textBbox", path)

    def step_06_analyze_fonts(self) -> None:
        if command_path("pdffonts"):
            result = run_command(["pdffonts", str(self.source_pdf)], timeout=120)
            report = {"tool": "poppler-pdffonts", "status": "ok" if result["exitCode"] == 0 else "failed", "result": result}
        else:
            report = self.warn_or_fail("06_analyze_fonts", "Poppler pdffonts is not installed")
        path = self.state_dir / "font-report.json"
        write_json(path, report)
        self.set_artifact("fontReport", path)

    def step_07_detect_tables(self) -> None:
        if module_available("pdfplumber"):
            import pdfplumber  # type: ignore
            tables = []
            with pdfplumber.open(str(self.source_pdf)) as pdf:
                for page_index, page in enumerate(pdf.pages):
                    try:
                        found_tables = page.find_tables()
                    except Exception:
                        found_tables = []
                    for table_index, table in enumerate(found_tables):
                        tables.append({"page": page_index + 1, "table": table_index, "bbox": list(table.bbox), "cellCount": len(table.cells or [])})
            report = {"tool": "pdfplumber", "status": "ok", "tables": tables, "recordedAt": now_iso()}
        else:
            report = self.warn_or_fail("07_detect_tables", "pdfplumber is not installed")
        path = self.state_dir / "table-layout.json"
        write_json(path, report)
        self.set_artifact("tableLayout", path)

    def step_08_extract_image_text(self) -> None:
        mode = self.config.ocr_mode
        if mode in {"off", "none", "false"}:
            report = {"tool": "none", "status": "skipped", "reason": "OCR_MODE=off", "items": [], "recordedAt": now_iso()}
        elif mode == "local":
            if module_available("paddleocr"):
                try:
                    report = self._extract_ocr_with_paddleocr()
                except Exception as exc:
                    if self.config.strict_tools or not self.config.allow_degraded:
                        raise StepError("08_extract_image_text", f"PaddleOCR failed: {exc}") from exc
                    report = {"tool": "PaddleOCR", "status": "degraded", "items": [], "message": str(exc), "recordedAt": now_iso()}
            else:
                report = self.warn_or_fail("08_extract_image_text", "PaddleOCR is not installed")
        elif mode == "azure":
            if self.config.azure_vision_endpoint and self.config.azure_vision_key:
                try:
                    report = self._extract_ocr_with_azure_vision()
                except Exception as exc:
                    if self.config.strict_tools or not self.config.allow_degraded:
                        raise StepError("08_extract_image_text", f"Azure Vision OCR failed: {exc}") from exc
                    report = {"tool": "Azure AI Vision", "status": "degraded", "items": [], "message": str(exc), "recordedAt": now_iso()}
            else:
                report = self.warn_or_fail("08_extract_image_text", "Azure Vision endpoint/key are not configured")
        else:
            report = self.warn_or_fail("08_extract_image_text", f"Unknown OCR_MODE: {mode}")
        path = self.state_dir / "ocr-layout.json"
        write_json(path, report)
        self.set_artifact("ocrLayout", path)

    def step_09_build_segments(self) -> None:
        text_layout = read_json(self.state_dir / "text-bbox.json", {}) or {}
        segments = []
        page_texts: dict[int, list[str]] = {}
        page_segments: dict[int, list[dict[str, Any]]] = {}
        for page in text_layout.get("pages") or []:
            page_number = int(page.get("page") or 1)
            page_runs = self._merge_text_runs(page.get("runs") or [])
            for run in page_runs:
                source = str(run.get("text") or "").strip()
                if not source:
                    continue
                segment_id = f"p{page_number:04d}-s{len(segments):05d}"
                segment = {
                    "id": segment_id,
                    "source": source,
                    "translated": None,
                    "sourceLang": self.config.source_lang,
                    "targetLang": self.config.target_lang,
                    "page": page_number,
                    "pageWidth": page.get("width"),
                    "pageHeight": page.get("height"),
                    "bbox": run.get("bbox"),
                    "style": run.get("style"),
                    "origin": "pdf-text",
                    "sourceRunCount": run.get("sourceRunCount", 1),
                    "status": "pending",
                }
                segments.append(segment)
                page_texts.setdefault(page_number, []).append(normalize_text(source).lower())
                page_segments.setdefault(page_number, []).append(segment)

        skipped_ocr = []
        ocr_layout = read_json(self.state_dir / "ocr-layout.json", {}) or {}
        for item in ocr_layout.get("items") or []:
            source = str(item.get("text") or "").strip()
            if not source:
                continue
            page_number = int(item.get("page") or 1)
            normalized_source = normalize_text(source).lower()
            existing_texts = page_texts.get(page_number, [])
            if any(normalized_source == text or normalized_source in text or text in normalized_source for text in existing_texts if text):
                skipped_ocr.append({"id": item.get("id"), "page": page_number, "reason": "duplicate-text"})
                continue
            bbox = item.get("bbox") or {}
            if any(bbox_overlap_ratio(bbox, segment.get("bbox")) >= 0.55 for segment in page_segments.get(page_number, [])):
                skipped_ocr.append({"id": item.get("id"), "page": page_number, "reason": "overlap-pdf-text"})
                continue
            height = float(bbox.get("height") or 0)
            segment_id = f"p{page_number:04d}-s{len(segments):05d}"
            segment = {
                "id": segment_id,
                "source": source,
                "translated": None,
                "sourceLang": self.config.source_lang,
                "targetLang": self.config.target_lang,
                "page": page_number,
                "pageWidth": item.get("pageWidth"),
                "pageHeight": item.get("pageHeight"),
                "bbox": bbox,
                "style": {"fontSize": max(8.0, min(18.0, height * 0.86 if height else 10.0)), "font": "ocr", "color": [0.0, 0.0, 0.0]},
                "origin": "ocr-image",
                "ocrScore": item.get("score"),
                "status": "pending",
            }
            segments.append(segment)
            page_texts.setdefault(page_number, []).append(normalized_source)
            page_segments.setdefault(page_number, []).append(segment)

        origin_counts: dict[str, int] = {}
        for segment in segments:
            origin = str(segment.get("origin") or "unknown")
            origin_counts[origin] = origin_counts.get(origin, 0) + 1
        output = {
            "status": "ok",
            "segments": segments,
            "total": len(segments),
            "originCounts": origin_counts,
            "ocrMerged": origin_counts.get("ocr-image", 0),
            "ocrSkipped": skipped_ocr,
            "recordedAt": now_iso(),
        }
        path = self.state_dir / "segments.json"
        write_json(path, output)
        self.set_artifact("segments", path)

        sqlite_path = self.state_dir / "segments.sqlite"
        with sqlite3.connect(sqlite_path) as database:
            database.execute("CREATE TABLE IF NOT EXISTS segments (id TEXT PRIMARY KEY, source TEXT, translated TEXT, status TEXT, page INTEGER, origin TEXT)")
            database.execute("DELETE FROM segments")
            database.executemany(
                "INSERT INTO segments (id, source, translated, status, page, origin) VALUES (?, ?, ?, ?, ?, ?)",
                [(item["id"], item["source"], item.get("translated"), item["status"], item.get("page"), item.get("origin")) for item in segments],
            )
            database.commit()
        self.set_artifact("segmentsSqlite", sqlite_path)

    def step_10_translate_segments(self) -> None:
        self._init_tm()
        payload = read_json(self.state_dir / "segments.json", {}) or {}
        segments = payload.get("segments") or []
        translated_segments = []
        openai_items = []
        tm_hits = self._tm_get_many([str(item.get("source") or "") for item in segments])
        openai_available = module_available("openai")
        can_use_azure = self.config.translation_mode == "azure-openai" and bool(self.config.azure_openai_api_key and self.config.azure_openai_endpoint and self.config.azure_openai_deployment and openai_available)
        can_use_openai = self.config.translation_mode == "openai" and bool(self.config.openai_api_key and openai_available)
        for item in segments:
            cached = tm_hits.get(item["source"])
            if cached is not None:
                item["translated"] = cached
                item["status"] = "tm-hit"
            elif not is_translatable_text(item["source"]):
                item["translated"] = item["source"]
                item["status"] = "not-translatable-source-copy"
            elif can_use_azure:
                openai_items.append(item)
            elif can_use_openai:
                openai_items.append(item)
            else:
                item["translated"] = item["source"]
                item["status"] = "source-copy"
            translated_segments.append(item)

        if openai_items:
            batch_size = 40
            print(f"[translate] api-items={len(openai_items)} batch-size={batch_size}", flush=True)
            for offset in range(0, len(openai_items), batch_size):
                batch = openai_items[offset:offset + batch_size]
                print(f"[translate] batch {offset + 1}-{offset + len(batch)} / {len(openai_items)}", flush=True)
                try:
                    if self.config.translation_mode == "azure-openai":
                        translations = self._translate_azure_openai_batch(batch)
                        model_name = self.config.azure_openai_deployment
                    else:
                        translations = self._translate_openai_batch(batch)
                        model_name = self.config.openai_model
                except Exception as exc:
                    for item in batch:
                        item["translated"] = item["source"]
                        item["status"] = "translation-failed-source-copy"
                        item["error"] = str(exc)
                    continue
                for item in batch:
                    translated = translations.get(item["id"], item["source"])
                    item["translated"] = translated
                    item["status"] = "translated"
                self._tm_put_many([(item["source"], item["translated"], model_name) for item in batch])
                progress = {
                    "status": "running",
                    "translationMode": self.config.translation_mode,
                    "apiItems": len(openai_items),
                    "completedApiItems": offset + len(batch),
                    "stats": {
                        "total": len(translated_segments),
                        "translated": sum(1 for translated_item in translated_segments if translated_item.get("status") == "translated"),
                        "tmHit": sum(1 for translated_item in translated_segments if translated_item.get("status") == "tm-hit"),
                        "sourceCopy": sum(1 for translated_item in translated_segments if "copy" in str(translated_item.get("status"))),
                    },
                    "recordedAt": now_iso(),
                }
                write_json(self.state_dir / "translated-progress.json", progress)
                print(f"[translate] done {offset + len(batch)} / {len(openai_items)} translated={progress['stats']['translated']}", flush=True)

        output = {
            "status": "ok",
            "translationMode": self.config.translation_mode,
            "segments": translated_segments,
            "stats": {
                "total": len(translated_segments),
                "translated": sum(1 for item in translated_segments if item.get("status") == "translated"),
                "tmHit": sum(1 for item in translated_segments if item.get("status") == "tm-hit"),
                "sourceCopy": sum(1 for item in translated_segments if "copy" in str(item.get("status"))),
            },
            "recordedAt": now_iso(),
        }
        path = self.state_dir / "translated.json"
        write_json(path, output)
        self.set_artifact("translated", path)

    def step_11_shape_text(self) -> None:
        translated = read_json(self.state_dir / "translated.json", {}) or {}
        shaped_runs = []
        shaped_count = 0
        degraded_count = 0
        for item in translated.get("segments") or []:
            style = item.get("style") or {}
            text = item.get("translated") or item.get("source") or ""
            font_size = max(4.0, float(style.get("fontSize") or 10))
            font_path = self._select_font_path(style)
            glyph_lines = []
            status = "passthrough"
            engine = "harfbuzz-unavailable"
            message = None
            if module_available("uharfbuzz") and font_path:
                try:
                    glyph_lines = self._shape_text_with_harfbuzz(str(text), font_path, font_size)
                    status = "shaped"
                    engine = "harfbuzz"
                    shaped_count += 1
                except Exception as exc:
                    status = "passthrough"
                    engine = "harfbuzz-degraded"
                    message = str(exc)
                    degraded_count += 1
            else:
                degraded_count += 1
            shaped_runs.append({
                "id": item["id"],
                "page": item["page"],
                "text": text,
                "bbox": item.get("bbox"),
                "style": style,
                "engine": engine,
                "fontPath": font_path,
                "glyphLines": glyph_lines,
                "glyphs": [glyph for line in glyph_lines for glyph in line.get("glyphs", [])],
                "status": status,
                **({"message": message} if message else {}),
            })
        path = self.state_dir / "shaped-runs.json"
        write_json(path, {"status": "ok" if shaped_count else "degraded", "tool": "HarfBuzz", "shaped": shaped_count, "degraded": degraded_count, "runs": shaped_runs, "recordedAt": now_iso()})
        self.set_artifact("shapedRuns", path)

    def step_12_layout_text(self) -> None:
        shaped = read_json(self.state_dir / "shaped-runs.json", {}) or {}
        page_sizes = {int(item["page"]): item for item in self._pdf_page_sizes()}
        pages: dict[int, dict[str, Any]] = {}
        pango_modules = None
        pango_error = None
        try:
            pango_modules = self._load_pango_cairo()
        except Exception as exc:
            pango_error = str(exc)
        pango_count = 0
        degraded_count = 0
        overflow_count = 0
        for run in shaped.get("runs") or []:
            page_number = int(run.get("page") or 1)
            page_info = page_sizes.get(page_number, {"page": page_number, "width": 612.0, "height": 792.0})
            page_entry = pages.setdefault(page_number, {"page": page_number, "width": page_info["width"], "height": page_info["height"], "items": []})
            bbox = run.get("bbox") or {"x": 0, "y": 0, "width": 160, "height": 20}
            style = run.get("style") or {"fontSize": 10, "color": [0, 0, 0]}
            text = str(run.get("text") or "")
            try:
                layout_result = self._layout_with_pango(text, bbox, style, float(page_info["height"]), pango_modules) if pango_modules else self._layout_with_custom_wrapper(text, bbox, style, float(page_info["height"]))
            except Exception as exc:
                layout_result = self._layout_with_custom_wrapper(text, bbox, style, float(page_info["height"]))
                layout_result["layoutEngine"] = "pango-degraded-custom-wrapper"
                layout_result["message"] = str(exc)
            if layout_result["layoutEngine"] == "pango":
                pango_count += 1
            else:
                degraded_count += 1
            if layout_result.get("overflow"):
                overflow_count += 1
            fitted_style = dict(style)
            if layout_result.get("fontSize"):
                fitted_style["fontSize"] = layout_result["fontSize"]
            page_entry["items"].append({
                "id": run.get("id"),
                "text": layout_result["text"],
                "bbox": layout_result["bbox"],
                "style": fitted_style,
                "origin": "translated-text",
                "layoutEngine": layout_result["layoutEngine"],
                "lineMetrics": layout_result.get("lineMetrics", []),
                "measuredWidth": layout_result.get("measuredWidth"),
                "measuredHeight": layout_result.get("measuredHeight"),
                "overflow": layout_result.get("overflow", False),
                **({"message": layout_result["message"]} if layout_result.get("message") else {}),
            })
        output = {
            "status": "ok" if pango_count and not overflow_count else "degraded",
            "tool": "Pango",
            "pangoLayoutItems": pango_count,
            "degradedLayoutItems": degraded_count,
            "overflowItems": overflow_count,
            "pages": [pages[key] for key in sorted(pages)],
            "recordedAt": now_iso(),
            **({"message": pango_error} if pango_error else {}),
        }
        path = self.state_dir / "positioned-layout.json"
        write_json(path, output)
        self.set_artifact("positionedLayout", path)

    def step_13_build_draft_pdf(self) -> None:
        target = self.pdf_dir / "draft.pdf"
        try:
            report = self._build_pdf_with_cairo(target)
        except Exception as exc:
            if not self.config.allow_degraded:
                raise StepError("13_build_draft_pdf", f"Cairo PDF builder failed: {exc}")
            if module_available("reportlab"):
                report = self._build_pdf_with_reportlab(target)
                report["degradedFrom"] = "cairo"
                report["degradedReason"] = str(exc)
            elif module_available("fitz"):
                report = self._build_pdf_with_pymupdf(target)
                report["degradedFrom"] = "cairo"
                report["degradedReason"] = str(exc)
            else:
                raise StepError("13_build_draft_pdf", "Cairo failed, ReportLab is not installed, and PyMuPDF degraded builder is disabled")
        path = self.state_dir / "build-report.json"
        write_json(path, {"status": "ok", **report, "recordedAt": now_iso()})
        self.set_artifact("draftPdf", target)
        self.set_artifact("buildReport", path)

    def step_14_restore_pdf_objects(self) -> None:
        draft = self.pdf_dir / "draft.pdf"
        enriched = self.pdf_dir / "enriched.pdf"
        if module_available("pikepdf"):
            try:
                report = self._restore_pdf_objects_with_pikepdf(draft, enriched)
            except Exception as exc:
                if self.config.strict_tools or not self.config.allow_degraded:
                    raise StepError("14_restore_pdf_objects", f"pikepdf object restore failed: {exc}") from exc
                self._copy_file(draft, enriched)
                report = {"status": "degraded", "tool": "pikepdf", "message": f"pikepdf object restore failed; draft copied to enriched: {exc}", "output": str(enriched.relative_to(self.job_dir))}
        else:
            if self.config.strict_tools or not self.config.allow_degraded:
                raise StepError("14_restore_pdf_objects", "pikepdf is not installed")
            self._copy_file(draft, enriched)
            report = {"status": "degraded", "tool": "pikepdf", "message": "pikepdf is not installed; draft copied to enriched.", "output": str(enriched.relative_to(self.job_dir))}
        path = self.state_dir / "restore-report.json"
        write_json(path, report)
        self.set_artifact("enrichedPdf", enriched)
        self.set_artifact("restoreReport", path)

    def step_15_optimize_pdf(self) -> None:
        enriched = self.pdf_dir / "enriched.pdf"
        optimized = self.pdf_dir / "optimized.pdf"
        if command_path("qpdf"):
            result = run_command(["qpdf", "--linearize", str(enriched), str(optimized)], timeout=180)
            if result["exitCode"] != 0:
                self._copy_file(enriched, optimized)
                report = {"status": "degraded", "tool": "qpdf", "message": "qpdf optimize failed; copied enriched PDF", "result": result}
            else:
                report = {"status": "ok", "tool": "qpdf", "result": result}
        elif command_path("gs"):
            result = run_command([
                "gs",
                "-sDEVICE=pdfwrite",
                "-dCompatibilityLevel=1.7",
                "-dPDFSETTINGS=/prepress",
                "-dNOPAUSE",
                "-dQUIET",
                "-dBATCH",
                f"-sOutputFile={optimized}",
                str(enriched),
            ], timeout=240)
            if result["exitCode"] == 0 and optimized.exists():
                report = {"status": "degraded", "tool": "ghostscript", "message": "QPDF is not installed; Ghostscript produced optimized PDF without QPDF linearization.", "result": result}
            else:
                self._copy_file(enriched, optimized)
                report = {"status": "degraded", "tool": "ghostscript", "message": "Ghostscript optimize failed; copied enriched PDF", "result": result}
        else:
            self._copy_file(enriched, optimized)
            report = self.warn_or_fail("15_optimize_pdf", "QPDF is not installed; copied enriched PDF")
        path = self.state_dir / "optimize-report.json"
        write_json(path, report)
        self.set_artifact("optimizedPdf", optimized)
        self.set_artifact("optimizeReport", path)

    def step_16_validate_output_pdf(self) -> None:
        optimized = self.pdf_dir / "optimized.pdf"
        if command_path("qpdf"):
            result = run_command(["qpdf", "--check", str(optimized)], timeout=120)
            report = {"tool": "qpdf", "status": "ok" if result["exitCode"] == 0 else "failed", "result": result}
            if result["exitCode"] != 0:
                write_json(self.state_dir / "output-validation.json", report)
                raise StepError("16_validate_output_pdf", "Output QPDF validation failed")
        elif module_available("pikepdf") and self.config.allow_degraded:
            import pikepdf  # type: ignore
            with pikepdf.open(optimized) as document:
                report = {"tool": "pikepdf-degraded", "status": "degraded", "pageCount": len(document.pages), "objectCount": len(document.objects)}
        elif module_available("fitz") and self.config.allow_degraded:
            import fitz  # type: ignore
            with fitz.open(optimized) as document:
                report = {"tool": "pymupdf-degraded", "status": "degraded", "pageCount": document.page_count}
        else:
            raise StepError("16_validate_output_pdf", "No output validation tool is available")
        path = self.state_dir / "output-validation.json"
        write_json(path, report)
        self.set_artifact("outputValidation", path)

    def step_17_render_diff(self) -> None:
        optimized = self.pdf_dir / "optimized.pdf"
        output_render = self._render_pdf(optimized, self.pages_dir / "output", "output")
        source_render = read_json(self.state_dir / "render-source.json", {}) or {}
        diff_report: dict[str, Any] = {"status": "ok", "tool": output_render.get("engine"), "pages": [], "recordedAt": now_iso()}
        if module_available("PIL"):
            from PIL import Image, ImageChops, ImageStat  # type: ignore
            for source_page, output_page in zip(source_render.get("pages") or [], output_render.get("pages") or []):
                source_image = self.job_dir / source_page["image"]
                output_image = self.job_dir / output_page["image"]
                try:
                    with Image.open(source_image) as left_image, Image.open(output_image) as right_image:
                        left = left_image.convert("RGB")
                        right = right_image.convert("RGB").resize(left.size)
                        diff = ImageChops.difference(left, right)
                        stat = ImageStat.Stat(diff)
                        mean = sum(stat.mean) / len(stat.mean)
                        diff_report["pages"].append({"page": source_page["page"], "meanDiff": mean})
                except Exception as exc:
                    diff_report["pages"].append({"page": source_page.get("page"), "error": str(exc)})
        else:
            diff_report["status"] = "degraded"
            diff_report["message"] = "Pillow is not installed; render images were created but diff was skipped."
        path = self.state_dir / "render-diff.json"
        write_json(path, diff_report)
        self.set_artifact("renderDiff", path)

        page_means = [float(page.get("meanDiff") or 0) for page in diff_report.get("pages") or [] if "meanDiff" in page]
        max_mean_diff = max(page_means) if page_means else None
        average_mean_diff = sum(page_means) / len(page_means) if page_means else None
        translated = read_json(self.state_dir / "translated.json", {}) or {}
        segments = read_json(self.state_dir / "segments.json", {}) or {}
        validation = read_json(self.state_dir / "output-validation.json", {}) or {}
        layout_state = read_json(self.state_dir / "positioned-layout.json", {}) or {}
        build_report = read_json(self.state_dir / "build-report.json", {}) or {}
        quality_status = "ok"
        reasons = []
        if diff_report.get("status") == "degraded":
            quality_status = "review"
            reasons.append("render-diff-degraded")
        if max_mean_diff is not None and max_mean_diff > self.config.render_diff_warn_mean:
            quality_status = "review"
            reasons.append("render-diff-over-warn")
        if max_mean_diff is not None and max_mean_diff > self.config.render_diff_fail_mean:
            quality_status = "blocked"
            reasons.append("render-diff-over-fail")
        if validation.get("status") not in {"ok", "degraded"}:
            quality_status = "blocked"
            reasons.append("output-validation-not-ok")
        if layout_state.get("status") != "ok":
            quality_status = "review" if quality_status == "ok" else quality_status
            reasons.append("layout-degraded")
        if int(layout_state.get("overflowItems") or 0) > 0:
            quality_status = "review" if quality_status == "ok" else quality_status
            reasons.append("layout-overflow")
        if build_report.get("degradedFrom"):
            quality_status = "review" if quality_status == "ok" else quality_status
            reasons.append("build-degraded")
        quality_report = {
            "status": quality_status,
            "reasons": reasons,
            "thresholds": {
                "renderDiffWarnMean": self.config.render_diff_warn_mean,
                "renderDiffFailMean": self.config.render_diff_fail_mean,
            },
            "renderDiff": {
                "tool": diff_report.get("tool"),
                "pageCount": len(diff_report.get("pages") or []),
                "averageMeanDiff": average_mean_diff,
                "maxMeanDiff": max_mean_diff,
            },
            "layout": {
                "tool": layout_state.get("tool"),
                "status": layout_state.get("status"),
                "pangoLayoutItems": layout_state.get("pangoLayoutItems", 0),
                "degradedLayoutItems": layout_state.get("degradedLayoutItems", 0),
                "overflowItems": layout_state.get("overflowItems", 0),
            },
            "build": {
                "engine": build_report.get("engine"),
                "textLayout": build_report.get("textLayout"),
                "status": build_report.get("status"),
                "degradedFrom": build_report.get("degradedFrom"),
            },
            "segments": {
                "total": segments.get("total", 0),
                "originCounts": segments.get("originCounts", {}),
                "ocrMerged": segments.get("ocrMerged", 0),
                "ocrSkipped": len(segments.get("ocrSkipped") or []),
            },
            "translation": translated.get("stats", {}),
            "validation": {"tool": validation.get("tool"), "status": validation.get("status")},
            "recordedAt": now_iso(),
        }
        quality_path = self.state_dir / "quality-report.json"
        write_json(quality_path, quality_report)
        self.set_artifact("qualityReport", quality_path)

    def step_18_publish_output(self) -> None:
        optimized = self.pdf_dir / "optimized.pdf"
        output_path = self._make_output_path()
        self._copy_file(optimized, output_path)
        report = {"status": "ok", "output": str(output_path), "recordedAt": now_iso()}
        path = self.state_dir / "publish-report.json"
        write_json(path, report)
        self.set_artifact("outputPdf", output_path)
        self.set_artifact("publishReport", path)


for step_name in STEP_ORDER:
    method_name = f"step_{step_name}"
    setattr(Pipeline, step_name, getattr(Pipeline, method_name))


def list_input_pdfs(config: Config) -> list[Path]:
    if not config.input_dir.exists():
        return []
    return sorted(
        path for path in config.input_dir.glob("*.pdf")
        if path.is_file() and not path.name.startswith("~$")
    )


def run_doctor(config: Config) -> int:
    report = tool_report()
    required_commands = ["qpdf", "node", "sqlite3"]
    required_modules = ["pikepdf", "pdfplumber", "reportlab", "pypdfium2", "fitz"]
    missing = []
    for name in required_commands:
        if not report["commands"].get(name, {}).get("available"):
            missing.append(name)
    for name in required_modules:
        if not report["pythonModules"].get(name, {}).get("available"):
            missing.append(name)
    report["missing"] = missing
    report["status"] = "ok" if not missing else "missing-tools"
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not missing or config.allow_degraded else 1


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="run-v5.sh")
    parser.add_argument("items", nargs="*", help="command or PDF path")
    parser.add_argument("--in-lang", dest="in_lang")
    parser.add_argument("--out-lang", dest="out_lang")
    parser.add_argument("--ocr", choices=["off", "local", "azure"], default=None)
    parser.add_argument("--translation-mode", choices=["copy", "openai", "azure-openai"], default=None)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--keep-work", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    config = load_config(args)
    command = "run"
    pdf_arg = None
    remaining = list(args.items)
    if remaining and remaining[0] in {"doctor", "run"}:
        command = remaining.pop(0)
    if remaining:
        pdf_arg = remaining[0]

    if command == "doctor":
        return run_doctor(config)

    ensure_dir(config.work_dir)
    ensure_dir(config.output_dir)
    ensure_dir(config.input_dir)
    ensure_dir(config.input_dir / "done")

    input_files = [Path(pdf_arg)] if pdf_arg else list_input_pdfs(config)
    if not input_files:
        print(f"[warn] input PDF not found: {config.input_dir}")
        return 0

    failures = 0
    for input_file in input_files:
        source_pdf = input_file if input_file.is_absolute() else ROOT / input_file
        pipeline = Pipeline(config, source_pdf)
        try:
            pipeline.run()
        except Exception as exc:
            failures += 1
            print(f"[error] {source_pdf}: {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
