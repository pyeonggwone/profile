#!/usr/bin/env python3
import argparse
import json
import os
import sys

import fitz


def int_to_rgb(value):
    number = int(value or 0)
    return ((number >> 16) & 255, (number >> 8) & 255, number & 255)


def as_rgb(value, default=(0, 0, 0)):
    if not isinstance(value, list) or len(value) != 3:
        return default
    out = []
    for item in value:
        try:
            number = float(item)
        except Exception:
            number = 0.0
        out.append(max(0.0, min(1.0, number)))
    return tuple(out)


def span_text(span):
    text = span.get("text", "")
    if text:
        return text
    chars = span.get("chars") or []
    return "".join(ch.get("c", "") for ch in chars)


def sample_background(pix, bbox, text_color):
    width = pix.width
    height = pix.height
    x0, y0, x1, y1 = [float(v) for v in bbox]
    points = []
    for x in (x0 + 1, (x0 + x1) / 2, x1 - 1):
        points.append((x, y0 + 1))
        points.append((x, y1 - 1))
    for y in (y0 + 1, (y0 + y1) / 2, y1 - 1):
        points.append((x0 + 1, y))
        points.append((x1 - 1, y))

    colors = []
    for x, y in points:
        px = int(round(x))
        py = int(round(y))
        if px < 0 or py < 0 or px >= width or py >= height:
            continue
        try:
            color = pix.pixel(px, py)[:3]
        except Exception:
            continue
        distance = sum(abs(int(color[i]) - int(text_color[i])) for i in range(3))
        if distance > 48:
            colors.append(tuple(int(c) for c in color))
    if not colors:
        return [1, 1, 1]

    buckets = {}
    for color in colors:
        key = tuple(round(c / 16) * 16 for c in color)
        buckets[key] = buckets.get(key, 0) + 1
    dominant = max(buckets.items(), key=lambda item: item[1])[0]
    return [round(max(0, min(255, c)) / 255, 4) for c in dominant]


def style_from_span(span):
    font = str(span.get("font") or "")
    flags = int(span.get("flags") or 0)
    lower = font.lower()
    return {
        "flags": flags,
        "bold": bool(flags & 16) or "bold" in lower or "black" in lower or "semibold" in lower,
        "italic": bool(flags & 2) or "italic" in lower or "oblique" in lower,
        "serif": bool(flags & 4) or "serif" in lower or "times" in lower,
        "monospace": bool(flags & 8) or "mono" in lower or "courier" in lower,
    }


def extract_pages(pdf_path):
    doc = fitz.open(pdf_path)
    pages = []
    flags = fitz.TEXT_PRESERVE_LIGATURES | fitz.TEXT_PRESERVE_WHITESPACE
    for page_index, page in enumerate(doc):
        pix = page.get_pixmap(alpha=False)
        page_data = page.get_text("dict", flags=flags)
        runs = []
        for block_index, block in enumerate(page_data.get("blocks", [])):
            if block.get("type") != 0:
                continue
            for line_index, line in enumerate(block.get("lines", [])):
                line_bbox = line.get("bbox") or [0, 0, 0, 0]
                for span_index, span in enumerate(line.get("spans", [])):
                    text = span_text(span)
                    if not text or not text.strip():
                        continue
                    bbox = span.get("bbox") or line_bbox
                    size = float(span.get("size") or max(1.0, bbox[3] - bbox[1]) or 10.0)
                    origin = span.get("origin") or [bbox[0], bbox[1] + size]
                    color_int = int(span.get("color") or 0)
                    color_rgb = int_to_rgb(color_int)
                    style = style_from_span(span)
                    runs.append({
                        "text": text,
                        "x": float(origin[0]),
                        "y": float(origin[1]),
                        "top": float(bbox[1]),
                        "bottom": float(bbox[3]),
                        "left": float(bbox[0]),
                        "right": float(bbox[2]),
                        "width": float(max(0.0, bbox[2] - bbox[0])),
                        "height": float(max(0.0, bbox[3] - bbox[1])),
                        "font_size": size,
                        "font_resource": span.get("font", ""),
                        "font": span.get("font", ""),
                        "color": color_int,
                        "color_rgb": [round(c / 255, 4) for c in color_rgb],
                        "bg_color": sample_background(pix, bbox, color_rgb),
                        **style,
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
    doc.close()
    return pages


def inspect_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    info = {
        "pageCount": doc.page_count,
        "metadata": doc.metadata or {},
        "isEncrypted": bool(doc.is_encrypted),
        "needsPass": bool(doc.needs_pass),
        "engine": "pymupdf",
        "pymupdf": fitz.VersionBind,
    }
    doc.close()
    return info


def draw_fill(page, edit):
    x = float(edit.get("x") or 0)
    y = float(edit.get("y") or 0)
    rect = fitz.Rect(
        x,
        y,
        x + max(0.0, float(edit.get("width") or 0)),
        y + max(0.0, float(edit.get("height") or 0)),
    )
    page.draw_rect(rect, color=None, fill=as_rgb(edit.get("color"), (1, 1, 1)), overlay=True)


def insert_textbox(page, edit):
    x = float(edit.get("x") or 0)
    y = float(edit.get("y") or 0)
    width = max(8.0, float(edit.get("width") or 160))
    height = max(8.0, float(edit.get("height") or 20))
    rect = fitz.Rect(x, y, x + width, y + height)
    text = str(edit.get("text") or "")
    size = max(4.0, float(edit.get("size") or 10.0))
    color = as_rgb(edit.get("color"), (0, 0, 0))
    font_path = edit.get("fontPath") or edit.get("font_path") or ""
    font_name = str(edit.get("fontName") or edit.get("font_name") or "helv")
    font_args = {}
    if font_path:
        font_args["fontfile"] = font_path

    current_size = size
    while current_size >= 4.0:
        try:
            result = page.insert_textbox(
                rect,
                text,
                fontsize=current_size,
                fontname=font_name,
                color=color,
                align=fitz.TEXT_ALIGN_LEFT,
                overlay=True,
                **font_args,
            )
        except Exception:
            if font_args:
                font_args = {}
                font_name = "helv"
                continue
            raise
        if result >= 0:
            return current_size
        current_size -= 0.5

    page.insert_text((x, y + size), text, fontsize=4.0, fontname=font_name, color=color, overlay=True, **font_args)
    return 4.0


def apply_edits(input_pdf, output_pdf, edits_path):
    with open(edits_path, "r", encoding="utf-8") as handle:
        edits = json.load(handle)
    if not isinstance(edits, list):
        raise ValueError("edits JSON must be an array")

    doc = fitz.open(input_pdf)
    applied = 0
    for edit in edits:
        page_number = int(edit.get("page") or 1)
        if page_number < 1 or page_number > doc.page_count:
            continue
        page = doc[page_number - 1]
        kind = edit.get("type")
        if kind == "FillRect":
            draw_fill(page, edit)
            applied += 1
        elif kind in {"AddTextBox", "AddTextBoxEmbedded"}:
            insert_textbox(page, edit)
            applied += 1
        elif kind in {"AddText", "AddTextEmbedded"}:
            size = max(4.0, float(edit.get("size") or 10.0))
            insert_textbox(page, {**edit, "y": float(edit.get("y") or 0) - size, "width": float(edit.get("width") or 240), "height": size * 1.6})
            applied += 1
        elif kind == "AddTextAnnotation":
            point = fitz.Point(float(edit.get("x") or 0), float(edit.get("y") or 0))
            page.add_text_annot(point, str(edit.get("contents") or ""))
            applied += 1

    os.makedirs(os.path.dirname(os.path.abspath(output_pdf)), exist_ok=True)
    doc.save(output_pdf, garbage=4, deflate=True, clean=True)
    doc.close()
    return {"output": output_pdf, "applied": applied, "engine": "pymupdf"}


def main(argv):
    parser = argparse.ArgumentParser(prog="pymupdf_engine")
    sub = parser.add_subparsers(dest="command", required=True)

    inspect_parser = sub.add_parser("inspect")
    inspect_parser.add_argument("pdf")
    inspect_parser.add_argument("--json", action="store_true")

    text_parser = sub.add_parser("text")
    text_parser.add_argument("pdf")
    text_parser.add_argument("--json", action="store_true")

    edit_parser = sub.add_parser("edit")
    edit_parser.add_argument("input")
    edit_parser.add_argument("output")
    edit_parser.add_argument("--edits", required=True)

    args = parser.parse_args(argv)
    if args.command == "inspect":
        print(json.dumps(inspect_pdf(args.pdf), ensure_ascii=False))
    elif args.command == "text":
        print(json.dumps(extract_pages(args.pdf), ensure_ascii=False))
    elif args.command == "edit":
        print(json.dumps(apply_edits(args.input, args.output, args.edits), ensure_ascii=False))


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception as exc:
        print(f"pymupdf_engine error: {exc}", file=sys.stderr)
        sys.exit(1)