"""LLM 기반 번역. TM 조회 → 미스만 배치 호출."""
from __future__ import annotations

import json

from ppt_translate.config import settings
from ppt_translate.translate import glossary, memory

_BATCH_SIZE = 30


def translate_segments(segments: list[dict]) -> list[dict]:
    """
    입력: extract 결과 [{slide, index, text}, ...]
    출력: [{slide, index, text, translated}, ...]
    """
    gloss = glossary.load()
    results: list[dict] = []
    pending: list[dict] = []

    for seg in segments:
        cached = memory.lookup(seg["text"])
        if cached is not None:
            results.append({**seg, "translated": cached})
        else:
            pending.append(seg)

    for i in range(0, len(pending), _BATCH_SIZE):
        batch = pending[i : i + _BATCH_SIZE]
        translations = _call_llm([s["text"] for s in batch], gloss)
        for seg, tgt in zip(batch, translations, strict=True):
            memory.store(seg["text"], tgt, model=settings.llm_model)
            results.append({**seg, "translated": tgt})

    # 원래 순서로 정렬 (slide → index)
    results.sort(key=lambda x: (x["slide"], x["index"]))
    return results


def _call_llm(texts: list[str], gloss: dict[str, dict]) -> list[str]:
    """LiteLLM 으로 OpenAI/Azure 통합 호출. JSON 배열로 응답 강제."""
    from litellm import completion

    glossary_lines = [
        f"- {t}: {info['translation']}" + (" (protected)" if info["protected"] else "")
        for t, info in gloss.items()
    ]
    system = (
        f"You translate {settings.source_lang} to {settings.target_lang}.\n"
        "Return a JSON array of translations matching the input order. "
        "Do not translate terms marked (protected). Keep numbers, URLs, code unchanged.\n"
        "Glossary:\n" + ("\n".join(glossary_lines) if glossary_lines else "(none)")
    )
    user = json.dumps(texts, ensure_ascii=False)

    resp = completion(
        model=settings.llm_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    content = resp["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    if isinstance(parsed, dict):
        # {"translations": [...]} 같은 래핑 허용
        for v in parsed.values():
            if isinstance(v, list):
                parsed = v
                break
    if not isinstance(parsed, list) or len(parsed) != len(texts):
        raise ValueError(f"LLM 응답 형식 오류: {content[:200]}")
    return [str(x) for x in parsed]
