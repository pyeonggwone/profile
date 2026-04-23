"""
step1_clear_microsoft.py — STEP 1 (Microsoft 공식 엔진 버전)

원본을 kr/ 작업본으로 복사한다. (in-place 치환 전략이라 Shape 클리어 없음)
COM 호출 자체는 불필요하므로 step1_clear.py 와 동일한 단순 복사 로직.
파일명 컨벤션을 일치시키기 위해 별도 파일로 둔다.
"""
from __future__ import annotations

import os
import shutil

from library.config import Config


def run(pptx_path: str, cfg: Config, stem: str) -> None:
    kr_path = _kr_path(cfg, stem)
    shutil.copy2(pptx_path, kr_path)
    print(f"[STEP 1 microsoft] 복사: {os.path.basename(pptx_path)} → {os.path.basename(kr_path)}")


def _kr_path(cfg: Config, stem: str) -> str:
    os.makedirs(cfg.kr_dir, exist_ok=True)
    return os.path.join(cfg.kr_dir, f"{stem}_KO.pptx")
