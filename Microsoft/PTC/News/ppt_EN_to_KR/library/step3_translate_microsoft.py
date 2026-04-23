"""
step3_translate_microsoft.py — STEP 3 (Microsoft 공식 엔진 버전)

translator_microsoft.translate 를 호출하여 LLM 번역 + COM 치환을 수행한다.
"""
from __future__ import annotations

import os

from library.config import Config
from library import translator_microsoft


def run(cfg: Config, stem: str, client) -> None:
    kr_path = os.path.join(cfg.kr_dir, f"{stem}_KO.pptx")

    print(f"[STEP 3 microsoft] 번역 + COM 재생성 시작")
    translator_microsoft.translate(
        kr_pptx_path = kr_path,
        work_dir     = cfg.work_dir,
        filename_stem= stem,
        dict_path    = cfg.dict_path,
        llm_client   = client,
        model        = cfg.model,
    )
    print(f"[STEP 3 microsoft] 완료 → {os.path.basename(kr_path)}")
