from __future__ import annotations

import json
import os
import pathlib
import re
import time

from openai import OpenAI


def load_env(path: pathlib.Path) -> None:
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def is_translatable_text(value: str) -> bool:
    text = " ".join(value.split())
    if len(text) < 3:
        return False
    letters = re.findall(r"[A-Za-z]", text)
    if len(letters) < 2:
        return False
    if re.fullmatch(r"[A-Z0-9_#./:,()\-\s]+", text) and len(text.split()) <= 3:
        return False
    return True


def latest_job() -> pathlib.Path:
    jobs = [path for path in pathlib.Path("work").iterdir() if path.is_dir()]
    return max(jobs, key=lambda path: path.stat().st_mtime)


def tm_sources() -> set[str]:
    import sqlite3

    tm_path = pathlib.Path("work") / "tm.sqlite"
    if not tm_path.exists():
        return set()
    with sqlite3.connect(tm_path) as database:
        return {row[0] for row in database.execute("SELECT src FROM tm")}


def main() -> None:
    load_env(pathlib.Path(".env"))
    batch_size = int(os.environ.get("SMOKE_BATCH_SIZE") or "10")
    job = latest_job()
    data = json.loads((job / "state" / "segments.json").read_text(encoding="utf-8"))
    skip_sources = tm_sources() if os.environ.get("SMOKE_SKIP_TM") == "1" else set()
    items = [
        {"id": item["id"], "source": item["source"]}
        for item in data.get("segments", [])
        if is_translatable_text(str(item.get("source") or "")) and item.get("source") not in skip_sources
    ][:batch_size]
    messages = [
        {"role": "system", "content": "Translate from en to ko. Return only a JSON object mapping id to translated text."},
        {"role": "user", "content": json.dumps([{"id": item["id"], "text": item["source"]} for item in items], ensure_ascii=False)},
    ]
    model = os.environ.get("OPENAI_MODEL") or "gpt-4.1-mini"
    start = time.time()
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), timeout=45.0, max_retries=0)
    response = client.chat.completions.create(model=model, temperature=0, messages=messages)
    content = response.choices[0].message.content or ""
    print(f"job={job}")
    print(f"model={model}")
    print(f"items={len(items)} elapsed={time.time() - start:.2f} chars={len(content)}")
    print(content[:1000])


if __name__ == "__main__":
    main()