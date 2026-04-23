"""EXTRACT: PPTX 슬라이드 XML 에서 <a:t> 텍스트 노드를 모두 수집."""
from __future__ import annotations

from pathlib import Path

from ppt_translate.ooxml import NS
from ppt_translate.ooxml.package import iter_slide_xml, parse_xml


def extract_segments(pptx_path: Path) -> list[dict]:
    """
    각 텍스트 런(<a:t>)을 식별 가능한 위치 정보와 함께 리스트로 반환.

    반환 항목:
      {
        "slide": "ppt/slides/slide1.xml",
        "index": 0,         # 슬라이드 내 <a:t> 출현 순서
        "text": "Hello",
      }
    """
    segments: list[dict] = []
    for slide_name, data in iter_slide_xml(Path(pptx_path)):
        root = parse_xml(data)
        for idx, t in enumerate(root.iter(f"{{{NS['a']}}}t")):
            text = t.text or ""
            if not text.strip():
                continue
            segments.append({"slide": slide_name, "index": idx, "text": text})
    return segments
