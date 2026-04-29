"""APPLY: 원본 PPTX 복사 → 동일 path 의 <a:t> 텍스트만 교체."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from ppt_translate.ooxml import NS
from ppt_translate.ooxml.package import (
    copy_pptx,
    iter_slide_xml,
    parse_xml,
    replace_xml_in_pptx,
    serialize_xml,
)


def apply_translations(src_pptx: Path, translated: list[dict], out_pptx: Path) -> None:
    # slide → {index: translated_text}
    by_slide: dict[str, dict[int, str]] = defaultdict(dict)
    for item in translated:
        by_slide[item["slide"]][item["index"]] = item["translated"]

    copy_pptx(src_pptx, out_pptx)

    replacements: dict[str, bytes] = {}
    for slide_name, data in iter_slide_xml(out_pptx):
        mapping = by_slide.get(slide_name)
        if not mapping:
            continue
        root = parse_xml(data)
        for idx, t in enumerate(root.iter(f"{{{NS['a']}}}t")):
            if idx in mapping:
                t.text = mapping[idx]
        replacements[slide_name] = serialize_xml(root)

    if replacements:
        replace_xml_in_pptx(out_pptx, replacements)
