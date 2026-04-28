"""
com_replacer_microsoft.py — STEP 3-2 (Microsoft 공식 엔진 버전)

PowerPoint COM 으로 components_kr/ JSON 의 번역문을
kr/{stem}_KO.pptx 의 동일 Shape 에 in-place 치환한다.

ooxml_replacer.py 와 동일한 시그니처를 제공하므로
translator_microsoft.py 가 동일하게 호출 가능.

치환 전략:
  - shape.Id 로 JSON 의 id (s{N}_shape{Id}) 매칭
  - 텍스트박스: 각 단락의 텍스트를 일괄 set, 폰트명은 한글 폰트로 override
  - 표: 셀별 첫 단락 텍스트로 set
  - SmartArt: AllNodes 순회하며 번역 노드 텍스트로 set
  - 노트: NotesPage 의 본문 placeholder 에 set
  - 차트: 제목만 갱신 (있을 경우)
"""
from __future__ import annotations

import json
import os
from typing import Dict, Optional

from library import logger
from library.com_app_microsoft import (
    powerpoint_app, open_presentation,
    MSO_TRUE,
    MSO_SHAPE_TABLE, MSO_SHAPE_CHART, MSO_SHAPE_SMARTART,
    PP_SAVE_AS_OPEN_XML_PRESENTATION,
)


def replace_pptx(kr_pptx_path: str, comp_kr_dir: str,
                 translated_dir: str, slide_limit: Optional[int] = None) -> dict:
    """kr/{stem}_KO.pptx 를 COM 으로 열어 슬라이드별 텍스트를 치환하고 저장한다.

    ooxml_replacer.replace_pptx 와 동일한 인터페이스.
    """
    log = logger.get()
    statuses: dict = {}
    os.makedirs(translated_dir, exist_ok=True)

    with powerpoint_app() as app:
        with open_presentation(app, kr_pptx_path, read_only=False) as prs:
            total = prs.Slides.Count
            for slide_idx in range(1, total + 1):
                if slide_limit and slide_idx > slide_limit:
                    continue

                comp_path = os.path.join(comp_kr_dir, f"slide_{slide_idx}_component_kr.json")
                font_path = os.path.join(comp_kr_dir, f"slide_{slide_idx}_font_kr.json")
                if not os.path.exists(comp_path):
                    log.warning(f"  slide_{slide_idx}: component_kr JSON 없음, 원본 유지")
                    continue

                with open(comp_path, encoding="utf-8") as f:
                    comp = json.load(f)
                font_map = {"__default__": "Pretendard"}
                if os.path.exists(font_path):
                    with open(font_path, encoding="utf-8") as f:
                        font_map = json.load(f)

                slide = prs.Slides(slide_idx)
                try:
                    status = _replace_slide(slide, comp, font_map)
                    statuses[slide_idx] = status
                    ok = sum(1 for i in status["items"] if i["ok"])
                    bad = len(status["items"]) - ok
                    log.info(f"  slide_{slide_idx} COM 치환 완료 (성공 {ok}, 실패 {bad})")
                except Exception as e:
                    log.error(f"  slide_{slide_idx} COM 치환 실패: {e}")

                # 노트
                notes_text = comp.get("notes", "")
                if notes_text:
                    try:
                        _replace_notes(slide, notes_text)
                    except Exception as e:
                        log.warning(f"  slide_{slide_idx} 노트 치환 실패: {e}")

            # 저장 (원본 형식 유지)
            try:
                prs.Save()
            except Exception:
                # 일부 환경에서 Save 실패 시 SaveAs 로 강제 저장
                abs_path = os.path.abspath(kr_pptx_path).replace("/", "\\")
                prs.SaveAs(abs_path, PP_SAVE_AS_OPEN_XML_PRESENTATION)
            log.info(f"[STEP 3-2 COM] 저장 완료 → {kr_pptx_path}")

    # status JSON 저장
    for sidx, status in statuses.items():
        with open(os.path.join(translated_dir, f"slide_{sidx}.json"),
                  "w", encoding="utf-8") as f:
            json.dump(status, f, ensure_ascii=False, indent=2)

    return statuses


# ──────────────────────────────────────────────
# 슬라이드 1장 치환
# ──────────────────────────────────────────────

def _replace_slide(slide, comp: dict, font_map: Dict[str, str]) -> dict:
    slide_num = comp["slide_num"]
    status: dict = {"slide_num": slide_num, "items": []}

    tb_map  = {tb["id"]:  tb  for tb  in comp.get("text_boxes", [])}
    tbl_map = {t["id"]:   t   for t   in comp.get("tables", [])}
    sa_map  = {sa["id"]:  sa  for sa  in comp.get("smartarts", [])}
    ch_map  = {c["id"]:   c   for c   in comp.get("charts", [])}

    default_kr = font_map.get("__default__", "Pretendard")

    for s_idx in range(1, slide.Shapes.Count + 1):
        try:
            shape = slide.Shapes(s_idx)
        except Exception:
            continue
        sid = f"s{slide_num}_shape{shape.Id}"

        try:
            stype = int(shape.Type)
        except Exception:
            stype = -1

        # 표
        if sid in tbl_map:
            try:
                _replace_table(shape, tbl_map[sid], font_map, default_kr)
                status["items"].append({"id": sid, "type": "table", "ok": True})
            except Exception as e:
                status["items"].append({"id": sid, "type": "table", "ok": False, "error": str(e)})
            continue

        # 텍스트박스
        if sid in tb_map:
            try:
                _replace_text(shape, tb_map[sid], font_map, default_kr)
                status["items"].append({"id": sid, "type": "text_box", "ok": True})
            except Exception as e:
                status["items"].append({"id": sid, "type": "text_box", "ok": False, "error": str(e)})
            continue

        # SmartArt
        if sid in sa_map:
            try:
                _replace_smartart(shape, sa_map[sid], default_kr)
                status["items"].append({"id": sid, "type": "smartart", "ok": True})
            except Exception as e:
                status["items"].append({"id": sid, "type": "smartart", "ok": False, "error": str(e)})
            continue

        # 차트
        if sid in ch_map:
            try:
                _replace_chart(shape, ch_map[sid], default_kr)
                status["items"].append({"id": sid, "type": "chart", "ok": True})
            except Exception as e:
                status["items"].append({"id": sid, "type": "chart", "ok": False, "error": str(e)})
            continue

    return status


# ──────────────────────────────────────────────
# Shape 종류별 치환
# ──────────────────────────────────────────────

def _replace_text(shape, tb_data: dict, font_map: dict, default_kr: str) -> None:
    if int(getattr(shape, "HasTextFrame", 0)) != MSO_TRUE:
        return
    tf = shape.TextFrame
    tr = tf.TextRange

    paragraphs = tb_data.get("paragraphs", [])
    if not paragraphs:
        return

    # 단락 단위 매칭. 기존 단락 수가 부족하면 첫 단락에 합쳐서 set.
    try:
        existing_count = tr.Paragraphs().Count
    except Exception:
        existing_count = 0

    if existing_count == 0:
        joined = "\r".join(p.get("text", "") for p in paragraphs)
        tr.Text = joined
        _apply_font_to_range(tr, default_kr)
        return

    for p_idx, para in enumerate(paragraphs, start=1):
        new_text = para.get("text", "")
        if p_idx > existing_count:
            # 추가 단락은 끝에 append
            tr.InsertAfter("\r" + new_text)
            try:
                last = tr.Paragraphs(tr.Paragraphs().Count)
                _apply_font_to_range(last, default_kr)
            except Exception:
                pass
            continue
        try:
            p_range = tr.Paragraphs(p_idx)
            p_range.Text = new_text
            _apply_font_to_range(p_range, _resolve_kr_font(para, font_map, default_kr))
        except Exception:
            continue


def _replace_table(shape, tbl_data: dict, font_map: dict, default_kr: str) -> None:
    table = shape.Table
    rows = tbl_data.get("rows", [])
    for r_idx, row in enumerate(rows, start=1):
        if r_idx > table.Rows.Count:
            break
        for c_idx, cell_data in enumerate(row, start=1):
            if c_idx > table.Columns.Count:
                break
            try:
                cell_tr = table.Cell(r_idx, c_idx).Shape.TextFrame.TextRange
                cell_tr.Text = cell_data.get("text", "")
                _apply_font_to_range(cell_tr, _resolve_kr_font(cell_data, font_map, default_kr))
            except Exception:
                continue


def _replace_smartart(shape, sa_data: dict, default_kr: str) -> None:
    nodes_data = sa_data.get("smartart_nodes", [])
    if not nodes_data:
        return
    smart = shape.SmartArt
    all_nodes = smart.AllNodes
    by_index = {n["index"]: n["text"] for n in nodes_data if "index" in n}
    for n_idx in range(1, all_nodes.Count + 1):
        if n_idx not in by_index:
            continue
        try:
            node = all_nodes(n_idx)
            tr = node.TextFrame2.TextRange
            tr.Text = by_index[n_idx]
            try:
                node.TextFrame2.TextRange.Font.Name.Latin = default_kr
                node.TextFrame2.TextRange.Font.Name.EastAsian = default_kr
            except Exception:
                pass
        except Exception:
            continue


def _replace_chart(shape, ch_data: dict, default_kr: str) -> None:
    texts = ch_data.get("chart_texts", [])
    if not texts:
        return
    try:
        chart = shape.Chart
    except Exception:
        return
    for entry in texts:
        if entry.get("role") == "title" and int(getattr(chart, "HasTitle", 0)) == MSO_TRUE:
            try:
                chart.ChartTitle.Text = entry.get("text", "")
            except Exception:
                continue


def _replace_notes(slide, notes_text: str) -> None:
    notes_page = slide.NotesPage
    for s_idx in range(1, notes_page.Shapes.Count + 1):
        sh = notes_page.Shapes(s_idx)
        try:
            if int(getattr(sh, "HasTextFrame", 0)) != MSO_TRUE:
                continue
            tf = sh.TextFrame
            # 노트 본문 placeholder 만 식별: 슬라이드 번호 placeholder 는 건너뛴다
            current = tf.TextRange.Text.strip() if int(tf.HasText) == MSO_TRUE else ""
            if current.isdigit():
                continue
            tf.TextRange.Text = notes_text
            return
        except Exception:
            continue


# ──────────────────────────────────────────────
# 폰트 헬퍼
# ──────────────────────────────────────────────

def _apply_font_to_range(text_range, kr_font: str) -> None:
    """TextRange 의 폰트명을 한글 폰트로 일괄 override (서식은 보존)."""
    try:
        text_range.Font.Name = kr_font
    except Exception:
        pass
    # 동아시아 폰트 별도 지정 (TextRange2 사용)
    try:
        # TextRange (PowerPoint) → Font 단일. 동아시아는 TextRange2 가 필요.
        # COM 에서 TextRange 의 부모 TextFrame 의 TextRange2 로 접근.
        parent = text_range.Parent  # TextFrame
        tr2 = parent.TextRange2
        tr2.Font.NameFarEast = kr_font
    except Exception:
        pass


def _resolve_kr_font(item: dict, font_map: dict, default_kr: str) -> str:
    # 단락/run/cell 의 'font' 키가 영문 폰트명이면 매핑, 없으면 기본값
    name = None
    if "font" in item:
        name = item.get("font")
    elif item.get("runs"):
        name = item["runs"][0].get("font")
    if name and name in font_map:
        return font_map[name]
    return default_kr
