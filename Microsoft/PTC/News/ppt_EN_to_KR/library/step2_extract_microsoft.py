"""
step2_extract_microsoft.py — STEP 2 (Microsoft 공식 엔진 버전)

PowerPoint COM 으로 컴포넌트 추출 + 폰트 분석을 실행한다.
출력 JSON 스키마는 step2_extract.py 와 동일.
"""
from __future__ import annotations

from library.config import Config
from library import extractor_microsoft, font_analyzer_microsoft
from library.com_app_microsoft import powerpoint_app, open_presentation


def run(pptx_path: str, cfg: Config, stem: str, client) -> int:
    """컴포넌트 추출 + 폰트 분석을 실행하고 슬라이드 총 수를 반환한다.

    Parameters
    ----------
    client : LLM 클라이언트 (인터페이스 호환용, 실제로는 사용하지 않음)
    """
    total_slides = _count_slides(pptx_path)

    print(f"[STEP 2-1 microsoft] 컴포넌트 추출 ({total_slides} 슬라이드)")
    extractor_microsoft.extract(pptx_path, cfg.work_dir, stem)

    print(f"[STEP 2-2 microsoft] 폰트 분석")
    font_analyzer_microsoft.analyze(
        pptx_path,
        cfg.work_dir,
        stem,
        cfg.font_map_path,
        client,
        cfg.model,
    )

    print(f"[STEP 2 microsoft] 완료")
    return total_slides


def _count_slides(pptx_path: str) -> int:
    with powerpoint_app() as app:
        with open_presentation(app, pptx_path, read_only=True) as prs:
            return prs.Slides.Count
