from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STEP_ORDER = [
    "01_init_job",
    "02_extract_pdf_state",
    "03_translate_text_state",
    "04_build_pdf_from_state",
    "05_publish_output",
]

TEXT_FEATURES = [
    "PDF object/page 접근",
    "Page content stream 접근/해석",
    "Content stream decode/uncompress",
    "Content stream 재작성",
    "Font resource/name/type",
    "Embedded font 여부",
    "Encoding/CMap/ToUnicode/Glyph code",
    "Unicode text extraction",
    "글자/글리프 단위 위치",
    "Glyph width/advance/font size",
    "Text matrix/CTM/rotation/skew",
    "Curved/rotated text 글자별 배치",
    "Text state: spacing/leading/rise/render mode",
    "Fill/stroke color/color space",
    "Opacity/blend/layer/OCG",
    "Text bbox/baseline/position",
    "Writing direction/vertical writing",
    "Ligature/Unicode mapping 보존",
    "Kerning/TJ adjustment",
    "Draw order",
    "Marked content/ActualText/Alt text",
    "Plain text export",
    "HTML/XML/JSON structured export",
    "Bold/Italic 자동 판정",
    "Fake bold 자동 판정",
    "Underline/Strikethrough 자동 추출",
    "Highlight/background 자동 추출",
    "Word/HTML식 style model",
    "Path/outline text 복원",
    "Bidi/RTL/reading order",
    "원본 text state JSON export/rewrite",
    "원본 content stream 동일 재현",
]


@dataclass
class Config:
    base_dir: Path
    input_dir: Path
    output_dir: Path
    work_dir: Path
    build_mode: str
    text_font_file: str
    source_lang: str
    target_lang: str
    openai_api_key: str
    openai_model: str
    max_chunk_chars: int
    max_chunk_items: int
    keep_text_raw: bool
    keep_char_state: bool
    keep_translation_chunks: bool
    keep_translation_results: bool


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def safe_stem(path: Path) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", path.stem).strip("-._")
    return text[:120] or "document"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def decoded_stream_text(value: bytes) -> dict[str, str]:
    try:
        return {"encoding": "utf-8", "text": value.decode("utf-8")}
    except UnicodeDecodeError:
        return {"encoding": "latin-1", "text": value.decode("latin-1")}


def pdf_operator_counts(text: str) -> dict[str, int]:
    operators = ["BT", "ET", "Tf", "Tm", "Td", "TD", "Tj", "TJ", "Tc", "Tw", "Tz", "TL", "Tr", "Ts"]
    return {operator: len(re.findall(rf"(?<!\S){re.escape(operator)}(?!\S)", text)) for operator in operators}


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def bool_env(name: str, default: bool = False) -> bool:
    value = env(name)
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "y", "on"}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="pdf-translate-v8 PDF state JSON round-trip project with chunked OpenAI translation")
    parser.add_argument("pdf", nargs="?", help="Source PDF. Defaults to the first PDF in input/.")
    parser.add_argument("--state", help="Existing pdf-state.json to build from.")
    parser.add_argument("--build-mode", choices=["exact", "semantic"], help="exact restores the source bytes from JSON; semantic starts from source bytes and writes text state.")
    parser.add_argument("--in-lang", help="Source language")
    parser.add_argument("--out-lang", help="Target language")
    parser.add_argument("--max-chunk-chars", type=int, help="Maximum source characters per OpenAI translation chunk")
    parser.add_argument("--max-chunk-items", type=int, help="Maximum text objects per OpenAI translation chunk")
    parser.add_argument("--keep-text-raw", action="store_true", help="Store PyMuPDF raw text dict in pdf-state.json")
    parser.add_argument("--keep-char-state", action="store_true", help="Store char-level state in textObjects")
    parser.add_argument("--keep-translation-chunks", action="store_true", help="Store full translation chunk payloads")
    parser.add_argument("--keep-translation-results", action="store_true", help="Store full translation result text")
    parser.add_argument("--extract-only", action="store_true", help="Only write pdf-state.json.")
    parser.add_argument("--keep-work", action="store_true", help="Work directory is always kept for state inspection.")
    return parser.parse_args(argv)


def load_config(base_dir: Path, args: argparse.Namespace) -> Config:
    load_env_file(base_dir / ".env")
    return Config(
        base_dir=base_dir,
        input_dir=base_dir / "input",
        output_dir=base_dir / "output",
        work_dir=base_dir / "work",
        build_mode=args.build_mode or env("PDF_BUILD_MODE", "exact"),
        text_font_file=env("TEXT_FONT_FILE") or env("PDF_TEXT_FONT_FILE") or env("PDF_CJK_FONT_FILE"),
        source_lang=args.in_lang or env("SOURCE_LANG", "en"),
        target_lang=args.out_lang or env("TARGET_LANG", "ko"),
        openai_api_key=env("OPENAI_API_KEY"),
        openai_model=env("OPENAI_MODEL", "gpt-4.1-mini"),
        max_chunk_chars=args.max_chunk_chars or int_value(env("MAX_CHUNK_CHARS"), 10000),
        max_chunk_items=args.max_chunk_items or int_value(env("MAX_CHUNK_ITEMS"), 250),
        keep_text_raw=args.keep_text_raw or bool_env("KEEP_TEXT_RAW", False),
        keep_char_state=args.keep_char_state or bool_env("KEEP_CHAR_STATE", False),
        keep_translation_chunks=args.keep_translation_chunks or bool_env("KEEP_TRANSLATION_CHUNKS", False),
        keep_translation_results=args.keep_translation_results or bool_env("KEEP_TRANSLATION_RESULTS", False),
    )


def resolve_source_pdf(config: Config, value: str | None) -> Path:
    if value:
        path = Path(value)
        if not path.is_absolute():
            path = config.base_dir / path
        path = path.resolve()
        if not path.exists():
            raise FileNotFoundError(f"Source PDF does not exist: {path}")
        return path
    ensure_dir(config.input_dir)
    candidates = sorted(config.input_dir.glob("*.pdf"))
    if not candidates:
        raise FileNotFoundError(
            "No source PDF found. Put a PDF in "
            f"{config.input_dir} or run ./run-v8.sh path/to/file.pdf"
        )
    return candidates[0].resolve()


def point_value(value: Any) -> list[float]:
    if hasattr(value, "x") and hasattr(value, "y"):
        return [float(value.x), float(value.y)]
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return [float(value[0]), float(value[1])]
    return [0.0, 0.0]


def rect_value(value: Any) -> list[float]:
    if hasattr(value, "x0"):
        return [float(value.x0), float(value.y0), float(value.x1), float(value.y1)]
    if isinstance(value, (list, tuple)) and len(value) >= 4:
        return [float(value[0]), float(value[1]), float(value[2]), float(value[3])]
    return [0.0, 0.0, 0.0, 0.0]


def rect_state(value: Any) -> dict[str, float]:
    left, top, right, bottom = rect_value(value)
    return {
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "width": max(0.0, right - left),
        "height": max(0.0, bottom - top),
    }


def color_value(value: Any) -> list[float] | None:
    if value is None:
        return None
    if isinstance(value, int):
        return [((value >> 16) & 255) / 255, ((value >> 8) & 255) / 255, (value & 255) / 255]
    if isinstance(value, (list, tuple)):
        return [float(item) for item in value[:3]]
    return None


def float_value(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def line_rotation(direction: Any) -> int:
    dx, dy = point_value(direction)
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return 0
    angle = math.degrees(math.atan2(dy, dx)) % 360
    cardinal = min((0, 90, 180, 270), key=lambda item: abs(((angle - item + 180) % 360) - 180))
    if abs(((angle - cardinal + 180) % 360) - 180) <= 2.0:
        return cardinal
    return 0


def text_from_chars(chars: list[dict[str, Any]]) -> str:
    return "".join(str(char.get("text") or "") for char in chars)


def language_label(value: str) -> str:
    normalized = value.strip().lower()
    labels = {
        "en": "English",
        "eng": "English",
        "ko": "Korean",
        "kr": "Korean",
        "kor": "Korean",
        "korean": "Korean",
    }
    return labels.get(normalized, value or "the target language")


def is_valid_rect(rect: list[float]) -> bool:
    return len(rect) >= 4 and rect[2] > rect[0] and rect[3] > rect[1]


def object_rect_value(value: Any) -> list[float]:
    if isinstance(value, dict):
        return [
            float_value(value.get("left")),
            float_value(value.get("top")),
            float_value(value.get("right")),
            float_value(value.get("bottom")),
        ]
    return rect_value(value)


def is_unusable_extracted_text(text: str) -> bool:
    compact = "".join(char for char in text if not char.isspace())
    if not compact:
        return True
    replacement_count = compact.count("\ufffd")
    if replacement_count == 0:
        return False
    ascii_word_count = len(re.findall(r"[A-Za-z]{2,}", compact))
    return replacement_count / len(compact) >= 0.35 and ascii_word_count == 0


def serialize_path_item(item: Any) -> dict[str, Any]:
    op = str(item[0]) if isinstance(item, (list, tuple)) and item else "unknown"
    values = list(item[1:]) if isinstance(item, (list, tuple)) else []
    if op == "re" and values:
        return {"op": op, "rect": rect_state(values[0]), "orientation": int(values[1]) if len(values) > 1 and isinstance(values[1], int) else None}
    if op in {"m", "l", "c"}:
        return {"op": op, "points": [point_value(value) for value in values]}
    if op == "qu" and values:
        return {"op": op, "quad": [point_value(point) for point in values[0]] if isinstance(values[0], (list, tuple)) else []}
    return {"op": op, "raw": str(item)}


def serialize_char(char: dict[str, Any]) -> dict[str, Any]:
    return {
        "text": str(char.get("c") or ""),
        "origin": point_value(char.get("origin")),
        "rect": rect_state(char.get("bbox")),
    }


class Pipeline:
    def __init__(self, config: Config, source_pdf: Path | None, state_path: Path | None, extract_only: bool):
        self.config = config
        self.source_pdf = source_pdf
        self.state_path_arg = state_path
        self.extract_only = extract_only
        source_name = safe_stem(source_pdf) if source_pdf else safe_stem(state_path or Path("state"))
        self.job_id = f"{source_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.job_dir = config.work_dir / self.job_id
        self.state_dir = self.job_dir / "state"
        self.reference_dir = self.job_dir / "reference"
        self.reference_image_dir = self.reference_dir / "images" / source_name
        self.pdf_dir = self.job_dir / "pdf"
        self.job_path = self.state_dir / "job.json"
        self.progress_path = self.state_dir / "progress.json"
        self.state_path = self.state_dir / "pdf-state.json"
        self._resolved_text_font_file: str | None = None

    def log(self, message: str) -> None:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}", flush=True)

    def log_progress(self, step: str, current: int, total: int, message: str = "", **extra: Any) -> None:
        percent = round((current / total) * 100, 1) if total > 0 else 100.0
        suffix = f" - {message}" if message else ""
        self.log(f"PROGRESS {step} {current}/{total} ({percent:.1f}%){suffix}")
        write_json(self.progress_path, {
            "jobId": self.job_id,
            "step": step,
            "current": current,
            "total": total,
            "percent": percent,
            "message": message,
            "updatedAt": now_iso(),
            **extra,
        })

    def run(self) -> None:
        for step in STEP_ORDER:
            if self.extract_only and step in {"03_translate_text_state", "04_build_pdf_from_state", "05_publish_output"}:
                continue
            if self.state_path_arg and step == "02_extract_pdf_state":
                continue
            self.log(f"START {step}")
            self.update_job(status="running", currentStep=step)
            getattr(self, f"step_{step}")()
            self.log(f"DONE  {step}")
        self.update_job(status="completed", currentStep=None)

    def initialize_dirs(self) -> None:
        for path in [self.state_dir, self.reference_dir, self.reference_image_dir, self.pdf_dir, self.config.output_dir, self.config.work_dir]:
            ensure_dir(path)

    def update_job(self, **updates: Any) -> None:
        state = read_json(self.job_path, {}) if self.job_path.exists() else {}
        state.update(updates)
        state["updatedAt"] = now_iso()
        write_json(self.job_path, state)

    def step_01_init_job(self) -> None:
        self.initialize_dirs()
        if self.state_path_arg:
            shutil.copyfile(self.state_path_arg, self.state_path)
        write_json(self.job_path, {
            "jobId": self.job_id,
            "sourcePdf": str(self.source_pdf) if self.source_pdf else None,
            "statePath": str(self.state_path),
            "buildMode": self.config.build_mode,
            "sourceLang": self.config.source_lang,
            "targetLang": self.config.target_lang,
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
            "status": "created",
        })

    def step_02_extract_pdf_state(self) -> None:
        import fitz  # type: ignore

        if not self.source_pdf:
            raise ValueError("source_pdf is required for extract")
        source_bytes = self.source_pdf.read_bytes()
        pages = []
        content_stream_pages = []
        with fitz.open(self.source_pdf) as document:
            page_total = len(document)
            self.log_progress("02_extract_pdf_state", 0, page_total, "start extracting pages")
            for page_index, page in enumerate(document):
                page_number = page_index + 1
                texts = self.extract_text_objects(page, page_number)
                reference_objects = self.extract_reference_objects(document, page, page_number)
                content_stream_pages.append(self.extract_reference_content_streams(document, page, page_number))
                pages.append({
                    "page": page_number,
                    "size": {"width": float(page.rect.width), "height": float(page.rect.height)},
                    "rotation": int(page.rotation or 0),
                    "rectangles": {
                        "page": rect_state(page.rect),
                        "media": rect_state(page.mediabox),
                        "crop": rect_state(page.cropbox),
                    },
                    "resources": {
                        "fonts": self.extract_fonts(page),
                        "imageCount": len(page.get_images(full=True) or []),
                    },
                    "textPlain": page.get_text("text") or "",
                    "textObjects": texts,
                    "referenceObjects": reference_objects,
                    "counts": {
                        "texts": len(texts),
                        "referenceObjects": len(reference_objects),
                        "referenceImages": len([item for item in reference_objects if item.get("type") == "image"]),
                        "referencePaths": len([item for item in reference_objects if item.get("type") == "path"]),
                        "referenceTables": len([item for item in reference_objects if item.get("type") == "table"]),
                    },
                })
                if self.config.keep_text_raw:
                    pages[-1]["textRaw"] = page.get_text("rawdict") or {}
                self.log_progress(
                    "02_extract_pdf_state",
                    page_number,
                    page_total,
                    f"page {page_number}: text={len(texts)}, reference={len(reference_objects)}",
                    textCount=len(texts),
                    referenceCount=len(reference_objects),
                )
            metadata = dict(document.metadata or {})
        state = {
            "schemaVersion": "v8.0",
            "captureProfile": "source-bytes-plus-text-state",
            "createdAt": now_iso(),
            "featureSource": "profile/Microsoft/PTC/News/pdf_project_text4.md",
            "implementedTextFeatures": TEXT_FEATURES,
            "source": {
                "name": self.source_pdf.name,
                "path": str(self.source_pdf),
                "sizeBytes": len(source_bytes),
                "sha256": sha256_bytes(source_bytes),
                "bytesBase64": base64.b64encode(source_bytes).decode("ascii"),
            },
            "document": {"metadata": metadata, "pageCount": len(pages)},
            "reference": {
                "purpose": "inspection-only; not used for PDF rebuild",
                "imageDir": str(self.reference_image_dir.relative_to(self.job_dir)),
                "contentStreamState": "reference/content-streams.json",
            },
            "pages": pages,
        }
        write_json(self.reference_dir / "content-streams.json", {
            "createdAt": now_iso(),
            "purpose": "decoded PDF content streams for inspection; not used for PDF rebuild",
            "source": self.source_pdf.name,
            "pageCount": len(content_stream_pages),
            "pages": content_stream_pages,
        })
        write_json(self.state_path, state)
        self.write_text_state_json(state, self.state_dir / "text-state.json", "extracted")

    def write_text_state_json(self, state: dict[str, Any], path: Path, status: str) -> None:
        pages = state.get("pages", [])
        output_pages = []
        for page in pages:
            text_objects = []
            for item in self.page_text_objects(page):
                text_objects.append({
                    "id": str(item.get("id") or ""),
                    "page": int_value(item.get("page"), int_value(page.get("page"), 0)),
                    "order": int_value(item.get("order"), 0),
                    "source": str(item.get("source") or ""),
                    "text": str(item.get("text") or ""),
                    "translationStatus": str(item.get("translationStatus") or "source"),
                    "rect": item.get("rect"),
                    "textState": item.get("textState"),
                    "styleModel": item.get("styleModel"),
                })
            output_pages.append({
                "page": int_value(page.get("page"), 0),
                "size": page.get("size"),
                "textCount": len(text_objects),
                "textObjects": text_objects,
            })
        write_json(path, {
            "createdAt": now_iso(),
            "status": status,
            "purpose": "human-readable text state used for translation and PDF text input",
            "source": (state.get("source") or {}).get("name"),
            "pageCount": len(output_pages),
            "pages": output_pages,
        })

    def extract_fonts(self, page: Any) -> list[dict[str, Any]]:
        fonts = []
        for font in page.get_fonts(full=True) or []:
            fonts.append({
                "xref": int_value(font[0]) if len(font) > 0 else 0,
                "ext": str(font[1]) if len(font) > 1 else "",
                "type": str(font[2]) if len(font) > 2 else "",
                "baseFont": str(font[3]) if len(font) > 3 else "",
                "name": str(font[4]) if len(font) > 4 else "",
                "encoding": str(font[5]) if len(font) > 5 else "",
                "embedded": bool(font[6]) if len(font) > 6 else None,
            })
        return fonts

    def extract_reference_objects(self, document: Any, page: Any, page_number: int) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        records.extend(self.extract_reference_paths(page, page_number))
        records.extend(self.extract_reference_images(document, page, page_number))
        records.extend(self.extract_reference_tables(page, page_number))
        return records

    def extract_reference_content_streams(self, document: Any, page: Any, page_number: int) -> dict[str, Any]:
        records: list[dict[str, Any]] = []
        seen: set[int] = set()
        for index, xref in enumerate(page.get_contents() or []):
            xref_id = int_value(xref)
            if xref_id <= 0 or xref_id in seen:
                continue
            seen.add(xref_id)
            records.append(self.content_stream_record(document, xref_id, page_number, "page-content", index))
        for index, xobject in enumerate(page.get_xobjects() or []):
            if not isinstance(xobject, (list, tuple)) or not xobject:
                continue
            xref_id = int_value(xobject[0])
            if xref_id <= 0 or xref_id in seen:
                continue
            seen.add(xref_id)
            records.append(self.content_stream_record(document, xref_id, page_number, "xobject", index, xobject))
        return {
            "page": page_number,
            "streamCount": len(records),
            "textStreamCount": len([item for item in records if item.get("containsTextBlock")]),
            "streams": records,
        }

    def content_stream_record(self, document: Any, xref: int, page_number: int, kind: str, index: int, xobject: Any = None) -> dict[str, Any]:
        stream = document.xref_stream(xref) or b""
        decoded = decoded_stream_text(stream)
        text = decoded["text"]
        operator_counts = pdf_operator_counts(text)
        record = {
            "id": f"p{page_number:04d}-{kind}-{index:05d}-x{xref}",
            "page": page_number,
            "kind": kind,
            "xref": xref,
            "sizeBytes": len(stream),
            "sha256": sha256_bytes(stream),
            "encoding": decoded["encoding"],
            "containsTextBlock": operator_counts.get("BT", 0) > 0 and operator_counts.get("ET", 0) > 0,
            "operatorCounts": operator_counts,
            "xrefObject": document.xref_object(xref, compressed=False),
            "decodedText": text,
        }
        if isinstance(xobject, (list, tuple)):
            record["xobject"] = {
                "name": str(xobject[1]) if len(xobject) > 1 else "",
                "invoker": str(xobject[2]) if len(xobject) > 2 else "",
                "bbox": rect_value(xobject[3]) if len(xobject) > 3 else None,
            }
        return record

    def extract_reference_paths(self, page: Any, page_number: int) -> list[dict[str, Any]]:
        records = []
        for index, drawing in enumerate(page.get_drawings() or []):
            records.append({
                "type": "path",
                "usage": "reference-only",
                "id": f"p{page_number:04d}-ref-path-{index:05d}",
                "page": page_number,
                "order": int_value(drawing.get("seqno"), index),
                "rect": rect_state(drawing.get("rect")),
                "items": [serialize_path_item(item) for item in drawing.get("items", [])],
                "stroke": color_value(drawing.get("color")),
                "fill": color_value(drawing.get("fill")),
                "width": float_value(drawing.get("width"), 1.0),
                "dashes": str(drawing.get("dashes") or ""),
                "lineCap": drawing.get("lineCap"),
                "lineJoin": drawing.get("lineJoin"),
                "closePath": bool(drawing.get("closePath")),
                "evenOdd": bool(drawing.get("even_odd")),
                "strokeOpacity": float_value(drawing.get("stroke_opacity"), 1.0),
                "fillOpacity": float_value(drawing.get("fill_opacity"), 1.0),
                "layer": drawing.get("layer"),
                "rawType": drawing.get("type"),
            })
        return records

    def extract_reference_images(self, document: Any, page: Any, page_number: int) -> list[dict[str, Any]]:
        records = []
        seen: set[tuple[int, str]] = set()
        for index, image in enumerate(page.get_image_info(xrefs=True) or []):
            xref = int_value(image.get("xref"), 0)
            rect = image.get("bbox")
            identity = (xref, str(rect))
            if xref <= 0 or identity in seen:
                continue
            seen.add(identity)
            extracted = document.extract_image(xref)
            image_bytes = extracted.get("image") or b""
            ext = str(extracted.get("ext") or "png")
            image_path = self.reference_image_dir / f"p{page_number:04d}-x{xref}-{index:05d}.{ext}"
            image_path.write_bytes(image_bytes)
            records.append({
                "type": "image",
                "usage": "reference-only",
                "id": f"p{page_number:04d}-ref-image-{index:05d}",
                "page": page_number,
                "order": int_value(image.get("number"), index),
                "xref": xref,
                "rect": rect_state(rect),
                "transform": [float_value(item) for item in image.get("transform", [])] if image.get("transform") else None,
                "width": int_value(extracted.get("width") or image.get("width"), 0),
                "height": int_value(extracted.get("height") or image.get("height"), 0),
                "colorspace": str(extracted.get("colorspace") or image.get("cs-name") or ""),
                "bitsPerComponent": extracted.get("bpc"),
                "extension": ext,
                "sizeBytes": len(image_bytes),
                "sha256": sha256_bytes(image_bytes),
                "imagePath": str(image_path.relative_to(self.job_dir)),
            })
        return records

    def extract_reference_tables(self, page: Any, page_number: int) -> list[dict[str, Any]]:
        finder = getattr(page, "find_tables", None)
        if not callable(finder):
            return []
        try:
            table_result = finder()
        except Exception:
            return []
        tables = getattr(table_result, "tables", None) or []
        records = []
        for index, table in enumerate(tables):
            bbox = getattr(table, "bbox", None)
            cells = getattr(table, "cells", None) or []
            records.append({
                "type": "table",
                "usage": "reference-only",
                "id": f"p{page_number:04d}-ref-table-{index:05d}",
                "page": page_number,
                "order": 200000 + index,
                "rect": rect_state(bbox),
                "rowCount": int_value(getattr(table, "row_count", 0), 0),
                "columnCount": int_value(getattr(table, "col_count", 0), 0),
                "cells": [rect_state(cell) for cell in cells if cell is not None],
            })
        return records

    def extract_text_objects(self, page: Any, page_number: int) -> list[dict[str, Any]]:
        records = []
        text_dict = page.get_text("rawdict") or {}
        for block_index, block in enumerate(text_dict.get("blocks", [])):
            if block.get("type") != 0:
                continue
            for line_index, line in enumerate(block.get("lines", [])):
                line_direction = point_value(line.get("dir") or [1.0, 0.0])
                for span_index, span in enumerate(line.get("spans", [])):
                    chars = [serialize_char(char) for char in span.get("chars", []) if str(char.get("c") or "")]
                    text = str(span.get("text") or text_from_chars(chars))
                    if not text.strip() or is_unusable_extracted_text(text):
                        continue
                    origin = point_value(span.get("origin") or (chars[0].get("origin") if chars else None))
                    text_state = {
                        "font": str(span.get("font") or ""),
                        "size": float_value(span.get("size"), 10.0),
                        "color": color_value(span.get("color")) or [0.0, 0.0, 0.0],
                        "alpha": float_value(span.get("alpha"), 1.0),
                        "origin": origin,
                        "lineDirection": line_direction,
                        "rotation": line_rotation(line_direction),
                        "writingMode": int_value(line.get("wmode"), 0),
                        "flags": int_value(span.get("flags"), 0),
                        "charFlags": int_value(span.get("char_flags"), 0),
                        "ascender": float_value(span.get("ascender"), 0.0),
                        "descender": float_value(span.get("descender"), 0.0),
                    }
                    record = {
                        "type": "text",
                        "id": f"p{page_number:04d}-text-{len(records):05d}",
                        "page": page_number,
                        "order": int_value(span.get("seqno"), 100000 + len(records)),
                        "rect": rect_state(span.get("bbox")),
                        "source": text,
                        "text": text,
                        "textState": text_state,
                        "block": block_index,
                        "line": line_index,
                        "span": span_index,
                        "styleModel": self.derive_style_model(text_state),
                    }
                    if self.config.keep_char_state:
                        record["chars"] = chars
                    records.append(record)
        return records

    def derive_style_model(self, text_state: dict[str, Any]) -> dict[str, Any]:
        flags = int_value(text_state.get("flags"), 0)
        char_flags = int_value(text_state.get("charFlags"), 0)
        font = str(text_state.get("font") or "").lower()
        return {
            "bold": bool(flags & 16) or "bold" in font,
            "italic": bool(flags & 2) or "italic" in font or "oblique" in font,
            "serif": bool(flags & 4),
            "monospace": bool(flags & 8),
            "underline": bool(char_flags & 2),
            "strikeout": bool(char_flags & 1),
            "syntheticBoldCandidate": bool(char_flags & 4),
        }

    def step_03_translate_text_state(self) -> None:
        state = read_json(self.state_path, {})
        pages = state.get("pages", [])
        text_items = [obj for page in pages for obj in self.page_text_objects(page)]
        cache_path = self.config.work_dir / "translation-cache.json"
        cache = read_json(cache_path, {})
        pending: list[dict[str, Any]] = []
        cached_count = 0
        skipped_count = 0
        text_total = len(text_items)
        self.log_progress("03_translate_text_state", 0, text_total, "scan cache and build pending list")
        for index, item in enumerate(text_items, start=1):
            source = str(item.get("source") or item.get("text") or "")
            item["source"] = source
            cache_key = self.translation_cache_key(source)
            if cache_key in cache:
                self.apply_translation(item, str(cache[cache_key]), "cached")
                cached_count += 1
            elif not self.should_translate_text(source):
                self.apply_translation(item, source, "source-copy")
                cache[cache_key] = source
                skipped_count += 1
            else:
                pending.append(item)
            if index == text_total or index % 500 == 0:
                self.log_progress(
                    "03_translate_text_state",
                    index,
                    text_total,
                    f"cache scan: pending={len(pending)}, cached={cached_count}, skipped={skipped_count}",
                    pending=len(pending),
                    cached=cached_count,
                    skipped=skipped_count,
                )
        chunks = self.build_translation_chunks(pages, pending)
        write_json(self.state_dir / "translation-input.json", {
            "createdAt": now_iso(),
            "purpose": "human-readable OpenAI translation input generated from text-state JSON",
            "sourceLang": self.config.source_lang,
            "targetLang": self.config.target_lang,
            "textCount": len(text_items),
            "pendingCount": len(pending),
            "cachedCount": cached_count,
            "skippedCount": skipped_count,
            "items": [self.translation_input_item(item) for item in pending],
        })
        write_json(self.state_dir / "translation-chunks.json", {"createdAt": now_iso(), "chunkCount": len(chunks), "chunks": [self.serializable_translation_chunk(chunk) for chunk in chunks]})
        if pending and not self.config.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI translation")
        translated_count = 0
        chunk_results = []
        chunk_total = len(chunks)
        self.log_progress("03_translate_text_state", 0, chunk_total, f"translate chunks: pending={len(pending)}", pending=len(pending), cached=cached_count, skipped=skipped_count)
        for chunk_index, chunk in enumerate(chunks, start=1):
            translations = self.translate_openai_chunk(chunk)
            translations = self.retry_missing_translations(chunk, translations)
            chunk_result = self.translation_result_summary(chunk, translations)
            chunk_results.append(chunk_result)
            for item in chunk["sourceItems"]:
                source = str(item.get("source") or item.get("text") or "")
                translated = translations.get(str(item.get("id")), source)
                status = "translated" if str(item.get("id")) in translations else "missing-translation"
                if translated == source and status == "translated":
                    status = "source-copy"
                self.apply_translation(item, translated, status)
                cache[self.translation_cache_key(source)] = translated
                translated_count += 1
            write_json(cache_path, cache)
            write_json(self.state_dir / "translation-results.json", {"updatedAt": now_iso(), "chunkCount": len(chunk_results), "chunks": chunk_results})
            write_json(self.state_dir / "translation-progress.json", {"status": "running", "completed": translated_count, "pending": len(pending), "cached": cached_count, "skipped": skipped_count, "total": len(text_items), "updatedAt": now_iso()})
            self.log_progress(
                "03_translate_text_state",
                chunk_index,
                chunk_total,
                f"chunk {chunk['chunkId']}: translated={translated_count}/{len(pending)}",
                translated=translated_count,
                pending=len(pending),
                cached=cached_count,
                skipped=skipped_count,
                chunkId=chunk["chunkId"],
            )
        state["translation"] = {
            "provider": "openai",
            "model": self.config.openai_model,
            "sourceLang": self.config.source_lang,
            "targetLang": self.config.target_lang,
            "updatedAt": now_iso(),
            "textCount": len(text_items),
            "chunkCount": len(chunks),
            "translatedCount": translated_count,
            "cachedCount": cached_count,
            "skippedCount": skipped_count,
            "maxChunkChars": self.config.max_chunk_chars,
            "maxChunkItems": self.config.max_chunk_items,
        }
        write_json(cache_path, cache)
        write_json(self.state_dir / "translation-results.json", {"updatedAt": now_iso(), "chunkCount": len(chunk_results), "chunks": chunk_results})
        write_json(self.state_dir / "translation-progress.json", {"status": "completed", "completed": translated_count, "pending": len(pending), "cached": cached_count, "skipped": skipped_count, "total": len(text_items), "updatedAt": now_iso()})
        write_json(self.state_path, state)
        self.write_text_state_json(state, self.state_dir / "translated-text-state.json", "translated")

    def apply_translation(self, item: dict[str, Any], translated: str, status: str) -> None:
        item["text"] = translated
        item.pop("translated", None)
        item["translationStatus"] = status

    def should_translate_text(self, text: str) -> bool:
        value = text.strip()
        if not value:
            return False
        if re.fullmatch(r"[\W\d_]+", value, flags=re.UNICODE):
            return False
        if re.fullmatch(r"https?://\S+|www\.\S+|\S+@\S+", value, flags=re.IGNORECASE):
            return False
        return any(char.isalpha() for char in value)

    def translation_cache_key(self, text: str) -> str:
        raw = json.dumps({"sourceLang": self.config.source_lang, "targetLang": self.config.target_lang, "model": self.config.openai_model, "text": text}, ensure_ascii=False, sort_keys=True)
        return sha256_bytes(raw.encode("utf-8"))

    def translation_input_item(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(item.get("id") or ""),
            "page": int_value(item.get("page"), 0),
            "source": str(item.get("source") or item.get("text") or ""),
            "rect": item.get("rect"),
            "textState": item.get("textState"),
        }

    def build_translation_chunks(self, pages: list[dict[str, Any]], pending: list[dict[str, Any]]) -> list[dict[str, Any]]:
        pending_ids = {str(item.get("id")) for item in pending}
        chunks = []
        chunk_items: list[dict[str, str]] = []
        source_items: list[dict[str, Any]] = []
        chunk_chars = 0
        chunk_index = 1
        for page in pages:
            page_number = int_value(page.get("page"), 0)
            for item in self.page_text_objects(page):
                if str(item.get("id")) not in pending_ids:
                    continue
                source = str(item.get("source") or item.get("text") or "")
                item_payload = {"id": str(item.get("id")), "text": source}
                next_chars = chunk_chars + len(source)
                if chunk_items and (len(chunk_items) >= self.config.max_chunk_items or next_chars > self.config.max_chunk_chars):
                    chunks.append(self.make_translation_chunk(chunk_index, page_number, chunk_items, source_items, chunk_chars))
                    chunk_index += 1
                    chunk_items = []
                    source_items = []
                    chunk_chars = 0
                chunk_items.append(item_payload)
                source_items.append(item)
                chunk_chars += len(source)
        if chunk_items:
            last_page = int_value(source_items[-1].get("page"), 0) if source_items else 0
            chunks.append(self.make_translation_chunk(chunk_index, last_page, chunk_items, source_items, chunk_chars))
        return chunks

    def make_translation_chunk(self, index: int, page_number: int, items: list[dict[str, str]], source_items: list[dict[str, Any]], char_count: int) -> dict[str, Any]:
        return {
            "chunkId": f"chunk-{index:05d}",
            "page": page_number,
            "itemCount": len(items),
            "charCount": char_count,
            "items": items,
            "sourceItems": source_items,
        }

    def serializable_translation_chunk(self, chunk: dict[str, Any]) -> dict[str, Any]:
        if self.config.keep_translation_chunks:
            return {key: value for key, value in chunk.items() if key != "sourceItems"}
        return {
            "chunkId": chunk["chunkId"],
            "page": chunk["page"],
            "itemCount": chunk["itemCount"],
            "charCount": chunk["charCount"],
            "itemIds": [str(item.get("id")) for item in chunk["items"]],
        }

    def translation_result_summary(self, chunk: dict[str, Any], translations: dict[str, str]) -> dict[str, Any]:
        if self.config.keep_translation_results:
            return {"chunkId": chunk["chunkId"], "itemCount": len(chunk["items"]), "translations": translations}
        missing = [str(item.get("id")) for item in chunk["items"] if str(item.get("id")) not in translations]
        return {"chunkId": chunk["chunkId"], "itemCount": len(chunk["items"]), "translatedCount": len(translations), "missingIds": missing}

    def page_text_objects(self, page_def: dict[str, Any]) -> list[dict[str, Any]]:
        text_objects = page_def.get("textObjects")
        if isinstance(text_objects, list):
            return [item for item in text_objects if isinstance(item, dict) and item.get("type") == "text"]
        objects = page_def.get("objects")
        if isinstance(objects, list):
            return [item for item in objects if isinstance(item, dict) and item.get("type") == "text"]
        return []

    def translate_openai_chunk(self, chunk: dict[str, Any]) -> dict[str, str]:
        from openai import OpenAI  # type: ignore

        payload = {"chunkId": chunk["chunkId"], "items": chunk["items"]}
        source_lang = language_label(self.config.source_lang)
        target_lang = language_label(self.config.target_lang)
        client = OpenAI(api_key=self.config.openai_api_key, timeout=90.0, max_retries=1)
        response = client.chat.completions.create(
            model=self.config.openai_model,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Translate every item from {source_lang} to {target_lang}. "
                        "Preserve numbers, product names, file names, URLs, and line breaks where possible. "
                        "Return only a JSON array. Each array item must have id and translated fields. "
                        "Do not add, remove, rename, or skip ids. Do not return Markdown."
                    ),
                },
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        )
        content = (response.choices[0].message.content or "{}").strip()
        content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\s*```$", "", content)
        parsed = json.loads(content or "{}")
        if isinstance(parsed, list):
            return {str(item.get("id")): str(item.get("translated") or item.get("text") or "") for item in parsed if isinstance(item, dict) and item.get("id")}
        if isinstance(parsed, dict):
            if isinstance(parsed.get("items"), list):
                return {str(item.get("id")): str(item.get("translated") or item.get("text") or "") for item in parsed["items"] if isinstance(item, dict) and item.get("id")}
            return {str(key): str(value) for key, value in parsed.items()}
        return {}

    def retry_missing_translations(self, chunk: dict[str, Any], translations: dict[str, str]) -> dict[str, str]:
        missing = [item for item in chunk["items"] if not str(translations.get(str(item.get("id")), "")).strip()]
        if not missing:
            return translations
        retry_chunk = {
            "chunkId": f"{chunk['chunkId']}-retry",
            "items": missing,
        }
        self.log(f"WARN translation retry {chunk['chunkId']}: missing={len(missing)}")
        retry_translations = self.translate_openai_chunk(retry_chunk)
        for item_id, translated in retry_translations.items():
            if translated.strip():
                translations[item_id] = translated
        return translations

    def step_04_build_pdf_from_state(self) -> None:
        state = read_json(self.state_path, {})
        if self.effective_build_mode(state) == "exact":
            self.build_exact_pdf(state)
        else:
            self.build_semantic_pdf(state)

    def effective_build_mode(self, state: dict[str, Any]) -> str:
        if state.get("translation"):
            return "semantic"
        return self.config.build_mode

    def build_exact_pdf(self, state: dict[str, Any]) -> None:
        self.log_progress("04_build_pdf_from_state", 0, 1, "restore source bytes")
        data = self.source_bytes_from_state(state)
        actual_hash = sha256_bytes(data)
        target = self.pdf_dir / "draft.pdf"
        ensure_dir(target.parent)
        target.write_bytes(data)
        write_json(self.state_dir / "build-report.json", {"status": "ok", "mode": "exact", "sha256": actual_hash, "output": str(target.relative_to(self.job_dir)), "recordedAt": now_iso()})
        self.log_progress("04_build_pdf_from_state", 1, 1, "exact PDF written")

    def build_semantic_pdf(self, state: dict[str, Any]) -> None:
        import fitz  # type: ignore

        target = self.pdf_dir / "draft.pdf"
        source_bytes = self.source_bytes_from_state(state)
        output = fitz.open(stream=source_bytes, filetype="pdf")
        pages = list(state.get("pages", []))
        page_total = len(pages)
        input_results = []
        self.log_progress("04_build_pdf_from_state", 0, page_total, "rewrite text state")
        for page_position, page_def in enumerate(pages, start=1):
            page_index = int_value(page_def.get("page"), 1) - 1
            if page_index < 0 or page_index >= len(output):
                self.log_progress("04_build_pdf_from_state", page_position, page_total, f"skip page index {page_index}")
                continue
            page = output[page_index]
            self.remove_page_text_streams(output, page)
            text_objects = sorted(self.page_text_objects(page_def), key=lambda item: int_value(item.get("order"), 0))
            page_results = []
            for obj in text_objects:
                page_results.append(self.draw_text_object(page, obj))
            written_count = len([item for item in page_results if item.get("status") == "written"])
            failed_count = len([item for item in page_results if item.get("status") != "written"])
            input_results.append({"page": page_position, "textCount": len(text_objects), "writtenCount": written_count, "failedCount": failed_count, "items": page_results})
            self.log_progress("04_build_pdf_from_state", page_position, page_total, f"page {page_position}: written={written_count}, failed={failed_count}")
        ensure_dir(target.parent)
        self.log_progress("04_build_pdf_from_state", page_total, page_total, "saving PDF")
        output.save(target, garbage=4, deflate=True, clean=True)
        output.close()
        write_json(self.state_dir / "build-report.json", {"status": "ok", "mode": "semantic", "source": "source.bytesBase64", "textSource": "textObjects", "output": str(target.relative_to(self.job_dir)), "recordedAt": now_iso()})
        write_json(self.state_dir / "text-input-report.json", {"createdAt": now_iso(), "method": "insert_textbox", "pageCount": len(input_results), "pages": input_results})

    def remove_page_text_streams(self, document: Any, page: Any) -> None:
        xrefs = {int_value(xref) for xref in (page.get_contents() or []) if int_value(xref) > 0}
        for xobject in page.get_xobjects() or []:
            if isinstance(xobject, (list, tuple)) and xobject:
                xref = int_value(xobject[0])
                if xref > 0:
                    xrefs.add(xref)
        for xref in sorted(xrefs):
            stream = document.xref_stream(xref) or b""
            if not stream:
                continue
            stripped = re.sub(rb"\bBT\b.*?\bET\b", b"", stream, flags=re.DOTALL)
            if stripped != stream:
                document.update_stream(xref, stripped)

    def source_bytes_from_state(self, state: dict[str, Any]) -> bytes:
        source = state.get("source") or {}
        encoded = str(source.get("bytesBase64") or "")
        if not encoded:
            raise ValueError("pdf-state.json does not contain source.bytesBase64")
        data = base64.b64decode(encoded)
        expected_hash = str(source.get("sha256") or "")
        actual_hash = sha256_bytes(data)
        if expected_hash and expected_hash != actual_hash:
            raise ValueError("source bytes hash mismatch")
        return data

    def resolve_text_font_file(self) -> str:
        if self._resolved_text_font_file is not None:
            return self._resolved_text_font_file
        candidates = []
        if self.config.text_font_file:
            configured = Path(self.config.text_font_file)
            candidates.append(configured if configured.is_absolute() else self.config.base_dir / configured)
        candidates.extend([
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
            Path("/mnt/c/Windows/Fonts/malgun.ttf"),
            Path("C:/Windows/Fonts/malgun.ttf"),
            Path("C:/Windows/Fonts/arial.ttf"),
        ])
        for candidate in candidates:
            if candidate.exists():
                self._resolved_text_font_file = str(candidate)
                return self._resolved_text_font_file
        self._resolved_text_font_file = ""
        return self._resolved_text_font_file

    def font_kwargs_for_text(self, state: dict[str, Any], text: str) -> dict[str, Any]:
        font_file = self.resolve_text_font_file()
        if font_file:
            return {"fontname": "v8text", "fontfile": font_file}
        font = str(state.get("font") or "").lower()
        if "cour" in font or "mono" in font:
            return {"fontname": "cour"}
        if "times" in font or "georgia" in font or "serif" in font:
            return {"fontname": "tiro"}
        return {"fontname": "helv"}

    def draw_text_object(self, page: Any, obj: dict[str, Any]) -> dict[str, Any]:
        import fitz  # type: ignore

        text = str(obj.get("text") or obj.get("source") or "")
        if not text:
            return {"id": str(obj.get("id") or ""), "status": "skipped", "reason": "empty text"}
        state = obj.get("textState") or {}
        font_size = max(1.0, float_value(state.get("size"), 10.0))
        rotate = int_value(state.get("rotation"), 0)
        params: dict[str, Any] = {
            "fontsize": font_size,
            "color": tuple(state.get("color") or [0, 0, 0]),
            "rotate": rotate,
            "overlay": True,
        }
        alpha = float_value(state.get("alpha"), 1.0)
        if alpha < 1.0:
            params["fill_opacity"] = alpha
        params.update(self.font_kwargs_for_text(state, text))
        rect = object_rect_value(obj.get("rect"))
        if not is_valid_rect(rect):
            return {"id": str(obj.get("id") or ""), "status": "skipped", "reason": "invalid rect"}
        boxes = [
            fitz.Rect(rect[0], rect[1], min(page.rect.x1, rect[2] + font_size * 2), min(page.rect.y1, rect[3] + font_size * 1.5)),
            fitz.Rect(rect[0], rect[1], page.rect.x1, min(page.rect.y1, rect[3] + font_size * 3)),
            fitz.Rect(rect[0], rect[1], page.rect.x1, page.rect.y1),
        ]
        for box_index, box in enumerate(boxes):
            for scale in (1.0, 0.92, 0.84, 0.76, 0.68, 0.6):
                trial = dict(params)
                trial["fontsize"] = max(4.0, font_size * scale)
                remaining = page.insert_textbox(box, text, **trial)
                if remaining is None or remaining >= 0:
                    return {"id": str(obj.get("id") or ""), "status": "written", "method": "insert_textbox", "boxIndex": box_index, "fontScale": scale}
        return {"id": str(obj.get("id") or ""), "status": "failed", "reason": "textbox overflow"}

    def step_05_publish_output(self) -> None:
        source = self.pdf_dir / "draft.pdf"
        state = read_json(self.state_path, {})
        output_name = safe_stem(Path(str((state.get("source") or {}).get("name") or "document.pdf")))
        suffix = "exact" if self.effective_build_mode(state) == "exact" else "semantic"
        target = self.config.output_dir / f"{output_name}_V8_{suffix}.pdf"
        ensure_dir(target.parent)
        self.log_progress("05_publish_output", 0, 1, "copy draft to output")
        shutil.copyfile(source, target)
        write_json(self.state_dir / "publish-report.json", {"status": "ok", "output": str(target), "recordedAt": now_iso()})
        self.log_progress("05_publish_output", 1, 1, str(target))


def main(argv: list[str]) -> int:
    base_dir = Path(__file__).resolve().parents[2]
    args = parse_args(argv)
    config = load_config(base_dir, args)
    try:
        state_path = Path(args.state).resolve() if args.state else None
        if state_path and not state_path.exists():
            raise FileNotFoundError(f"State file does not exist: {state_path}")
        source_pdf = None if state_path else resolve_source_pdf(config, args.pdf)
        Pipeline(config, source_pdf, state_path, bool(args.extract_only)).run()
        return 0
    except FileNotFoundError as error:
        print(f"[error] {error}", file=sys.stderr)
        return 2
    except ValueError as error:
        print(f"[error] {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
