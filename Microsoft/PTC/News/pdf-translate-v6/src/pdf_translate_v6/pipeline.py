from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STEP_ORDER = [
    "01_init_job",
    "02_extract_object_manifest",
    "03_translate_text_objects",
    "04_build_pdf_from_manifest",
    "05_publish_output",
]


@dataclass
class Config:
    base_dir: Path
    input_dir: Path
    output_dir: Path
    work_dir: Path
    source_lang: str
    target_lang: str
    translation_mode: str
    openai_api_key: str
    openai_model: str
    min_font_size: float
    max_shrink_steps: int
    text_font_file: str


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


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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
    parser = argparse.ArgumentParser(description="pdf-translate-v6 object-manifest PDF translator")
    parser.add_argument("pdf", nargs="?", help="Source PDF. Defaults to the first PDF in input/.")
    parser.add_argument("--translation-mode", choices=["copy", "openai"], help="Translation provider")
    parser.add_argument("--in-lang", help="Source language")
    parser.add_argument("--out-lang", help="Target language")
    parser.add_argument("--keep-work", action="store_true", help="Keep work directory. Currently always kept for manifest debugging.")
    return parser.parse_args(argv)


def load_config(base_dir: Path, args: argparse.Namespace) -> Config:
    load_env_file(base_dir / ".env")
    return Config(
        base_dir=base_dir,
        input_dir=base_dir / "input",
        output_dir=base_dir / "output",
        work_dir=base_dir / "work",
        source_lang=args.in_lang or env("SOURCE_LANG", "en"),
        target_lang=args.out_lang or env("TARGET_LANG", "ko"),
        translation_mode=args.translation_mode or env("TRANSLATION_MODE", "copy"),
        openai_api_key=env("OPENAI_API_KEY"),
        openai_model=env("OPENAI_MODEL", "gpt-4.1-mini"),
        min_font_size=float(env("FIT_TEXT_MIN_FONT_SIZE", "4") or 4),
        max_shrink_steps=int(env("FIT_TEXT_MAX_SHRINK_STEPS", "16") or 16),
        text_font_file=env("TEXT_FONT_FILE") or env("PDF_TEXT_FONT_FILE") or env("PDF_CJK_FONT_FILE"),
    )


def resolve_source_pdf(config: Config, value: str | None) -> Path:
    if value:
        path = Path(value)
        if not path.is_absolute():
            path = config.base_dir / path
        return path.resolve()
    candidates = sorted(config.input_dir.glob("*.pdf"))
    if not candidates:
        raise FileNotFoundError("No source PDF found. Put a PDF in input/ or pass a path.")
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


def color_value(value: Any) -> list[float] | None:
    if value is None:
        return None
    if isinstance(value, int):
        return [((value >> 16) & 255) / 255, ((value >> 8) & 255) / 255, (value & 255) / 255]
    if isinstance(value, (list, tuple)):
        return [float(item) for item in value[:3]]
    return None


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def float_value(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
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
    return "".join(str(char.get("c") or "") for char in chars)


def serialize_char(char: dict[str, Any]) -> dict[str, Any]:
    return {
        "c": str(char.get("c") or ""),
        "origin": point_value(char.get("origin")),
        "bbox": bbox_dict(char.get("bbox")),
    }


def serialize_path_item(item: Any) -> dict[str, Any]:
    op = str(item[0]) if isinstance(item, (list, tuple)) and item else "unknown"
    values = list(item[1:]) if isinstance(item, (list, tuple)) else []
    if op == "re" and values:
        return {"op": op, "rect": rect_value(values[0]), "orientation": int(values[1]) if len(values) > 1 and isinstance(values[1], int) else None}
    if op in {"m", "l"}:
        return {"op": op, "points": [point_value(value) for value in values]}
    if op == "c":
        return {"op": op, "points": [point_value(value) for value in values]}
    if op == "qu" and values:
        return {"op": op, "quad": [point_value(point) for point in values[0]] if isinstance(values[0], (list, tuple)) else []}
    return {"op": op, "raw": str(item)}


def bbox_dict(value: Any) -> dict[str, float]:
    x0, y0, x1, y1 = rect_value(value)
    return {"x": x0, "y": y0, "width": max(0.0, x1 - x0), "height": max(0.0, y1 - y0), "left": x0, "top": y0, "right": x1, "bottom": y1}


def estimate_text_width(text: str, font_size: float) -> float:
    width = 0.0
    for char in text:
        if ord(char) > 0x3000:
            width += font_size
        elif char.isspace():
            width += font_size * 0.34
        else:
            width += font_size * 0.56
    return width


def wrap_text(text: str, width: float, font_size: float) -> list[str]:
    if not text:
        return [""]
    result: list[str] = []
    for paragraph in text.splitlines() or [text]:
        words = paragraph.split(" ")
        line = ""
        for word in words:
            candidate = word if not line else f"{line} {word}"
            if estimate_text_width(candidate, font_size) <= width or not line:
                line = candidate
            else:
                result.append(line)
                line = word
        if line:
            result.append(line)
    return result or [text]


class Pipeline:
    def __init__(self, config: Config, source_pdf: Path):
        self.config = config
        self.source_pdf = source_pdf
        self.job_id = f"{safe_stem(source_pdf)}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.job_dir = config.work_dir / self.job_id
        self.state_dir = self.job_dir / "state"
        self.object_dir = self.job_dir / "objects"
        self.image_dir = self.object_dir / "images"
        self.pdf_dir = self.job_dir / "pdf"
        self.tm_path = config.work_dir / "tm.sqlite"
        self.job_path = self.state_dir / "job.json"
        self._resolved_text_font_file: str | None = None

    def log(self, message: str) -> None:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}", flush=True)

    def run(self) -> None:
        for step in STEP_ORDER:
            self.log(f"START {step}")
            self.update_job(status="running", currentStep=step)
            getattr(self, f"step_{step}")()
            self.log(f"DONE  {step}")
        self.update_job(status="completed", currentStep=None)

    def initialize_dirs(self) -> None:
        for path in [self.state_dir, self.object_dir, self.image_dir, self.pdf_dir, self.config.output_dir, self.config.work_dir]:
            ensure_dir(path)

    def update_job(self, **updates: Any) -> None:
        state = read_json(self.job_path, {}) if self.job_path.exists() else {}
        state.update(updates)
        state["updatedAt"] = now_iso()
        write_json(self.job_path, state)

    def step_01_init_job(self) -> None:
        self.initialize_dirs()
        write_json(self.job_path, {
            "jobId": self.job_id,
            "sourcePdf": str(self.source_pdf),
            "sourceLang": self.config.source_lang,
            "targetLang": self.config.target_lang,
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
            "status": "created",
        })

    def step_02_extract_object_manifest(self) -> None:
        import fitz  # type: ignore

        pages = []
        with fitz.open(self.source_pdf) as document:
            for page_index, page in enumerate(document):
                page_number = page_index + 1
                drawings = self.extract_drawings(page, page_number)
                images = self.extract_images(document, page, page_number)
                texts = self.extract_text_spans(page, page_number)
                pages.append({
                    "page": page_number,
                    "width": float(page.rect.width),
                    "height": float(page.rect.height),
                    "objects": drawings + images + texts,
                    "counts": {"drawings": len(drawings), "images": len(images), "texts": len(texts)},
                })
        output = {"status": "ok", "sourcePdf": str(self.source_pdf), "pages": pages, "recordedAt": now_iso()}
        write_json(self.state_dir / "object-manifest.json", output)

    def extract_drawings(self, page: Any, page_number: int) -> list[dict[str, Any]]:
        records = []
        for index, drawing in enumerate(page.get_drawings() or []):
            records.append({
                "type": "path",
                "id": f"p{page_number:04d}-path-{index:05d}",
                "page": page_number,
                "order": int(drawing.get("seqno", index) or index),
                "bbox": bbox_dict(drawing.get("rect")),
                "items": [serialize_path_item(item) for item in drawing.get("items", [])],
                "stroke": color_value(drawing.get("color")),
                "fill": color_value(drawing.get("fill")),
                "width": float(drawing.get("width") or 1.0),
                "dashes": str(drawing.get("dashes") or ""),
                "lineCap": drawing.get("lineCap"),
                "lineJoin": drawing.get("lineJoin"),
                "closePath": bool(drawing.get("closePath")),
                "evenOdd": bool(drawing.get("even_odd")),
                "strokeOpacity": float(drawing.get("stroke_opacity", 1.0) or 1.0),
                "fillOpacity": float(drawing.get("fill_opacity", 1.0) or 1.0),
                "rawType": drawing.get("type"),
            })
        return records

    def extract_images(self, document: Any, page: Any, page_number: int) -> list[dict[str, Any]]:
        records = []
        seen: set[tuple[int, str]] = set()
        for index, image in enumerate(page.get_image_info(xrefs=True) or []):
            xref = int(image.get("xref") or 0)
            bbox = image.get("bbox")
            identity = (xref, str(bbox))
            if xref <= 0 or identity in seen:
                continue
            seen.add(identity)
            extracted = document.extract_image(xref)
            ext = str(extracted.get("ext") or "png")
            image_path = self.image_dir / f"p{page_number:04d}-x{xref}.{ext}"
            image_path.write_bytes(extracted.get("image") or b"")
            records.append({
                "type": "image",
                "id": f"p{page_number:04d}-image-{index:05d}",
                "page": page_number,
                "order": int(image.get("number", index) or index),
                "xref": xref,
                "bbox": bbox_dict(bbox),
                "width": int(extracted.get("width") or image.get("width") or 0),
                "height": int(extracted.get("height") or image.get("height") or 0),
                "colorspace": str(extracted.get("colorspace") or image.get("cs-name") or ""),
                "bitsPerComponent": extracted.get("bpc"),
                "imagePath": str(image_path.relative_to(self.job_dir)),
            })
        return records

    def extract_text_spans(self, page: Any, page_number: int) -> list[dict[str, Any]]:
        records = []
        text_dict = page.get_text("rawdict") or {}
        for block_index, block in enumerate(text_dict.get("blocks", [])):
            if block.get("type") != 0:
                continue
            for line_index, line in enumerate(block.get("lines", [])):
                for span_index, span in enumerate(line.get("spans", [])):
                    chars = [serialize_char(char) for char in span.get("chars", []) if str(char.get("c") or "")]
                    text = str(span.get("text") or text_from_chars(chars))
                    if not text.strip():
                        continue
                    origin = point_value(span.get("origin") or (chars[0].get("origin") if chars else None))
                    records.append({
                        "type": "text",
                        "id": f"p{page_number:04d}-text-{len(records):05d}",
                        "page": page_number,
                        "order": int(span.get("seqno", 100000 + len(records)) or 100000 + len(records)),
                        "bbox": bbox_dict(span.get("bbox")),
                        "source": text,
                        "translated": None,
                        "font": str(span.get("font") or ""),
                        "fontSize": float(span.get("size") or 10),
                        "color": color_value(span.get("color")) or [0.0, 0.0, 0.0],
                        "alpha": float_value(span.get("alpha"), 1.0),
                        "origin": origin,
                        "lineDirection": point_value(line.get("dir") or [1.0, 0.0]),
                        "writingMode": int_value(line.get("wmode"), 0),
                        "flags": int_value(span.get("flags"), 0),
                        "charFlags": int_value(span.get("char_flags"), 0),
                        "ascender": float_value(span.get("ascender"), 0.0),
                        "descender": float_value(span.get("descender"), 0.0),
                        "chars": chars,
                        "writeStrategy": "state-origin",
                        "block": block_index,
                        "line": line_index,
                        "span": span_index,
                    })
        return records

    def step_03_translate_text_objects(self) -> None:
        manifest = read_json(self.state_dir / "object-manifest.json", {})
        self.init_tm()
        text_items = [obj for page in manifest.get("pages", []) for obj in page.get("objects", []) if obj.get("type") == "text"]
        tm_hits = self.tm_get_many([item["source"] for item in text_items])
        api_items = []
        for item in text_items:
            cached = tm_hits.get(item["source"])
            if cached is not None:
                item["translated"] = cached
                item["translationStatus"] = "tm-hit"
            elif self.config.translation_mode == "openai" and self.config.openai_api_key:
                api_items.append(item)
            else:
                item["translated"] = item["source"]
                item["translationStatus"] = "source-copy"
        if api_items:
            for offset in range(0, len(api_items), 40):
                batch = api_items[offset:offset + 40]
                translations = self.translate_openai_batch(batch)
                rows = []
                for item in batch:
                    translated = translations.get(item["id"], item["source"])
                    item["translated"] = translated
                    item["translationStatus"] = "translated"
                    rows.append((item["source"], translated, self.config.openai_model))
                self.tm_put_many(rows)
                write_json(self.state_dir / "translated-progress.json", {"status": "running", "completed": offset + len(batch), "total": len(api_items), "recordedAt": now_iso()})
        write_json(self.state_dir / "translated-manifest.json", manifest)

    def init_tm(self) -> None:
        ensure_dir(self.tm_path.parent)
        with sqlite3.connect(self.tm_path) as database:
            database.execute("CREATE TABLE IF NOT EXISTS tm (src_hash TEXT PRIMARY KEY, src TEXT NOT NULL, tgt TEXT NOT NULL, model TEXT, source_lang TEXT, target_lang TEXT, created_at TEXT NOT NULL)")
            database.commit()

    def tm_key(self, source: str) -> str:
        return sha256_text(f"{self.config.source_lang}\n{self.config.target_lang}\n{source}")

    def tm_get_many(self, sources: list[str]) -> dict[str, str]:
        keys = {self.tm_key(source): source for source in sources}
        hits: dict[str, str] = {}
        with sqlite3.connect(self.tm_path) as database:
            for key, target in database.execute("SELECT src_hash, tgt FROM tm"):
                source = keys.get(key)
                if source is not None:
                    hits[source] = target
        return hits

    def tm_put_many(self, rows: list[tuple[str, str, str]]) -> None:
        if not rows:
            return
        with sqlite3.connect(self.tm_path) as database:
            database.executemany(
                "INSERT OR REPLACE INTO tm (src_hash, src, tgt, model, source_lang, target_lang, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [(self.tm_key(source), source, target, model, self.config.source_lang, self.config.target_lang, now_iso()) for source, target, model in rows],
            )
            database.commit()

    def translate_openai_batch(self, items: list[dict[str, Any]]) -> dict[str, str]:
        from openai import OpenAI  # type: ignore

        payload = [{"id": item["id"], "text": item["source"]} for item in items]
        client = OpenAI(api_key=self.config.openai_api_key, timeout=60.0, max_retries=0)
        response = client.chat.completions.create(
            model=self.config.openai_model,
            temperature=0,
            messages=[
                {"role": "system", "content": f"Translate from {self.config.source_lang} to {self.config.target_lang}. Return only a JSON object mapping id to translated text."},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        )
        content = (response.choices[0].message.content or "{}").strip()
        content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\s*```$", "", content)
        parsed = json.loads(content or "{}")
        return {str(key): str(value) for key, value in parsed.items()} if isinstance(parsed, dict) else {}

    def step_04_build_pdf_from_manifest(self) -> None:
        import fitz  # type: ignore

        manifest = read_json(self.state_dir / "translated-manifest.json", {})
        target = self.pdf_dir / "draft.pdf"
        output = fitz.open()
        for page_def in manifest.get("pages", []):
            page = output.new_page(width=float(page_def.get("width") or 612), height=float(page_def.get("height") or 792))
            objects = list(page_def.get("objects", []))
            for obj in sorted((item for item in objects if item.get("type") in {"path", "image"}), key=lambda item: int(item.get("order") or 0)):
                if obj.get("type") == "path":
                    self.draw_path_object(page, obj)
                elif obj.get("type") == "image":
                    self.draw_image_object(page, obj)
            for obj in sorted((item for item in objects if item.get("type") == "text"), key=lambda item: int(item.get("order") or 0)):
                self.draw_translated_text(page, obj)
        ensure_dir(target.parent)
        output.save(target, garbage=4, deflate=True, clean=True)
        output.close()
        write_json(self.state_dir / "build-report.json", {"status": "ok", "engine": "pymupdf-object-manifest", "output": str(target.relative_to(self.job_dir)), "recordedAt": now_iso()})

    def draw_path_object(self, page: Any, obj: dict[str, Any]) -> None:
        import fitz  # type: ignore

        shape = page.new_shape()
        for item in obj.get("items") or []:
            op = item.get("op")
            if op == "re":
                shape.draw_rect(fitz.Rect(*item.get("rect", [0, 0, 0, 0])))
            elif op == "l":
                points = item.get("points") or []
                if len(points) >= 2:
                    shape.draw_line(fitz.Point(*points[0]), fitz.Point(*points[1]))
            elif op == "c":
                points = item.get("points") or []
                if len(points) >= 4:
                    shape.draw_bezier(fitz.Point(*points[0]), fitz.Point(*points[1]), fitz.Point(*points[2]), fitz.Point(*points[3]))
        stroke = obj.get("stroke")
        fill = obj.get("fill")
        if not stroke and not fill:
            return
        shape.finish(
            color=tuple(stroke) if stroke else None,
            fill=tuple(fill) if fill else None,
            width=float(obj.get("width") or 1.0),
            even_odd=bool(obj.get("evenOdd")),
            closePath=bool(obj.get("closePath")),
            stroke_opacity=float(obj.get("strokeOpacity", 1.0) or 1.0),
            fill_opacity=float(obj.get("fillOpacity", 1.0) or 1.0),
        )
        shape.commit()

    def draw_image_object(self, page: Any, obj: dict[str, Any]) -> None:
        import fitz  # type: ignore

        image_path = self.job_dir / str(obj.get("imagePath") or "")
        if not image_path.exists():
            return
        bbox = obj.get("bbox") or {}
        rect = fitz.Rect(float(bbox.get("left") or 0), float(bbox.get("top") or 0), float(bbox.get("right") or 0), float(bbox.get("bottom") or 0))
        if rect.is_empty:
            return
        page.insert_image(rect, filename=str(image_path), keep_proportion=False, overlay=True)

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

    def font_kwargs_for_text(self, obj: dict[str, Any], text: str) -> dict[str, Any]:
        font_file = self.resolve_text_font_file()
        if font_file and any(ord(char) > 0x7F for char in text):
            return {"fontname": "v6text", "fontfile": font_file}
        font = str(obj.get("font") or "").lower()
        if "cour" in font or "mono" in font:
            return {"fontname": "cour"}
        if "times" in font or "georgia" in font or "serif" in font:
            return {"fontname": "tiro"}
        return {"fontname": "helv"}

    def insert_text_state(self, page: Any, obj: dict[str, Any], point: list[float], text: str, font_size: float, rotate: int) -> bool:
        import fitz  # type: ignore

        if not text:
            return True
        params: dict[str, Any] = {
            "fontsize": font_size,
            "color": tuple(obj.get("color") or [0, 0, 0]),
            "rotate": rotate,
            "overlay": True,
        }
        params.update(self.font_kwargs_for_text(obj, text))
        alpha = float_value(obj.get("alpha"), 1.0)
        if alpha < 1.0:
            params["fill_opacity"] = alpha
        try:
            page.insert_text(fitz.Point(float(point[0]), float(point[1])), text, **params)
            return True
        except Exception:
            params.pop("fontfile", None)
            params["fontname"] = "helv"
            try:
                page.insert_text(fitz.Point(float(point[0]), float(point[1])), text, **params)
                return True
            except Exception:
                return False

    def draw_translated_text(self, page: Any, obj: dict[str, Any]) -> None:
        bbox = obj.get("bbox") or {}
        text = str(obj.get("translated") or obj.get("source") or "")
        if not text:
            return
        font_size = max(self.config.min_font_size, float_value(obj.get("fontSize"), 10.0))
        rotate = line_rotation(obj.get("lineDirection") or [1.0, 0.0])
        source = str(obj.get("source") or "")
        chars = obj.get("chars") if isinstance(obj.get("chars"), list) else []
        if text == source and chars and text_from_chars(chars) == source:
            for char in chars:
                char_text = str(char.get("c") or "")
                if not char_text:
                    continue
                self.insert_text_state(page, obj, point_value(char.get("origin")), char_text, font_size, rotate)
            return
        origin = point_value(obj.get("origin"))
        if origin == [0.0, 0.0]:
            origin = [float_value(bbox.get("left"), 0.0), float_value(bbox.get("bottom"), 0.0)]
        self.insert_text_state(page, obj, origin, text, font_size, rotate)

    def fit_text_to_rect(self, text: str, rect: Any, base_font_size: float) -> tuple[float, list[str]]:
        font_size = max(self.config.min_font_size, base_font_size)
        for _ in range(self.config.max_shrink_steps + 1):
            wrapped = wrap_text(text, max(1.0, float(rect.width)), font_size)
            if len(wrapped) * font_size * 1.2 <= float(rect.height) + 0.5:
                return font_size, wrapped
            if font_size <= self.config.min_font_size:
                break
            font_size = max(self.config.min_font_size, font_size - 0.5)
        return font_size, wrap_text(text, max(1.0, float(rect.width)), font_size)

    def step_05_publish_output(self) -> None:
        source = self.pdf_dir / "draft.pdf"
        target = self.config.output_dir / f"{safe_stem(self.source_pdf)}_{self.config.target_lang.upper()}.pdf"
        ensure_dir(target.parent)
        shutil.copyfile(source, target)
        write_json(self.state_dir / "publish-report.json", {"status": "ok", "output": str(target), "recordedAt": now_iso()})


def main(argv: list[str]) -> int:
    base_dir = Path(__file__).resolve().parents[2]
    args = parse_args(argv)
    config = load_config(base_dir, args)
    source_pdf = resolve_source_pdf(config, args.pdf)
    Pipeline(config, source_pdf).run()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
