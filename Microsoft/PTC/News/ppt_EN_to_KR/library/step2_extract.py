"""
step2_extract.py — STEP 2: 슬라이드별 컴포넌트 직렬화 + 폰트 분석

처리 흐름:
  1. extractor.py   : 원본 슬라이드별 Shape 추출 → slide_{N}_component_en.json
  2. font_analyzer.py: 슬라이드별 폰트 수집, 신규 폰트 매핑 → slide_{N}_font_en.json

출력:
  work/components_en/{stem}/slide_{N}_component_en.json
  work/components_en/{stem}/slide_{N}_font_en.json
  work/img/{stem}/slide_{N}/*.jpg
"""
from openai import AzureOpenAI
from pptx import Presentation

from library.config import Config
from library import extractor, font_analyzer


def run(pptx_path: str, cfg: Config, stem: str, client: AzureOpenAI) -> int:
    """
    컴포넌트 추출 + 폰트 분석을 실행하고, 슬라이드 총 수를 반환한다.

    Parameters
    ----------
    pptx_path : 원본 .pptx 절대 경로
    cfg       : Config 인스턴스
    stem      : 확장자 없는 파일명
    client    : AzureOpenAI 클라이언트 (폰트 LLM 매핑에 사용)

    Returns
    -------
    int : 슬라이드 총 수
    """
    total_slides = _count_slides(pptx_path)

    print(f"[STEP 2-1] 컴포넌트 추출 ({total_slides} 슬라이드)")
    extractor.extract(pptx_path, cfg.work_dir, stem)

    print(f"[STEP 2-2] 폰트 분석")
    font_analyzer.analyze(
        pptx_path,
        cfg.work_dir,
        stem,
        cfg.font_map_path,
        client,
        cfg.model,
    )

    print(f"[STEP 2] 완료")
    return total_slides


def _count_slides(pptx_path: str) -> int:
    prs = Presentation(pptx_path)
    return len(prs.slides)
