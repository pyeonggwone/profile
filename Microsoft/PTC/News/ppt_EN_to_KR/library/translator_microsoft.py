"""
translator_microsoft.py — STEP 3 (Microsoft 공식 엔진 버전)

translator.py 와 동일한 LLM 배치 번역 흐름을 사용하되,
STEP 3-2 의 in-place 치환을 ooxml_replacer 대신
com_replacer_microsoft (PowerPoint COM) 로 위임한다.

LLM 호출/사전 갱신/검증 로직은 translator.py 의 함수를 재사용한다.
"""
from __future__ import annotations

import json
import os
import traceback

from openai import AzureOpenAI
from tqdm import tqdm

from library import dict_manager, logger, translator
from library import com_replacer_microsoft


def translate(
    kr_pptx_path: str,
    work_dir: str,
    filename_stem: str,
    dict_path: str,
    llm_client: AzureOpenAI,
    model: str,
) -> None:
    """STEP 3-1 LLM 번역 (translator.py 로직 재사용) + STEP 3-2 COM 치환."""
    log = logger.get()

    comp_en_dir    = os.path.join(work_dir, "components_en", filename_stem)
    comp_kr_dir    = os.path.join(work_dir, "components_kr", filename_stem)
    translated_dir = os.path.join(work_dir, "translated",    filename_stem)
    os.makedirs(comp_kr_dir, exist_ok=True)
    os.makedirs(translated_dir, exist_ok=True)

    translation_data = dict_manager.load(dict_path)

    # 슬라이드 총 수: components_en 폴더의 slide_*_component_en.json 갯수로 산출
    en_files = [
        f for f in os.listdir(comp_en_dir)
        if f.startswith("slide_") and f.endswith("_component_en.json")
    ]
    total = len(en_files)

    _TEST_SLIDE_LIMIT = 6   # translator.py 와 동일
    _BATCH_SIZE       = 10
    target_total = min(total, _TEST_SLIDE_LIMIT)

    done_path  = os.path.join(comp_kr_dir, "done.json")
    done_state = translator._load_done(done_path)

    print(f"[STEP 3-1 microsoft] 번역 JSON 생성 ({total} 슬라이드, 테스트: 최대 {_TEST_SLIDE_LIMIT}, 배치 {_BATCH_SIZE})")

    slide_indices = list(range(1, target_total + 1))
    batches = [slide_indices[i:i + _BATCH_SIZE] for i in range(0, len(slide_indices), _BATCH_SIZE)]

    for batch in tqdm(batches, desc="번역 배치"):
        en_items: list = []
        for slide_idx in batch:
            comp_en_path = os.path.join(comp_en_dir, f"slide_{slide_idx}_component_en.json")
            font_en_path = os.path.join(comp_en_dir, f"slide_{slide_idx}_font_en.json")
            if not os.path.exists(comp_en_path):
                log.warning(f"  slide_{slide_idx}: component_en JSON 없음, 건너뜀")
                continue
            with open(comp_en_path, encoding="utf-8") as f:
                comp_en = json.load(f)
            font_data = None
            if os.path.exists(font_en_path):
                with open(font_en_path, encoding="utf-8") as f:
                    font_data = json.load(f)
            en_items.append((slide_idx, comp_en, font_data))

        if not en_items:
            continue

        log.info(f"[STEP 3-1 microsoft] 배치 번역 시작: slides {[s for s, _, _ in en_items]}")
        try:
            translated_map = translator._translate_slides_batch(
                [(s, c) for s, c, _ in en_items],
                translation_data, llm_client, model,
            )
        except Exception as e:
            log.error(f"  배치 LLM 번역 실패: {e}")
            log.debug(traceback.format_exc())
            translated_map = {s: c for s, c, _ in en_items}

        for slide_idx, comp_en, font_data in en_items:
            comp_kr = translated_map.get(slide_idx, comp_en)
            comp_kr_path = os.path.join(comp_kr_dir, f"slide_{slide_idx}_component_kr.json")
            font_kr_path = os.path.join(comp_kr_dir, f"slide_{slide_idx}_font_kr.json")

            with open(comp_kr_path, "w", encoding="utf-8") as f:
                json.dump(comp_kr, f, ensure_ascii=False, indent=2)
            if font_data is not None:
                with open(font_kr_path, "w", encoding="utf-8") as f:
                    json.dump(font_data, f, ensure_ascii=False, indent=2)

            done_state["slides"][str(slide_idx)] = {
                "text_boxes": comp_kr.get("text_boxes", []),
                "tables":     comp_kr.get("tables", []),
                "notes":      comp_kr.get("notes", ""),
            }

            original_text = translator._collect_text(comp_en)
            if original_text.strip():
                try:
                    dict_manager.update_from_slide(dict_path, original_text, llm_client, model)
                except Exception as e:
                    log.warning(f"  slide_{slide_idx} 사전 업데이트 실패: {e}")

        with open(done_path, "w", encoding="utf-8") as f:
            json.dump(done_state, f, ensure_ascii=False, indent=2)
        log.info(f"  done.json 갱신 — 누적: {sorted(done_state['slides'].keys(), key=int)}")

    # ── STEP 3-2: COM 기반 치환 ────────────────────────────
    print(f"[STEP 3-2 microsoft] COM 직접 치환 ({total} 슬라이드, 테스트: 최대 {_TEST_SLIDE_LIMIT}장)")
    statuses = com_replacer_microsoft.replace_pptx(
        kr_pptx_path  = kr_pptx_path,
        comp_kr_dir   = comp_kr_dir,
        translated_dir= translated_dir,
        slide_limit   = _TEST_SLIDE_LIMIT,
    )
    for sidx, status in statuses.items():
        failed = [i for i in status.get("items", []) if not i.get("ok")]
        log.info(
            f"  slide_{sidx} 완료 — 성공 {len(status.get('items', [])) - len(failed)}, 실패 {len(failed)}"
        )
        for item in failed:
            log.warning(f"    ✗ {item['id']} ({item['type']}): {item.get('error', '')}")

    log.info(f"[STEP 3 microsoft] 저장 완료 → {kr_pptx_path}")

    # 검증 (translator._validate 재사용)
    translator._validate(comp_kr_dir, translated_dir, total)
