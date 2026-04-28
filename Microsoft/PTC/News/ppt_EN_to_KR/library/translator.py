"""
translator.py — STEP 3: 슬라이드별 JSON 기반 LLM 번역 + kr/ 슬라이드 재생성
STEP 3-1: components_en/ JSON → LLM 번역 → components_kr/ JSON 생성
STEP 3-2: components_kr/ JSON → ooxml_replacer로 슬라이드 XML <a:t> 1:1 치환
"""
import json
import os
import traceback

from openai import AzureOpenAI
from pptx import Presentation
from tqdm import tqdm

from library import dict_manager, logger, ooxml_replacer


def translate(
    kr_pptx_path: str,
    work_dir: str,
    filename_stem: str,
    dict_path: str,
    llm_client: AzureOpenAI,
    model: str,
) -> None:
    """
    STEP 3-1: components_en/ JSON을 번역하여 components_kr/ JSON을 생성한다.
    STEP 3-2: components_kr/ JSON을 이용해 kr/ 슬라이드에 Shape를 삽입하고 저장한다.
    """
    log = logger.get()
    prs = Presentation(kr_pptx_path)
    comp_en_dir = os.path.join(work_dir, "components_en", filename_stem)
    comp_kr_dir = os.path.join(work_dir, "components_kr", filename_stem)
    translated_dir = os.path.join(work_dir, "translated", filename_stem)
    os.makedirs(comp_kr_dir, exist_ok=True)
    os.makedirs(translated_dir, exist_ok=True)

    translation_data = dict_manager.load(dict_path)
    total = len(prs.slides)
    _TEST_SLIDE_LIMIT = 6  # TODO: 테스트 완료 후 제거
    _BATCH_SIZE = 10  # 슬라이드 배치 크기 (LLM 1회 호출당 슬라이드 수)
    done_path = os.path.join(comp_kr_dir, "done.json")
    done_state = _load_done(done_path)

    # ── STEP 3-1: EN JSON → KR JSON 배치 번역 ────────────────
    target_total = min(total, _TEST_SLIDE_LIMIT)
    print(f"[STEP 3-1] 번역 JSON 생성 ({total} 슬라이드, 테스트: 최대 {_TEST_SLIDE_LIMIT}장, 배치 {_BATCH_SIZE})")

    slide_indices = list(range(1, target_total + 1))
    batches = [slide_indices[i:i + _BATCH_SIZE] for i in range(0, len(slide_indices), _BATCH_SIZE)]

    for batch in tqdm(batches, desc="번역 배치"):
        # 배치 내 EN 컴포넌트 로드
        en_items: list = []  # [(slide_idx, comp_en, font_en_data_or_None), ...]
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

        log.info(f"[STEP 3-1] 배치 번역 시작: slides {[s for s, _, _ in en_items]}")

        # LLM 배치 번역
        try:
            translated_map = _translate_slides_batch(
                [(s, c) for s, c, _ in en_items],
                translation_data, llm_client, model,
            )
        except Exception as e:
            log.error(f"  배치 LLM 번역 실패: {e}")
            log.debug(traceback.format_exc())
            translated_map = {s: c for s, c, _ in en_items}  # 원문 fallback

        # 슬라이드별 KR JSON 저장 + done.json 갱신
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
                "tables": comp_kr.get("tables", []),
                "notes": comp_kr.get("notes", ""),
            }

            # 사전 업데이트
            original_text = _collect_text(comp_en)
            if original_text.strip():
                try:
                    dict_manager.update_from_slide(dict_path, original_text, llm_client, model)
                except Exception as e:
                    log.warning(f"  slide_{slide_idx} 사전 업데이트 실패: {e}")

        # 배치 단위 done.json 저장 (중단 시 복구 가능)
        with open(done_path, "w", encoding="utf-8") as f:
            json.dump(done_state, f, ensure_ascii=False, indent=2)
        log.info(f"  done.json 갱신 — 누적 슬라이드: {sorted(done_state['slides'].keys(), key=int)}")

    # ── STEP 3-2: KR JSON → PPTX 텍스트 in-place 치환 (OOXML 직접 조작) ───
    print(f"[STEP 3-2] OOXML 직접 치환 ({total} 슬라이드, 테스트: 최대 {_TEST_SLIDE_LIMIT}장)")
    statuses = ooxml_replacer.replace_pptx(
        kr_pptx_path  = kr_pptx_path,
        comp_kr_dir   = comp_kr_dir,
        translated_dir= translated_dir,
        slide_limit   = _TEST_SLIDE_LIMIT,
    )
    for sidx, status in statuses.items():
        failed = [i for i in status.get("items", []) if not i.get("ok")]
        log.info(f"  slide_{sidx} 완료 — 성공: {len(status.get('items',[]))-len(failed)}, 실패: {len(failed)}")
        if failed:
            for item in failed:
                log.warning(f"    ✗ {item['id']} ({item['type']}): {item.get('error','')}")

    log.info(f"[STEP 3] 저장 완료 → {kr_pptx_path}")

    # 검증
    _validate(comp_kr_dir, translated_dir, total)


# ──────────────────────────────────────────────
# LLM 번역
# ──────────────────────────────────────────────

def _translate_slides_batch(
    slides: list,
    translation_data: dict,
    client,
    model: str,
) -> dict:
    """슬라이드 여러 장을 한 번의 LLM 호출로 번역.

    Parameters
    ----------
    slides : list of (slide_idx, comp_en) 튜플

    Returns
    -------
    dict : {slide_idx: comp_kr}
    """
    log = logger.get()
    if not slides:
        return {}

    payload_slides = []
    has_text_slides = []
    empty_results: dict = {}
    for slide_idx, comp in slides:
        text_boxes = comp.get("text_boxes", [])
        tables = comp.get("tables", [])
        notes = comp.get("notes", "")
        if not text_boxes and not tables and not notes:
            empty_results[slide_idx] = comp
            continue
        payload_slides.append({
            "slide_num": slide_idx,
            "text_boxes": text_boxes,
            "tables": tables,
            "notes": notes,
        })
        has_text_slides.append((slide_idx, comp))

    if not payload_slides:
        return empty_results

    entries = translation_data.get("entries", {})
    protected = translation_data.get("protected_terms", [])
    dict_hint = json.dumps(entries, ensure_ascii=False) if entries else "{}"
    protected_hint = ", ".join(protected) if protected else ""

    prompt = (
        "아래 JSON의 slides 배열에 포함된 모든 슬라이드의 텍스트 필드를 영어→한국어로 번역하라.\n"
        "규칙:\n"
        f"1. protected_terms 목록의 단어는 번역하지 말고 원문 유지: [{protected_hint}]\n"
        f"2. 번역 사전 참조 (우선 적용): {dict_hint}\n"
        "3. 영어 단어가 하나라도 있으면 번역한다.\n"
        "4. 텍스트가 이미 한국어이면 그대로 둔다.\n"
        "5. 구조(키, 배열 순서, slide_num)는 절대 변경하지 말고, 텍스트 값만 교체하라.\n"
        "6. 결과는 입력과 동일한 JSON 구조 ({\"slides\": [...]})로만 반환하라.\n\n"
        f"입력:\n{json.dumps({'slides': payload_slides}, ensure_ascii=False)}"
    )

    log.debug(f"  배치 LLM 요청 — 모델: {model}, 슬라이드 수: {len(payload_slides)}")

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    log.debug(f"  배치 LLM 응답 ({len(raw)} chars)")

    translated_payload: dict = json.loads(raw)
    translated_slides = translated_payload.get("slides", [])

    # slide_num 기반 매핑
    by_num = {item.get("slide_num"): item for item in translated_slides}

    result: dict = dict(empty_results)
    for slide_idx, comp in has_text_slides:
        translated = by_num.get(slide_idx)
        if translated is None:
            log.warning(f"  slide_{slide_idx}: LLM 응답에 누락, 원문 유지")
            result[slide_idx] = comp
            continue
        merged = dict(comp)
        if "text_boxes" in translated:
            merged["text_boxes"] = translated["text_boxes"]
        if "tables" in translated:
            merged["tables"] = translated["tables"]
        if "notes" in translated:
            merged["notes"] = translated["notes"]
        result[slide_idx] = merged
    return result


# ──────────────────────────────────────────────
# 유틸
# ──────────────────────────────────────────────

def _load_done(done_path: str) -> dict:
    """done.json을 로드하거나 빈 구조 반환."""
    if os.path.exists(done_path):
        try:
            with open(done_path, encoding="utf-8") as f:
                data = json.load(f)
            if "slides" not in data:
                data["slides"] = {}
            return data
        except Exception:
            pass
    return {"slides": {}}


def _collect_text(comp: dict) -> str:
    parts = []
    for tb in comp.get("text_boxes", []):
        for para in tb.get("paragraphs", []):
            parts.append(para.get("text", ""))
    for tbl in comp.get("tables", []):
        for row in tbl.get("rows", []):
            for cell in row:
                parts.append(cell.get("text", ""))
    if comp.get("notes"):
        parts.append(comp["notes"])
    return "\n".join(parts)


def _validate(comp_kr_dir: str, translated_dir: str, total_slides: int) -> None:
    log = logger.get()
    log.info("\n[STEP 3] 검증 시작")
    missing = []
    for i in range(1, total_slides + 1):
        comp_path   = os.path.join(comp_kr_dir, f"slide_{i}_component_kr.json")
        status_path = os.path.join(translated_dir, f"slide_{i}.json")

        if not os.path.exists(comp_path):
            continue
        if not os.path.exists(status_path):
            missing.append(f"slide_{i}: status JSON 없음")
            continue

        with open(comp_path, encoding="utf-8") as f:
            comp = json.load(f)
        with open(status_path, encoding="utf-8") as f:
            status = json.load(f)

        comp_ids = set()
        for key in ("text_boxes", "images", "tables", "smartarts", "charts"):
            for item in comp.get(key, []):
                comp_ids.add(item["id"])

        done_ids = {item["id"] for item in status.get("items", []) if item.get("ok")}
        not_done = comp_ids - done_ids
        if not_done:
            missing.append(f"slide_{i}: 미처리 {not_done}")

    if missing:
        log.warning("[STEP 3] 미처리 항목:")
        for m in missing:
            log.warning(f"  - {m}")
    else:
        log.info("[STEP 3] 모든 슬라이드 정상 처리 완료")
