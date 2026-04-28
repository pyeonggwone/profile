"""
step3_translate.py — STEP 3: 슬라이드별 LLM 번역 + kr/ 재생성

처리 흐름:
  3-1. translator.py: components_en/ JSON 번역 → components_kr/ JSON 생성
       - slide_{N}_component_kr.json: 텍스트가 한국어로 번역된 컴포넌트 JSON
       - slide_{N}_font_kr.json: 폰트 매핑 복사
  3-2. translator.py: components_kr/ JSON 기반 → kr/ 슬라이드에 Shape 삽입
  3-3. dict_manager.py: 슬라이드 완료마다 신규 용어 추출 → translation_dict.json 업데이트
  3-4. 완료 후 미처리 항목 검증

출력:
  kr/{stem}_KO.pptx (번역 완료본)
  work/components_kr/{stem}/slide_{N}_component_kr.json (번역된 컴포넌트 JSON)
  work/components_kr/{stem}/slide_{N}_font_kr.json (폰트 매핑)
  work/translated/{stem}/slide_{N}.json (삽입 상태)
  translation_dict.json (신규 용어 누적)
"""
import os

from openai import AzureOpenAI

from library.config import Config
from library import translator


def run(cfg: Config, stem: str, client: AzureOpenAI) -> None:
    """
    kr/ 작업본에 번역된 Shape를 삽입하고 저장한다.

    Parameters
    ----------
    cfg    : Config 인스턴스
    stem   : 확장자 없는 파일명
    client : AzureOpenAI 클라이언트
    """
    kr_path = os.path.join(cfg.kr_dir, f"{stem}_KO.pptx")

    print(f"[STEP 3] 번역 + 재생성 시작")
    translator.translate(
        kr_pptx_path = kr_path,
        work_dir     = cfg.work_dir,
        filename_stem= stem,
        dict_path    = cfg.dict_path,
        llm_client   = client,
        model        = cfg.model,
    )
    print(f"[STEP 3] 완료 → {os.path.basename(kr_path)}")
