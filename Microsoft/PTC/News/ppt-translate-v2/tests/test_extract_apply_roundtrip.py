"""extract → apply 라운드트립: 텍스트 교체가 PPTX 구조를 깨지 않는지 검증."""
from __future__ import annotations

from pathlib import Path

import pytest

from ppt_translate.apply.inplace import apply_translations
from ppt_translate.extract.shapes import extract_segments

FIXTURE = Path(__file__).parent / "fixtures" / "sample.pptx"


@pytest.mark.skipif(not FIXTURE.exists(), reason="fixture 미배치")
def test_roundtrip(tmp_path: Path) -> None:
    segments = extract_segments(FIXTURE)
    assert segments, "샘플 PPTX 에 텍스트 없음"

    translated = [{**s, "translated": f"[KO]{s['text']}"} for s in segments]
    out = tmp_path / "out.pptx"
    apply_translations(FIXTURE, translated, out)

    after = extract_segments(out)
    assert len(after) == len(segments)
    for a, b in zip(after, translated, strict=True):
        assert a["text"] == b["translated"]
