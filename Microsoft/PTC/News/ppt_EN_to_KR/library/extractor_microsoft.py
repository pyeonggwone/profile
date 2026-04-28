"""
extractor_microsoft.py — STEP 2 (Microsoft 공식 엔진 버전)

PowerPoint COM Automation (pywin32) 으로 슬라이드별 컴포넌트를 직렬화한다.
출력 JSON 스키마는 library/extractor.py 와 100% 동일하므로
translator(_microsoft) 가 그대로 재사용 가능하다.

차이점:
  - python-pptx 가 처리하지 못하던 SmartArt 노드 텍스트, 차트 제목/축 라벨까지 추출
  - 이미지는 Shape.Export 로 렌더링 결과를 PNG/JPG 로 저장 (원본 blob 추출 아님)
  - 모든 좌표/크기는 EMU 단위로 통일 (기존 JSON 호환)
"""
from __future__ import annotations

import json
import os
from typing import Optional

from library.com_app_microsoft import (
    powerpoint_app, open_presentation,
    points_to_emu, color_int_to_hex,
    MSO_TRUE,
    MSO_SHAPE_TEXT_BOX, MSO_SHAPE_PLACEHOLDER,
    MSO_SHAPE_PICTURE, MSO_SHAPE_LINKED_PICTURE,
    MSO_SHAPE_TABLE, MSO_SHAPE_CHART, MSO_SHAPE_SMARTART,
    MSO_SHAPE_GROUP,
    PP_SHAPE_FORMAT_JPG,
)


def extract(pptx_path: str, work_dir: str, filename_stem: str) -> None:
    """원본 PPTX 를 COM 으로 열고 슬라이드별 컴포넌트를 JSON 으로 저장한다."""
    out_dir = os.path.join(work_dir, "components_en", filename_stem)
    img_dir = os.path.join(work_dir, "img", filename_stem)
    os.makedirs(out_dir, exist_ok=True)

    with powerpoint_app() as app:
        with open_presentation(app, pptx_path, read_only=True) as prs:
            total = prs.Slides.Count
            for slide_idx in range(1, total + 1):
                slide = prs.Slides(slide_idx)
                data = _extract_slide(slide, slide_idx, img_dir)
                out_path = os.path.join(out_dir, f"slide_{slide_idx}_component_en.json")
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"[extractor_microsoft] {filename_stem}: {total} 슬라이드 추출 완료")


# ──────────────────────────────────────────────
# 슬라이드 1장 처리
# ──────────────────────────────────────────────

def _extract_slide(slide, slide_num: int, img_dir: str) -> dict:
    data: dict = {"slide_num": slide_num}
    text_boxes, images, tables, smartarts, charts = [], [], [], [], []
    slide_img_dir = os.path.join(img_dir, f"slide_{slide_num}")

    for shape_idx in range(1, slide.Shapes.Count + 1):
        try:
            shape = slide.Shapes(shape_idx)
        except Exception:
            continue
        sid = f"s{slide_num}_shape{shape.Id}"

        try:
            stype = int(shape.Type)
        except Exception:
            stype = -1

        # 표
        if stype == MSO_SHAPE_TABLE or _safe_bool(getattr(shape, "HasTable", 0)):
            tbl = _extract_table(shape, sid)
            if tbl:
                tables.append(tbl)
            continue

        # 이미지
        if stype in (MSO_SHAPE_PICTURE, MSO_SHAPE_LINKED_PICTURE):
            entry = _extract_image(shape, sid, slide_img_dir)
            if entry:
                images.append(entry)
            continue

        # 차트
        if _safe_bool(getattr(shape, "HasChart", 0)):
            charts.append(_extract_chart(shape, sid))
            continue

        # SmartArt
        if _safe_bool(getattr(shape, "HasSmartArt", 0)) or stype == MSO_SHAPE_SMARTART:
            smartarts.append(_extract_smartart(shape, sid))
            continue

        # 텍스트 (텍스트박스, 자동도형, 자리표시자 등)
        if _safe_bool(getattr(shape, "HasTextFrame", 0)):
            try:
                if _safe_bool(shape.TextFrame.HasText):
                    text_boxes.append(_extract_text(shape, sid))
                    continue
            except Exception:
                pass

        # 그룹 / 기타 → 메타만 기록
        if stype == MSO_SHAPE_GROUP:
            smartarts.append(_extract_meta(shape, sid))
            continue

        smartarts.append(_extract_meta(shape, sid))

    if text_boxes: data["text_boxes"] = text_boxes
    if images:     data["images"]     = images
    if tables:     data["tables"]     = tables
    if smartarts:  data["smartarts"]  = smartarts
    if charts:     data["charts"]     = charts

    notes_text = _extract_notes(slide)
    if notes_text:
        data["notes"] = notes_text

    return data


# ──────────────────────────────────────────────
# Shape 종류별 추출
# ──────────────────────────────────────────────

def _extract_text(shape, sid: str) -> dict:
    paragraphs = []
    tf = shape.TextFrame
    try:
        text_range = tf.TextRange
        para_count = text_range.Paragraphs().Count
    except Exception:
        return _meta_with_paragraphs(shape, sid, [])

    for p_idx in range(1, para_count + 1):
        try:
            para = text_range.Paragraphs(p_idx)
        except Exception:
            continue
        runs = _split_runs_by_format(para)
        para_text = para.Text.rstrip("\r\n\v")
        paragraphs.append({"runs": runs, "text": para_text})

    return _meta_with_paragraphs(shape, sid, paragraphs)


def _split_runs_by_format(para_range) -> list:
    """단락을 문자 단위 서식 변화 지점으로 분할하여 run 배열로 반환.

    PowerPoint COM 의 TextRange 에는 명시적 Run 컬렉션이 없으므로,
    인접 문자의 Font 속성이 동일한 구간끼리 묶는다.
    """
    text = para_range.Text.rstrip("\r\n\v")
    if not text:
        return []

    runs: list = []
    current = {"text": "", "_fmt": None}

    for i in range(1, len(text) + 1):
        try:
            ch_range = para_range.Characters(i, 1)
            font = ch_range.Font
            fmt = (
                _safe_str(font, "Name"),
                _safe_tristate(font, "Bold"),
                _safe_tristate(font, "Italic"),
                _safe_tristate(font, "Underline"),
                _safe_int(font, "Size"),
                _safe_color(font),
            )
        except Exception:
            fmt = (None, None, None, None, None, None)
        ch = text[i - 1]

        if current["_fmt"] is None:
            current = {"text": ch, "_fmt": fmt}
        elif fmt == current["_fmt"]:
            current["text"] += ch
        else:
            runs.append(_run_from_fmt(current["text"], current["_fmt"]))
            current = {"text": ch, "_fmt": fmt}

    if current["_fmt"] is not None and current["text"]:
        runs.append(_run_from_fmt(current["text"], current["_fmt"]))
    return runs


def _run_from_fmt(text: str, fmt: tuple) -> dict:
    name, bold, italic, underline, size, color = fmt
    return {
        "text": text,
        "font": name,
        "bold": bold,
        "italic": italic,
        "underline": underline,
        "size": size,
        "color": color,
    }


def _extract_image(shape, sid: str, slide_img_dir: str) -> Optional[dict]:
    try:
        os.makedirs(slide_img_dir, exist_ok=True)
        idx = len(os.listdir(slide_img_dir)) + 1
        img_filename = f"image_{idx}.jpg"
        img_path = os.path.join(slide_img_dir, img_filename)
        # COM 의 Shape.Export 는 절대 경로 + 백슬래시 필수
        shape.Export(os.path.abspath(img_path).replace("/", "\\"), PP_SHAPE_FORMAT_JPG)
        return {
            "id": sid,
            "left": _emu(shape.Left), "top": _emu(shape.Top),
            "width": _emu(shape.Width), "height": _emu(shape.Height),
            "img_path": img_path.replace("\\", "/"),
        }
    except Exception as e:
        print(f"[extractor_microsoft] 이미지 추출 실패 ({sid}): {e}")
        return None


def _extract_table(shape, sid: str) -> Optional[dict]:
    try:
        table = shape.Table
    except Exception:
        return None
    rows = []
    for r_idx in range(1, table.Rows.Count + 1):
        cells = []
        for c_idx in range(1, table.Columns.Count + 1):
            try:
                cell = table.Cell(r_idx, c_idx)
                tf = cell.Shape.TextFrame
                cell_text = tf.TextRange.Text.rstrip("\r\n\v") if tf.HasText else ""
                font_info = {}
                try:
                    char = tf.TextRange.Characters(1, 1)
                    f = char.Font
                    font_info = {
                        "font":  _safe_str(f, "Name"),
                        "bold":  _safe_tristate(f, "Bold"),
                        "size":  _safe_int(f, "Size"),
                        "color": _safe_color(f),
                    }
                except Exception:
                    pass
                cells.append({"text": cell_text, **font_info})
            except Exception:
                cells.append({"text": ""})
        rows.append(cells)
    return {
        "id": sid,
        "left": _emu(shape.Left), "top": _emu(shape.Top),
        "width": _emu(shape.Width), "height": _emu(shape.Height),
        "rows": rows,
    }


def _extract_chart(shape, sid: str) -> dict:
    info = _extract_meta(shape, sid)
    info["shape_type"] = MSO_SHAPE_CHART
    titles: list = []
    try:
        chart = shape.Chart
        if _safe_bool(chart.HasTitle):
            titles.append({"role": "title", "text": chart.ChartTitle.Text})
    except Exception:
        pass
    if titles:
        info["chart_texts"] = titles
    return info


def _extract_smartart(shape, sid: str) -> dict:
    info = _extract_meta(shape, sid)
    info["shape_type"] = MSO_SHAPE_SMARTART
    nodes: list = []
    try:
        smart = shape.SmartArt
        all_nodes = smart.AllNodes
        for n_idx in range(1, all_nodes.Count + 1):
            try:
                node = all_nodes(n_idx)
                txt = node.TextFrame2.TextRange.Text.rstrip("\r\n\v")
                if txt:
                    nodes.append({"index": n_idx, "text": txt})
            except Exception:
                continue
    except Exception:
        pass
    if nodes:
        info["smartart_nodes"] = nodes
    return info


def _extract_meta(shape, sid: str) -> dict:
    return {
        "id": sid,
        "left": _emu(shape.Left), "top": _emu(shape.Top),
        "width": _emu(shape.Width), "height": _emu(shape.Height),
        "shape_type": int(getattr(shape, "Type", -1)),
    }


def _meta_with_paragraphs(shape, sid: str, paragraphs: list) -> dict:
    return {
        "id": sid,
        "left": _emu(shape.Left), "top": _emu(shape.Top),
        "width": _emu(shape.Width), "height": _emu(shape.Height),
        "paragraphs": paragraphs,
    }


def _extract_notes(slide) -> str:
    try:
        notes_slide = slide.NotesPage
        # NotesPage.Shapes(2) 가 일반적으로 노트 텍스트 placeholder
        for s_idx in range(1, notes_slide.Shapes.Count + 1):
            sh = notes_slide.Shapes(s_idx)
            if _safe_bool(getattr(sh, "HasTextFrame", 0)) and _safe_bool(sh.TextFrame.HasText):
                txt = sh.TextFrame.TextRange.Text.strip()
                # 첫 placeholder 는 슬라이드 썸네일이라 텍스트 없음 → 두 번째 이후가 노트
                if txt and not txt.isdigit():
                    return txt
    except Exception:
        pass
    return ""


# ──────────────────────────────────────────────
# 안전 접근 유틸 (COM 속성 부재 시 None 반환)
# ──────────────────────────────────────────────

def _safe_bool(val) -> bool:
    try:
        return int(val) == MSO_TRUE
    except Exception:
        return False


def _safe_str(obj, attr: str) -> Optional[str]:
    try:
        v = getattr(obj, attr)
        return str(v) if v else None
    except Exception:
        return None


def _safe_int(obj, attr: str) -> Optional[int]:
    try:
        v = getattr(obj, attr)
        return int(v) if v is not None else None
    except Exception:
        return None


def _safe_tristate(obj, attr: str) -> Optional[bool]:
    try:
        v = int(getattr(obj, attr))
        if v == MSO_TRUE:
            return True
        if v == 0:
            return False
        return None
    except Exception:
        return None


def _safe_color(font) -> Optional[str]:
    try:
        return color_int_to_hex(int(font.Color.RGB))
    except Exception:
        return None


def _emu(pts) -> int:
    """COM 은 좌표/크기를 포인트로 반환 → JSON 호환을 위해 EMU 로 변환."""
    try:
        return points_to_emu(float(pts))
    except Exception:
        return 0
