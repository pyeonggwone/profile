"""
dict_manager.py — STEP 3 보조: 번역 사전 로드/업데이트 + 신규 용어 LLM 추출
슬라이드 번역 완료 후 호출하여 translation_dict.json 에 신규 용어를 추가한다.
"""
import json
import os

from openai import AzureOpenAI


def load(dict_path: str) -> dict:
    """translation_dict.json 로드. 없으면 기본 구조 반환."""
    if os.path.exists(dict_path):
        with open(dict_path, encoding="utf-8") as f:
            return json.load(f)
    return {"version": 1, "entries": {}, "protected_terms": []}


def save(dict_path: str, data: dict) -> None:
    with open(dict_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def update_from_slide(
    dict_path: str,
    original_text: str,
    llm_client: AzureOpenAI,
    model: str,
) -> None:
    """
    슬라이드 원문 텍스트를 LLM에 전달하여 사전에 없는 신규 용어를 추출하고
    translation_dict.json entries에 추가한다.
    기존 entries 덮어쓰기 금지.
    """
    data = load(dict_path)
    existing_keys = list(data.get("entries", {}).keys())
    keys_str = json.dumps(existing_keys, ensure_ascii=False)

    prompt = (
        "아래 원문 텍스트에서 IT·기술 용어를 추출하고 한국어 번역을 JSON 객체로 반환하라.\n"
        "단, 이미 다음 키 목록에 있는 용어는 제외하라.\n"
        f"기존 키 목록: {keys_str}\n\n"
        f"원문:\n{original_text}\n\n"
        "결과 형식: {{\"영어 용어\": \"한국어 번역\", ...}}\n"
        "신규 용어가 없으면 빈 객체 {{}} 를 반환하라."
    )

    response = llm_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content
    new_terms: dict = json.loads(content)

    if not new_terms:
        return

    entries = data.setdefault("entries", {})
    added = 0
    for k, v in new_terms.items():
        if k not in entries:  # 덮어쓰기 금지
            entries[k] = v
            added += 1

    if added:
        save(dict_path, data)
        print(f"[dict_manager] 신규 용어 {added}개 추가")
