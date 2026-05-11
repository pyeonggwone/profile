from __future__ import annotations

import os
import pathlib
import time

from openai import OpenAI


def load_env(path: pathlib.Path) -> None:
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def main() -> None:
    load_env(pathlib.Path(".env"))
    model = os.environ.get("OPENAI_MODEL") or "gpt-4.1-mini"
    start = time.time()
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"), timeout=20.0, max_retries=0)
    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[{"role": "user", "content": "Translate to Korean: Worldwide Personal Computing Device Tracker"}],
    )
    print(f"model={model}")
    print(f"elapsed={time.time() - start:.2f}")
    print(response.choices[0].message.content or "")


if __name__ == "__main__":
    main()