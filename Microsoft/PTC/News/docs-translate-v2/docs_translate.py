# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pywin32>=306; sys_platform == 'win32'",
#   "litellm>=1.50",
#   "openai>=1.40",
#   "pydantic-settings>=2.5",
#   "typer>=0.12",
#   "rich>=13.8",
# ]
# ///
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

import typer
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich.console import Console

if sys.platform != "win32":
    raise SystemExit("docs-translate-v2 는 Microsoft Word COM Automation 이 필요하므로 Windows native Python 에서만 동작합니다.")

try:
    import litellm
except Exception:  # pragma: no cover
    litellm = None

try:
    import pythoncom
    import pywintypes
    import win32com.client
except Exception:  # pragma: no cover
    pythoncom = None
    pywintypes = None
    win32com = None

app = typer.Typer(no_args_is_help=True, add_completion=False)
tm_app = typer.Typer(no_args_is_help=True, add_completion=False)
app.add_typer(tm_app, name="tm")
console = Console()

SUPPORTED_LANGS = {"en", "kr", "ko", "ch", "zh", "jp", "ja"}
SUPPORTED_EXTENSIONS = {".docx", ".doc"}
TARGET_SUFFIX = {"kr": "KR", "ko": "KR", "ch": "CH", "zh": "CH", "jp": "JP", "ja": "JP", "en": "EN"}
LANG_NAME = {
    "en": "English",
    "kr": "Korean",
    "ko": "Korean",
    "ch": "Chinese",
    "zh": "Chinese",
    "jp": "Japanese",
    "ja": "Japanese",
}
BATCH_SIZE = 8
PLACEHOLDER_RE = re.compile(r"__DOCSTR_[A-Z]+_\d{4}__")
BLOCK_MARKER_RE = re.compile(r"^===\s*(\d+)\s*===\s*$", re.MULTILINE)
URL_RE = re.compile(r"\bhttps?://[^\s)\]}>\"]+")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
VARIABLE_RE = re.compile(r"(\$\{[^}\r\n]+\}|{{.*?}}|<%.*?%>)")
_FIELD_CODE_MARKERS = ("HYPERLINK", "PAGEREF", "REF ", "TOC", "PAGE", "NUMPAGES")

# Word constants used through late-bound COM.
WD_FORMAT_DOCUMENT_DEFAULT = 16
WD_FORMAT_DOCUMENT = 0
WD_DO_NOT_SAVE_CHANGES = 0


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    azure_openai_api_key: str | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_api_version: str = "2024-08-01-preview"
    azure_openai_deployment: str | None = None
    source_lang: str = "en"
    target_lang: str = "kr"
    work_dir: str = "work"
    tm_db_path: str = "work/tm.sqlite"
    glossary_path: str = "glossary.csv"
    kr_font: str = "맑은 고딕"

    @property
    def llm_model(self) -> str:
        if self.azure_openai_deployment:
            return f"azure/{self.azure_openai_deployment}"
        return self.openai_model


def settings() -> Settings:
    cfg = Settings()
    if cfg.openai_api_key:
        os.environ["OPENAI_API_KEY"] = cfg.openai_api_key
    if cfg.azure_openai_api_key:
        os.environ["AZURE_API_KEY"] = cfg.azure_openai_api_key
        os.environ["AZURE_OPENAI_API_KEY"] = cfg.azure_openai_api_key
    if cfg.azure_openai_endpoint:
        os.environ["AZURE_API_BASE"] = cfg.azure_openai_endpoint
        os.environ["AZURE_OPENAI_ENDPOINT"] = cfg.azure_openai_endpoint
    if cfg.azure_openai_api_version:
        os.environ["AZURE_API_VERSION"] = cfg.azure_openai_api_version
        os.environ["AZURE_OPENAI_API_VERSION"] = cfg.azure_openai_api_version
    return cfg


def normalize_lang(value: str) -> str:
    lowered = value.lower()
    if lowered not in SUPPORTED_LANGS:
        raise typer.BadParameter(f"지원 언어가 아닙니다: {value}. en/kr/ch/jp 중 하나를 사용하세요.")
    return {"ko": "kr", "zh": "ch", "ja": "jp"}.get(lowered, lowered)


@contextmanager
def word_app() -> Iterator[Any]:
    if pythoncom is None or win32com is None:
        raise RuntimeError("pywin32 가 필요합니다. Windows native Python/PowerShell 에서 실행하세요.")
    pythoncom.CoInitialize()
    app_obj = None
    try:
        app_obj = win32com.client.DispatchEx("Word.Application")
        app_obj.Visible = False
        app_obj.DisplayAlerts = 0
        yield app_obj
    finally:
        if app_obj is not None:
            try:
                app_obj.Quit(SaveChanges=WD_DO_NOT_SAVE_CHANGES)
            except Exception:
                pass
        pythoncom.CoUninitialize()


@contextmanager
def open_document(app_obj: Any, path: Path, read_only: bool) -> Iterator[Any]:
    doc = None
    try:
        doc = app_obj.Documents.Open(str(path.resolve()), ReadOnly=read_only, AddToRecentFiles=False, Visible=False)
        yield doc
    finally:
        if doc is not None:
            try:
                doc.Close(SaveChanges=WD_DO_NOT_SAVE_CHANGES)
            except Exception:
                pass


def load_glossary(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.exists():
        return [], []
    rows: list[dict[str, str]] = []
    protected_terms: list[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            term = (row.get("term") or "").strip()
            translation = (row.get("translation") or "").strip()
            protected = (row.get("protected") or "").strip().lower() == "true"
            if not term:
                continue
            rows.append({"term": term, "translation": translation, "protected": str(protected).lower()})
            if protected:
                protected_terms.append(term)
    return rows, protected_terms


class TokenMasker:
    def __init__(self, protected_terms: list[str]) -> None:
        self.protected_terms = protected_terms
        self.counter = 0

    def _token(self, kind: str, value: str, tokens: list[dict[str, str]]) -> str:
        self.counter += 1
        token = f"__DOCSTR_{kind.upper()}_{self.counter:04d}__"
        tokens.append({"id": token, "value": value, "kind": kind})
        return token

    def mask(self, text: str) -> tuple[str, list[dict[str, str]]]:
        tokens: list[dict[str, str]] = []
        masked = URL_RE.sub(lambda m: self._token("url", m.group(0), tokens), text)
        masked = EMAIL_RE.sub(lambda m: self._token("email", m.group(0), tokens), masked)
        masked = VARIABLE_RE.sub(lambda m: self._token("variable", m.group(0), tokens), masked)
        for term in sorted(self.protected_terms, key=len, reverse=True):
            if not term:
                continue
            pattern = re.compile(rf"(?<!\w){re.escape(term)}(?!\w)")
            masked = pattern.sub(lambda m: self._token("term", m.group(0), tokens), masked)
        return masked, tokens


def restore_tokens(text: str, tokens: list[dict[str, str]]) -> str:
    restored = text
    for token in tokens:
        restored = restored.replace(token["id"], token["value"])
    return restored


def clean_word_text(text: str) -> str:
    return text.replace("\r", "").replace("\x07", "").strip()


def paragraph_text_range(paragraph: Any) -> Any | None:
    rng = paragraph.Range.Duplicate
    if rng.End <= rng.Start:
        return None
    text = rng.Text or ""
    while rng.End > rng.Start and text.endswith(("\r", "\x07")):
        rng.End = rng.End - 1
        text = rng.Text or ""
    return rng if clean_word_text(text) else None


def is_field_code_range(rng: Any) -> bool:
    try:
        if int(rng.Fields.Count) > 0:
            return True
        text = (rng.Text or "").upper()
        return any(marker in text for marker in _FIELD_CODE_MARKERS)
    except Exception:
        return False


def update_document_fields(doc: Any) -> None:
    try:
        doc.Fields.Update()
    except Exception:
        pass
    try:
        for table_of_contents in doc.TablesOfContents:
            table_of_contents.Update()
    except Exception:
        pass


def iter_story_ranges(doc: Any) -> Iterator[tuple[int, int, Any]]:
    story_index = 0
    seen: set[tuple[int, int, int]] = set()
    root_stories: list[Any] = []
    try:
        root_stories.extend(doc.StoryRanges)
    except Exception:
        for story_type_value in range(1, 12):
            try:
                root_stories.append(doc.StoryRanges.Item(story_type_value))
            except Exception:
                continue
    for root_story in root_stories:
        story = root_story
        while story is not None:
            try:
                story_type = int(story.StoryType)
                key = (story_type, int(story.Start), int(story.End))
                if key not in seen:
                    seen.add(key)
                    yield story_type, story_index, story
                    story_index += 1
                story = story.NextStoryRange
            except Exception:
                break


def extract_segments(input_path: Path, cfg: Settings) -> dict[str, Any]:
    if input_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("docs-translate-v2 는 .docx / .doc 파일만 지원합니다.")
    glossary, protected_terms = load_glossary(Path(cfg.glossary_path))
    masker = TokenMasker(protected_terms)
    segments: list[dict[str, Any]] = []
    with word_app() as word:
        with open_document(word, input_path, read_only=True) as doc:
            for story_type, story_index, story in iter_story_ranges(doc):
                paragraph_count = int(story.Paragraphs.Count)
                console.print(f"EXTRACT story={story_type}/{story_index} paragraphs={paragraph_count}")
                for paragraph_index in range(1, paragraph_count + 1):
                    try:
                        paragraph = story.Paragraphs.Item(paragraph_index)
                        rng = paragraph_text_range(paragraph)
                        if rng is None or is_field_code_range(rng):
                            continue
                        raw_text = clean_word_text(rng.Text or "")
                        masked, tokens = masker.mask(raw_text)
                        segments.append({
                            "id": len(segments) + 1,
                            "path": ["story", story_type, story_index, "p", paragraph_index],
                            "text": masked,
                            "raw_text": raw_text,
                            "tokens": tokens,
                            "story_type": story_type,
                            "story_index": story_index,
                            "paragraph_index": paragraph_index,
                        })
                    except Exception as exc:
                        console.print(f"[yellow]skip paragraph story={story_type}/{story_index} p={paragraph_index}: {exc}[/yellow]")
    return {
        "version": 2,
        "engine": "word-com",
        "source_file": str(input_path),
        "source_lang": normalize_lang(cfg.source_lang),
        "target_lang": normalize_lang(cfg.target_lang),
        "glossary": glossary,
        "segments": segments,
    }


def init_tm(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tm (
                src_hash TEXT PRIMARY KEY,
                src TEXT NOT NULL,
                tgt TEXT NOT NULL,
                model TEXT,
                source_lang TEXT,
                target_lang TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def hash_src(src: str, source_lang: str, target_lang: str) -> str:
    return hashlib.sha256(f"{source_lang}\n{target_lang}\n{src}".encode("utf-8")).hexdigest()


def tm_get(db_path: Path, src: str, source_lang: str, target_lang: str) -> str | None:
    init_tm(db_path)
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT tgt FROM tm WHERE src_hash = ?", (hash_src(src, source_lang, target_lang),)).fetchone()
    return row[0] if row else None


def tm_put(db_path: Path, src: str, tgt: str, model: str, source_lang: str, target_lang: str) -> None:
    init_tm(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO tm(src_hash, src, tgt, model, source_lang, target_lang)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (hash_src(src, source_lang, target_lang), src, tgt, model, source_lang, target_lang),
        )


def glossary_prompt(glossary: list[dict[str, str]]) -> str:
    if not glossary:
        return "(none)"
    lines = []
    for row in glossary:
        suffix = " (protected, keep exactly)" if row.get("protected") == "true" else ""
        lines.append(f"- {row['term']} => {row.get('translation') or row['term']}{suffix}")
    return "\n".join(lines)


def parse_output_block(text: str, expected: int) -> list[str] | None:
    matches = list(BLOCK_MARKER_RE.finditer(text))
    if len(matches) != expected:
        return None
    results: list[str] = []
    for index, match in enumerate(matches):
        if int(match.group(1)) != index + 1:
            return None
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        results.append(text[start:end].strip())
    return results


def call_llm_block(items: list[dict[str, Any]], payload: dict[str, Any], cfg: Settings) -> list[str]:
    if litellm is None:
        raise RuntimeError("litellm 을 import 할 수 없습니다.")
    source_lang = normalize_lang(payload.get("source_lang", cfg.source_lang))
    target_lang = normalize_lang(payload.get("target_lang", cfg.target_lang))
    system = f"""You are a professional Microsoft Word document translator.
Translate from {LANG_NAME[source_lang]} to {LANG_NAME[target_lang]}.
Return only numbered blocks in the exact same format.
Do NOT add JSON, commentary, markdown fences, or explanations.
Preserve every placeholder matching __DOCSTR_*_0000__ exactly.
Do not translate URLs, emails, variables, or protected glossary terms represented by placeholders.
Keep text concise enough for the original document layout.
Glossary:
{glossary_prompt(payload.get('glossary', []))}
"""
    user_lines: list[str] = []
    for index, item in enumerate(items, start=1):
        user_lines.append(f"=== {index} ===")
        user_lines.append(item["text"])
    response = litellm.completion(
        model=cfg.llm_model,
        temperature=0,
        max_tokens=4096,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": "\n".join(user_lines)}],
    )
    content = response.choices[0].message.content or ""
    parsed = parse_output_block(content, len(items))
    if parsed is None:
        raise ValueError("LLM 응답 번호 블록 파싱 실패")
    return parsed


def translate_payload(payload: dict[str, Any], cfg: Settings) -> dict[str, Any]:
    source_lang = normalize_lang(payload.get("source_lang", cfg.source_lang))
    target_lang = normalize_lang(payload.get("target_lang", cfg.target_lang))
    db_path = Path(cfg.tm_db_path)
    translated_segments: list[dict[str, Any]] = []
    misses: list[dict[str, Any]] = []
    for segment in payload["segments"]:
        cached = tm_get(db_path, segment["text"], source_lang, target_lang)
        item = dict(segment)
        if cached is None:
            item["tm"] = "miss"
            misses.append(item)
        else:
            item["tm"] = "hit"
            item["translated_text"] = cached
        translated_segments.append(item)

    total = len(misses)
    for start in range(0, total, BATCH_SIZE):
        batch = misses[start : start + BATCH_SIZE]
        cache_batch = True
        try:
            outputs = call_llm_block(batch, payload, cfg)
        except Exception as exc:
            console.print(f"[yellow]LLM 배치 실패: {exc}. 원문 fallback 처리[/yellow]")
            outputs = [item["text"] for item in batch]
            cache_batch = False
        for item, translated in zip(batch, outputs, strict=True):
            cache_item = cache_batch
            if sorted(PLACEHOLDER_RE.findall(item["text"])) != sorted(PLACEHOLDER_RE.findall(translated)):
                console.print(f"[yellow]placeholder 불일치: segment {item['id']} 원문 fallback[/yellow]")
                translated = item["text"]
                cache_item = False
            if cache_item:
                tm_put(db_path, item["text"], translated, cfg.llm_model, source_lang, target_lang)
            for saved in translated_segments:
                if saved["id"] == item["id"]:
                    saved["translated_text"] = translated
                    break
        console.print(f"TRANSLATE {min(start + BATCH_SIZE, total)}/{total}")
    return {
        "version": payload.get("version", 2),
        "engine": payload.get("engine", "word-com"),
        "source_file": payload.get("source_file"),
        "source_lang": source_lang,
        "target_lang": target_lang,
        "model": cfg.llm_model,
        "segments": translated_segments,
    }


def story_by_index(doc: Any, wanted_type: int, wanted_index: int) -> Any | None:
    for story_type, story_index, story in iter_story_ranges(doc):
        if story_type == wanted_type and story_index == wanted_index:
            return story
    return None


def apply_segment_to_paragraph(paragraph: Any, translated_text: str, cfg: Settings) -> None:
    rng = paragraph_text_range(paragraph)
    if rng is None:
        return
    rng.Text = translated_text
    try:
        rng.Font.NameFarEast = cfg.kr_font
        rng.Font.Name = cfg.kr_font
    except Exception:
        pass


def apply_translations(input_path: Path, translated_path: Path, output_path: Path, cfg: Settings) -> dict[str, Any]:
    payload = json.loads(translated_path.read_text(encoding="utf-8"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(input_path, output_path)
    applied = 0
    skipped: list[str] = []
    with word_app() as word:
        with open_document(word, output_path, read_only=False) as doc:
            for segment in payload["segments"]:
                story = story_by_index(doc, int(segment["story_type"]), int(segment["story_index"]))
                if story is None:
                    message = f"story not found: {segment['path']}"
                    skipped.append(message)
                    console.print(f"[yellow]{message}[/yellow]")
                    continue
                paragraph_index = int(segment["paragraph_index"])
                if paragraph_index < 1 or paragraph_index > int(story.Paragraphs.Count):
                    message = f"paragraph not found: {segment['path']}"
                    skipped.append(message)
                    console.print(f"[yellow]{message}[/yellow]")
                    continue
                translated = segment.get("translated_text", segment.get("text", ""))
                restored = restore_tokens(translated, segment.get("tokens", []))
                try:
                    apply_segment_to_paragraph(story.Paragraphs.Item(paragraph_index), restored, cfg)
                    applied += 1
                except Exception as exc:
                    message = f"apply failed: {segment['path']} ({exc})"
                    skipped.append(message)
                    console.print(f"[yellow]{message}[/yellow]")
            update_document_fields(doc)
            save_format = WD_FORMAT_DOCUMENT if output_path.suffix.lower() == ".doc" else WD_FORMAT_DOCUMENT_DEFAULT
            doc.SaveAs2(str(output_path.resolve()), FileFormat=save_format)
    result = verify_output(output_path)
    result["applied"] = applied
    result["skipped"] = skipped
    return result


def verify_output(path: Path) -> dict[str, Any]:
    issues: list[str] = []
    with word_app() as word:
        with open_document(word, path, read_only=True) as doc:
            chunks: list[str] = []
            for _, _, story in iter_story_ranges(doc):
                try:
                    chunks.append(story.Text or "")
                except Exception:
                    pass
            if PLACEHOLDER_RE.search("\n".join(chunks)):
                issues.append("unrestored_placeholder")
    return {"ok": not issues, "issues": issues, "path": str(path)}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def work_key(path: Path) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(path.with_suffix("")))[:180]


def default_work_file(input_path: Path, filename: str, cfg: Settings) -> Path:
    return Path(cfg.work_dir) / work_key(input_path) / filename


def default_output_path(input_path: Path, target_lang: str, base_input: Path | None = None) -> Path:
    suffix = TARGET_SUFFIX.get(target_lang, target_lang.upper())
    if base_input and base_input.is_dir():
        try:
            rel = input_path.relative_to(base_input)
            return Path("output") / rel.parent / f"{input_path.stem}_{suffix}{input_path.suffix}"
        except ValueError:
            pass
    if input_path.parent.name.lower() == "input":
        return input_path.parent.parent / "output" / f"{input_path.stem}_{suffix}{input_path.suffix}"
    return input_path.with_name(f"{input_path.stem}_{suffix}{input_path.suffix}")


def discover_inputs(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if path.suffix.lower() in SUPPORTED_EXTENSIONS else []
    files: list[Path] = []
    for item in path.rglob("*"):
        if not item.is_file() or item.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        parts = {part.lower() for part in item.parts}
        if "done" in parts or "output" in parts or "work" in parts:
            continue
        if item.name.startswith("~$"):
            continue
        files.append(item)
    return sorted(files)


def move_done(path: Path) -> Path:
    done_dir = path.parent / "done"
    done_dir.mkdir(parents=True, exist_ok=True)
    target = done_dir / path.name
    if target.exists():
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        target = done_dir / f"{path.stem}_{stamp}{path.suffix}"
    shutil.move(str(path), str(target))
    return target


@app.command()
def extract(
    input_path: Path = typer.Argument(..., exists=True, readable=True),
    out: Path | None = typer.Option(None, "--out"),
    in_lang: str | None = typer.Option(None, "-in_lang", "--in-lang"),
    out_lang: str | None = typer.Option(None, "-out_lang", "--out-lang"),
) -> None:
    cfg = settings()
    if in_lang:
        cfg.source_lang = normalize_lang(in_lang)
    if out_lang:
        cfg.target_lang = normalize_lang(out_lang)
    payload = extract_segments(input_path, cfg)
    output = out or default_work_file(input_path, "segments.json", cfg)
    write_json(output, payload)
    console.print(f"EXTRACT {len(payload['segments'])} segments -> {output}")


@app.command()
def translate(
    segments_path: Path = typer.Argument(..., exists=True, readable=True),
    out: Path | None = typer.Option(None, "--out"),
    in_lang: str | None = typer.Option(None, "-in_lang", "--in-lang"),
    out_lang: str | None = typer.Option(None, "-out_lang", "--out-lang"),
) -> None:
    cfg = settings()
    payload = read_json(segments_path)
    if in_lang:
        payload["source_lang"] = normalize_lang(in_lang)
    if out_lang:
        payload["target_lang"] = normalize_lang(out_lang)
    translated = translate_payload(payload, cfg)
    output = out or segments_path.with_name("translated.json")
    write_json(output, translated)
    console.print(f"TRANSLATE {len(translated['segments'])} segments -> {output}")


@app.command()
def apply(
    input_path: Path = typer.Argument(..., exists=True, readable=True),
    translated_path: Path = typer.Argument(..., exists=True, readable=True),
    out: Path | None = typer.Option(None, "--out"),
    out_lang: str | None = typer.Option(None, "-out_lang", "--out-lang"),
) -> None:
    cfg = settings()
    target_lang = normalize_lang(out_lang or cfg.target_lang)
    output = out or default_output_path(input_path, target_lang)
    result = apply_translations(input_path, translated_path, output, cfg)
    status = "OK" if result["ok"] else f"WARN {result['issues']}"
    console.print(f"APPLY {status} applied={result.get('applied', 0)} -> {output}")


@app.command()
def run(
    input_path: Path = typer.Argument(..., exists=True, readable=True),
    in_lang: str | None = typer.Option(None, "-in_lang", "--in-lang"),
    out_lang: str | None = typer.Option(None, "-out_lang", "--out-lang"),
    lang: str | None = typer.Option(None, "-lang", "--lang"),
    output: Path | None = typer.Option(None, "--output"),
    no_move_done: bool = typer.Option(False, "--no-move-done"),
) -> None:
    cfg = settings()
    if in_lang:
        cfg.source_lang = normalize_lang(in_lang)
    if out_lang or lang:
        cfg.target_lang = normalize_lang(out_lang or lang or cfg.target_lang)
    files = discover_inputs(input_path)
    if not files:
        console.print("[yellow]처리할 .docx 또는 .doc 파일이 없습니다.[/yellow]")
        return
    failures: list[tuple[Path, str]] = []
    for index, source in enumerate(files, start=1):
        console.print(f"[{index}/{len(files)}] RUN {source}")
        try:
            segments = extract_segments(source, cfg)
            work_dir = default_work_file(source, "segments.json", cfg).parent
            segments_path = work_dir / "segments.json"
            translated_path = work_dir / "translated.json"
            write_json(segments_path, segments)
            translated = translate_payload(segments, cfg)
            write_json(translated_path, translated)
            out_path = output if output and len(files) == 1 else default_output_path(source, cfg.target_lang, input_path if input_path.is_dir() else None)
            result = apply_translations(source, translated_path, out_path, cfg)
            if not result["ok"]:
                console.print(f"[yellow]VERIFY WARN {source}: {result['issues']}[/yellow]")
            if not no_move_done and source.parent.name.lower() == "input":
                moved = move_done(source)
                console.print(f"DONE 이동: {moved}")
            console.print(f"OUTPUT {out_path}")
        except Exception as exc:
            failures.append((source, str(exc)))
            console.print(f"[red]FAILED {source}: {exc}[/red]")
    if failures:
        console.print("[red]실패 목록[/red]")
        for source, message in failures:
            console.print(f"- {source}: {message}")
        raise typer.Exit(code=1)


@tm_app.command("import")
def tm_import(
    csv_path: Path = typer.Argument(..., exists=True, readable=True),
    in_lang: str | None = typer.Option(None, "-in_lang", "--in-lang"),
    out_lang: str | None = typer.Option(None, "-out_lang", "--out-lang"),
) -> None:
    cfg = settings()
    source_lang = normalize_lang(in_lang or cfg.source_lang)
    target_lang = normalize_lang(out_lang or cfg.target_lang)
    count = 0
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            src = (row.get("source") or row.get("src") or row.get("term") or "").strip()
            tgt = (row.get("target") or row.get("tgt") or row.get("translation") or "").strip()
            if src and tgt:
                tm_put(Path(cfg.tm_db_path), src, tgt, "import", source_lang, target_lang)
                count += 1
    console.print(f"TM import {count} rows")


if __name__ == "__main__":
    app()
