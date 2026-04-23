"""
step4_guide.py — STEP 4: 설명자료 PPTX 생성 (기본 실행 제외)

처리 흐름:
  - template_guide.pptx 없으면 자동 스킵
  - doc_generator.py : STEP 2 component JSON + 템플릿 레이아웃 → LLM → 슬라이드 생성

출력:
  kr/{stem}_GUIDE.pptx
"""
import os

from openai import AzureOpenAI

from library.config import Config
from library import doc_generator


def run(cfg: Config, stem: str, client: AzureOpenAI, total_slides: int) -> None:
    """
    템플릿 기반 설명자료 PPTX를 생성한다.
    template_guide.pptx 가 없으면 스킵.

    Parameters
    ----------
    cfg          : Config 인스턴스
    stem         : 확장자 없는 파일명
    client       : AzureOpenAI 클라이언트
    total_slides : STEP 2에서 반환된 슬라이드 총 수
    """
    if not os.path.exists(cfg.guide_template_path):
        print(f"[STEP 4] template_guide.pptx 없음 → 스킵")
        return

    print(f"[STEP 4] 설명자료 생성 시작")
    comp_dir = os.path.join(cfg.work_dir, "components")
    doc_generator.generate(
        template_path = cfg.guide_template_path,
        comp_dir      = comp_dir,
        filename_stem = stem,
        kr_dir        = cfg.kr_dir,
        llm_client    = client,
        model         = cfg.model,
        total_slides  = total_slides,
    )
    print(f"[STEP 4] 완료 → {stem}_GUIDE.pptx")
