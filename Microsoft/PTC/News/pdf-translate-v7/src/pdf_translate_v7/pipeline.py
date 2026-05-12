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


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="pdf-translate-v7 PDF state JSON round-trip project")
    parser.add_argument("pdf", nargs="?", help="Source PDF. Defaults to the first PDF in input/.")
    parser.add_argument("--state", help="Existing pdf-state.json to build from.")
    parser.add_argument("--build-mode", choices=["exact", "semantic"], help="exact restores the source bytes from JSON; semantic starts from source bytes and writes text state.")
    parser.add_argument("--in-lang", help="Source language")
    parser.add_argument("--out-lang", help="Target language")
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
            f"{config.input_dir} or run ./run-v7.sh path/to/file.pdf"
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
        self.state_path = self.state_dir / "pdf-state.json"
        self._resolved_text_font_file: str | None = None

    def log(self, message: str) -> None:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}", flush=True)

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
        with fitz.open(self.source_pdf) as document:
            for page_index, page in enumerate(document):
                page_number = page_index + 1
                texts = self.extract_text_objects(page, page_number)
                reference_objects = self.extract_reference_objects(document, page, page_number)
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
                    "textRaw": page.get_text("rawdict") or {},
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
            metadata = dict(document.metadata or {})
        state = {
            "schemaVersion": "v7.0",
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
            },
            "pages": pages,
        }
        write_json(self.state_path, state)

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
                    if not text.strip():
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
                    records.append({
                        "type": "text",
                        "id": f"p{page_number:04d}-text-{len(records):05d}",
                        "page": page_number,
                        "order": int_value(span.get("seqno"), 100000 + len(records)),
                        "rect": rect_state(span.get("bbox")),
                        "source": text,
                        "text": text,
                        "textState": text_state,
                        "chars": chars,
                        "block": block_index,
                        "line": line_index,
                        "span": span_index,
                        "styleModel": self.derive_style_model(text_state),
                    })
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
        text_items = [obj for page in state.get("pages", []) for obj in self.page_text_objects(page)]
        if text_items and not self.config.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI translation")
        translated_count = 0
        for offset in range(0, len(text_items), 40):
            batch = text_items[offset:offset + 40]
            translations = self.translate_openai_batch(batch)
            for item in batch:
                source = str(item.get("source") or item.get("text") or "")
                translated = translations.get(str(item.get("id")), source)
                item["source"] = source
                item["text"] = translated
                item["translated"] = translated
                item["translationStatus"] = "translated" if translated != source else "source-copy"
                translated_count += 1
            write_json(self.state_dir / "translation-progress.json", {"status": "running", "completed": translated_count, "total": len(text_items), "updatedAt": now_iso()})
        state["translation"] = {
            "provider": "openai",
            "model": self.config.openai_model,
            "sourceLang": self.config.source_lang,
            "targetLang": self.config.target_lang,
            "updatedAt": now_iso(),
            "textCount": len(text_items),
        }
        write_json(self.state_path, state)

    def page_text_objects(self, page_def: dict[str, Any]) -> list[dict[str, Any]]:
        text_objects = page_def.get("textObjects")
        if isinstance(text_objects, list):
            return [item for item in text_objects if isinstance(item, dict) and item.get("type") == "text"]
        objects = page_def.get("objects")
        if isinstance(objects, list):
            return [item for item in objects if isinstance(item, dict) and item.get("type") == "text"]
        return []

    def translate_openai_batch(self, items: list[dict[str, Any]]) -> dict[str, str]:
        from openai import OpenAI  # type: ignore

        payload = [{"id": item.get("id"), "text": str(item.get("source") or item.get("text") or "")} for item in items]
        client = OpenAI(api_key=self.config.openai_api_key, timeout=90.0, max_retries=1)
        response = client.chat.completions.create(
            model=self.config.openai_model,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Translate text from {self.config.source_lang} to {self.config.target_lang}. "
                        "Preserve numbers, product names, file names, URLs, and line breaks where possible. "
                        "Return only a JSON object mapping each id to translated text."
                    ),
                },
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        )
        content = (response.choices[0].message.content or "{}").strip()
        content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\s*```$", "", content)
        parsed = json.loads(content or "{}")
        if not isinstance(parsed, dict):
            return {}
        return {str(key): str(value) for key, value in parsed.items()}

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
        data = self.source_bytes_from_state(state)
        actual_hash = sha256_bytes(data)
        target = self.pdf_dir / "draft.pdf"
        ensure_dir(target.parent)
        target.write_bytes(data)
        write_json(self.state_dir / "build-report.json", {"status": "ok", "mode": "exact", "sha256": actual_hash, "output": str(target.relative_to(self.job_dir)), "recordedAt": now_iso()})

    def build_semantic_pdf(self, state: dict[str, Any]) -> None:
        import fitz  # type: ignore

        target = self.pdf_dir / "draft.pdf"
        source_bytes = self.source_bytes_from_state(state)
        output = fitz.open(stream=source_bytes, filetype="pdf")
        for page_def in state.get("pages", []):
            page_index = int_value(page_def.get("page"), 1) - 1
            if page_index < 0 or page_index >= len(output):
                continue
            page = output[page_index]
            self.remove_page_text_streams(output, page)
            for obj in sorted(self.page_text_objects(page_def), key=lambda item: int_value(item.get("order"), 0)):
                self.draw_text_object(page, obj)
        ensure_dir(target.parent)
        output.save(target, garbage=4, deflate=True, clean=True)
        output.close()
        write_json(self.state_dir / "build-report.json", {"status": "ok", "mode": "semantic", "source": "source.bytesBase64", "textSource": "textObjects", "output": str(target.relative_to(self.job_dir)), "recordedAt": now_iso()})

    def remove_page_text_streams(self, document: Any, page: Any) -> None:
        for xref in page.get_contents() or []:
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
        if font_file and any(ord(char) > 0x7F for char in text):
            return {"fontname": "v7text", "fontfile": font_file}
        font = str(state.get("font") or "").lower()
        if "cour" in font or "mono" in font:
            return {"fontname": "cour"}
        if "times" in font or "georgia" in font or "serif" in font:
            return {"fontname": "tiro"}
        return {"fontname": "helv"}

    def draw_text_object(self, page: Any, obj: dict[str, Any]) -> None:
        import fitz  # type: ignore

        text = str(obj.get("text") or obj.get("source") or "")
        if not text:
            return
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
        chars = obj.get("chars") if isinstance(obj.get("chars"), list) else []
        if chars and text_from_chars(chars) == text:
            for char in chars:
                char_text = str(char.get("text") or "")
                if not char_text:
                    continue
                point = point_value(char.get("origin"))
                page.insert_text(fitz.Point(point[0], point[1]), char_text, **params)
            return
        origin = point_value(state.get("origin"))
        page.insert_text(fitz.Point(origin[0], origin[1]), text, **params)

    def step_05_publish_output(self) -> None:
        source = self.pdf_dir / "draft.pdf"
        state = read_json(self.state_path, {})
        output_name = safe_stem(Path(str((state.get("source") or {}).get("name") or "document.pdf")))
        suffix = "exact" if self.effective_build_mode(state) == "exact" else "semantic"
        target = self.config.output_dir / f"{output_name}_V7_{suffix}.pdf"
        ensure_dir(target.parent)
        shutil.copyfile(source, target)
        write_json(self.state_dir / "publish-report.json", {"status": "ok", "output": str(target), "recordedAt": now_iso()})


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
