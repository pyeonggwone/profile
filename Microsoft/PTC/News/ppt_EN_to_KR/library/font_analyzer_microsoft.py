"""
font_analyzer_microsoft.py — STEP 2 보조 (Microsoft 공식 엔진 버전)

PowerPoint COM 으로 슬라이드별 폰트를 수집하고
규칙 기반으로 한글 폰트에 매핑한다. (LLM 미사용)

출력 JSON 스키마는 library/font_analyzer.py 와 동일.
"""
from __future__ import annotations

import json
import os
from typing import Set

from library.com_app_microsoft import (
    powerpoint_app, open_presentation,
    MSO_TRUE,
)


# 규칙 기반 폰트 매핑 (font_analyzer.py 와 동일)
_RULE_BASED: list = [
    (["light", "thin"],                                       "Pretendard Light"),
    (["consolas", "courier", "mono", "code"],                 "D2Coding"),
    (["times", "georgia", "serif", "batang", "garamond"],     "본명조"),
    (["black", "heavy", "extrabold"],                          "Pretendard ExtraBold"),
    (["bold", "semibold", "demi"],                             "Pretendard SemiBold"),
    (["arial", "helvetica", "gothic"],                         "Pretendard"),
    (["segoe", "calibri", "tahoma", "verdana", "trebuchet"],   "Pretendard"),
]
_DEFAULT_KR_FONT = "Pretendard"


def analyze(pptx_path: str, work_dir: str, filename_stem: str,
            font_map_path: str, llm_client=None, model: str = "") -> None:
    """원본 PPTX 의 폰트를 COM 으로 수집하고 매핑 JSON 을 저장한다.

    Parameters
    ----------
    llm_client, model : 시그니처 호환을 위해 유지 (실제로는 사용하지 않음)
    """
    out_dir = os.path.join(work_dir, "components_en", filename_stem)
    os.makedirs(out_dir, exist_ok=True)
    font_map = _load_font_map(font_map_path)

    with powerpoint_app() as app:
        with open_presentation(app, pptx_path, read_only=True) as prs:
            for slide_idx in range(1, prs.Slides.Count + 1):
                slide = prs.Slides(slide_idx)
                slide_fonts = _collect_slide_fonts(slide)

                new_fonts = [f for f in slide_fonts if f and f not in font_map]
                if new_fonts:
                    font_map.update(_map_fonts_by_rule(new_fonts))
                    _save_font_map(font_map_path, font_map)

                slide_font_map = {
                    f: font_map.get(f, _DEFAULT_KR_FONT)
                    for f in slide_fonts if f
                }
                slide_font_map["__default__"] = font_map.get("__default__", _DEFAULT_KR_FONT)

                out_path = os.path.join(out_dir, f"slide_{slide_idx}_font_en.json")
                with open(out_path, "w", encoding="utf-8") as fp:
                    json.dump(slide_font_map, fp, ensure_ascii=False, indent=2)

    print(f"[font_analyzer_microsoft] {filename_stem}: 폰트 분석 완료")


def _collect_slide_fonts(slide) -> Set[str]:
    fonts: Set[str] = set()
    for s_idx in range(1, slide.Shapes.Count + 1):
        try:
            shape = slide.Shapes(s_idx)
        except Exception:
            continue
        _collect_shape_fonts(shape, fonts)
    return fonts


def _collect_shape_fonts(shape, fonts: Set[str]) -> None:
    # 텍스트 프레임
    try:
        if int(getattr(shape, "HasTextFrame", 0)) == MSO_TRUE \
           and int(shape.TextFrame.HasText) == MSO_TRUE:
            tr = shape.TextFrame.TextRange
            text = tr.Text.rstrip("\r\n\v")
            for i in range(1, len(text) + 1):
                try:
                    name = tr.Characters(i, 1).Font.Name
                    if name:
                        fonts.add(str(name))
                except Exception:
                    continue
    except Exception:
        pass

    # 테이블
    try:
        if int(getattr(shape, "HasTable", 0)) == MSO_TRUE:
            table = shape.Table
            for r in range(1, table.Rows.Count + 1):
                for c in range(1, table.Columns.Count + 1):
                    try:
                        tf = table.Cell(r, c).Shape.TextFrame
                        if int(tf.HasText) == MSO_TRUE:
                            text = tf.TextRange.Text.rstrip("\r\n\v")
                            for i in range(1, len(text) + 1):
                                name = tf.TextRange.Characters(i, 1).Font.Name
                                if name:
                                    fonts.add(str(name))
                    except Exception:
                        continue
    except Exception:
        pass


def _map_fonts_by_rule(fonts: list) -> dict:
    result: dict = {}
    for font in fonts:
        lower = font.lower()
        kr = _DEFAULT_KR_FONT
        for keywords, mapped in _RULE_BASED:
            if any(kw in lower for kw in keywords):
                kr = mapped
                break
        result[font] = kr
        print(f"  [font_analyzer_microsoft] 신규 폰트 매핑: {font!r} → {kr}")
    return result


def _load_font_map(path: str) -> dict:
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"__default__": _DEFAULT_KR_FONT}


def _save_font_map(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
