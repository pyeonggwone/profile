from __future__ import annotations

import argparse
import json
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
    "02_extract_structure_manifest",
    "03_build_textless_pdf",
    "04_publish_output",
]


@dataclass
class Config:
    base_dir: Path
    input_dir: Path
    output_dir: Path
    work_dir: Path


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


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="pdf-translate-v7 textless PDF structure rebuild")
    parser.add_argument("pdf", nargs="?", help="Source PDF. Defaults to the first PDF in input/.")
    return parser.parse_args(argv)


def load_config(base_dir: Path) -> Config:
    load_env_file(base_dir / ".env")
    return Config(
        base_dir=base_dir,
        input_dir=base_dir / "input",
        output_dir=base_dir / "output",
        work_dir=base_dir / "work",
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


def bbox_dict(value: Any) -> dict[str, float]:
    x0, y0, x1, y1 = rect_value(value)
    return {
        "x": x0,
        "y": y0,
        "width": max(0.0, x1 - x0),
        "height": max(0.0, y1 - y0),
        "left": x0,
        "top": y0,
        "right": x1,
        "bottom": y1,
    }


def serialize_path_item(item: Any) -> dict[str, Any]:
    op = str(item[0]) if isinstance(item, (list, tuple)) and item else "unknown"
    values = list(item[1:]) if isinstance(item, (list, tuple)) else []
    if op == "re" and values:
        return {"op": op, "rect": rect_value(values[0])}
    if op in {"m", "l", "c"}:
        return {"op": op, "points": [point_value(value) for value in values]}
    if op == "qu" and values:
        return {"op": op, "quad": [point_value(point) for point in values[0]] if isinstance(values[0], (list, tuple)) else []}
    return {"op": op, "raw": str(item)}


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
        self.job_path = self.state_dir / "job.json"

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
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
            "status": "created",
            "mode": "textless-structure-rebuild",
        })

    def step_02_extract_structure_manifest(self) -> None:
        import fitz  # type: ignore

        pages = []
        text_count = 0
        with fitz.open(self.source_pdf) as document:
            for page_index, page in enumerate(document):
                page_number = page_index + 1
                drawings = self.extract_drawings(page, page_number)
                images = self.extract_images(document, page, page_number)
                removed_texts = self.count_text_spans(page)
                text_count += removed_texts
                pages.append({
                    "page": page_number,
                    "width": float(page.rect.width),
                    "height": float(page.rect.height),
                    "objects": drawings + images,
                    "counts": {"drawings": len(drawings), "images": len(images), "removedTexts": removed_texts},
                })
        write_json(self.state_dir / "object-manifest.json", {
            "status": "ok",
            "sourcePdf": str(self.source_pdf),
            "pages": pages,
            "summary": {"pages": len(pages), "removedTexts": text_count},
            "recordedAt": now_iso(),
        })

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
                "closePath": bool(drawing.get("closePath")),
                "evenOdd": bool(drawing.get("even_odd")),
                "strokeOpacity": float(drawing.get("stroke_opacity", 1.0) or 1.0),
                "fillOpacity": float(drawing.get("fill_opacity", 1.0) or 1.0),
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
                "imagePath": str(image_path.relative_to(self.job_dir)),
            })
        return records

    def count_text_spans(self, page: Any) -> int:
        count = 0
        text_dict = page.get_text("dict") or {}
        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if str(span.get("text") or "").strip():
                        count += 1
        return count

    def step_03_build_textless_pdf(self) -> None:
        import fitz  # type: ignore

        manifest = read_json(self.state_dir / "object-manifest.json", {})
        target = self.pdf_dir / "textless.pdf"
        output = fitz.open()
        for page_def in manifest.get("pages", []):
            page = output.new_page(width=float(page_def.get("width") or 612), height=float(page_def.get("height") or 792))
            objects = sorted(page_def.get("objects", []), key=lambda item: int(item.get("order") or 0))
            for obj in objects:
                if obj.get("type") == "path":
                    self.draw_path_object(page, obj)
                elif obj.get("type") == "image":
                    self.draw_image_object(page, obj)
        ensure_dir(target.parent)
        output.save(target, garbage=4, deflate=True, clean=True)
        output.close()
        write_json(self.state_dir / "build-report.json", {
            "status": "ok",
            "engine": "pymupdf-textless-structure-rebuild",
            "output": str(target.relative_to(self.job_dir)),
            "recordedAt": now_iso(),
        })

    def draw_path_object(self, page: Any, obj: dict[str, Any]) -> None:
        import fitz  # type: ignore

        shape = page.new_shape()
        has_items = False
        for item in obj.get("items") or []:
            op = item.get("op")
            if op == "re":
                shape.draw_rect(fitz.Rect(*item.get("rect", [0, 0, 0, 0])))
                has_items = True
            elif op == "l":
                points = item.get("points") or []
                if len(points) >= 2:
                    shape.draw_line(fitz.Point(*points[0]), fitz.Point(*points[1]))
                    has_items = True
            elif op == "c":
                points = item.get("points") or []
                if len(points) >= 4:
                    shape.draw_bezier(fitz.Point(*points[0]), fitz.Point(*points[1]), fitz.Point(*points[2]), fitz.Point(*points[3]))
                    has_items = True
        stroke = obj.get("stroke")
        fill = obj.get("fill")
        if not has_items or (not stroke and not fill):
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

    def step_04_publish_output(self) -> None:
        source = self.pdf_dir / "textless.pdf"
        target = self.config.output_dir / f"{safe_stem(self.source_pdf)}_textless.pdf"
        ensure_dir(target.parent)
        shutil.copyfile(source, target)
        write_json(self.state_dir / "publish-report.json", {"status": "ok", "output": str(target), "recordedAt": now_iso()})


def main(argv: list[str]) -> int:
    base_dir = Path(__file__).resolve().parents[2]
    args = parse_args(argv)
    config = load_config(base_dir)
    source_pdf = resolve_source_pdf(config, args.pdf)
    Pipeline(config, source_pdf).run()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))