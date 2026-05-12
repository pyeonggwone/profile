from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _read_dotenv(root: Path) -> dict[str, str]:
    dotenv = root / ".env"
    if not dotenv.exists():
        return {}
    values: dict[str, str] = {}
    for line in dotenv.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass
class Config:
    root: Path
    source_lang: str
    target_lang: str
    openai_provider: str
    openai_model: str
    openai_api_key: str
    azure_openai_api_key: str
    azure_openai_endpoint: str
    azure_openai_api_version: str
    azure_openai_deployment: str
    openai_chunk_size: int
    translation_parallelism: int
    openai_retry_max: int
    openai_retry_base_ms: int
    openai_timeout_secs: int
    input_dir: Path
    output_dir: Path
    work_dir: Path
    glossary_path: Path
    state_db_path: Path
    tm_db_path: Path
    terms_db_path: Path
    pdf_translation_render_mode: str
    font_regular: Path | None
    font_bold: Path | None
    font_fallback: Path | None
    encode_unsupported_policy: str
    rebuild_mismatch_policy: str
    strict_tools: bool
    allow_degraded: bool
    keep_work: bool


def load_config(root: Path, source_lang: str | None = None, target_lang: str | None = None, model: str | None = None) -> Config:
    root = root.resolve()
    dotenv = _read_dotenv(root)

    def get(key: str, default: str = "") -> str:
        return os.environ.get(key) or dotenv.get(key) or default

    def path_value(key: str, default: str) -> Path:
        value = Path(get(key, default))
        return value if value.is_absolute() else root / value

    def optional_path(key: str) -> Path | None:
        value = get(key)
        if not value:
            return None
        path = Path(value)
        return path if path.is_absolute() else root / path

    return Config(
        root=root,
        source_lang=source_lang or get("SOURCE_LANG", "en"),
        target_lang=target_lang or get("TARGET_LANG", "ko"),
        openai_provider=get("OPENAI_PROVIDER", "openai"),
        openai_model=model or get("OPENAI_MODEL", "gpt-4o-mini"),
        openai_api_key=get("OPENAI_API_KEY"),
        azure_openai_api_key=get("AZURE_OPENAI_API_KEY"),
        azure_openai_endpoint=get("AZURE_OPENAI_ENDPOINT"),
        azure_openai_api_version=get("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
        azure_openai_deployment=get("AZURE_OPENAI_DEPLOYMENT"),
        openai_chunk_size=int(get("OPENAI_CHUNK_SIZE", "100")),
        translation_parallelism=int(get("TRANSLATION_PARALLELISM", "0")),
        openai_retry_max=int(get("OPENAI_RETRY_MAX", "3")),
        openai_retry_base_ms=int(get("OPENAI_RETRY_BASE_MS", "1000")),
        openai_timeout_secs=int(get("OPENAI_TIMEOUT_SECS", "300")),
        input_dir=path_value("INPUT_DIR", "input"),
        output_dir=path_value("OUTPUT_DIR", "output"),
        work_dir=path_value("WORK_DIR", "work"),
        glossary_path=path_value("GLOSSARY_PATH", "glossary.csv"),
        state_db_path=path_value("STATE_DB_PATH", "work/db/state.sqlite"),
        tm_db_path=path_value("TM_DB_PATH", "work/db/tm.sqlite"),
        terms_db_path=path_value("TERMS_DB_PATH", "work/db/terms.sqlite"),
        pdf_translation_render_mode=get("PDF_TRANSLATION_RENDER_MODE", "text-compose"),
        font_regular=optional_path("FONT_REGULAR"),
        font_bold=optional_path("FONT_BOLD"),
        font_fallback=optional_path("FONT_FALLBACK"),
        encode_unsupported_policy=get("ENCODE_UNSUPPORTED_POLICY", "preserve-original"),
        rebuild_mismatch_policy=get("REBUILD_MISMATCH_POLICY", "preserve-original"),
        strict_tools=_bool(get("STRICT_TOOLS"), False),
        allow_degraded=_bool(get("ALLOW_DEGRADED"), False),
        keep_work=_bool(get("KEEP_WORK"), True),
    )