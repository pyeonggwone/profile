# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pywin32>=306 ; sys_platform == 'win32'",
#   "litellm>=1.50",
#   "openai>=1.40",
#   "pydantic-settings>=2.5",
#   "typer>=0.12",
#   "rich>=13.8",
# ]
# ///
"""ppt-translate-v3 — PowerPoint COM 기반 PPTX 번역 도구.

WindowsPowerShell 7+ + Windows native Python 에서 실행한다.
PowerPoint 데스크톱 앱이 설치되어 있어야 한다.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path

import typer
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich.console import Console

# ────────────────────────────────────────────────
# 플랫폼 가드
# ────────────────────────────────────────────────
if sys.platform != "win32":
    raise SystemExit("ppt-translate-v3 는 Windows native Python 전용입니다 (WSL 불가).")

import win32com.client  # noqa: E402
from pywintypes import com_error  # noqa: E402

console = Console()


# ────────────────────────────────────────────────
# 설정
# ────────────────────────────────────────────────
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-08-01-preview"
    azure_openai_deployment: str = ""

    source_lang: str = "en"
    target_lang: str = "ko"

    work_dir: Path = Path("work")
    tm_db_path: Path = Path("work/tm.sqlite")
    glossary_path: Path = Path("glossary.csv")
    kr_font: str = "맑은 고딕"

    @property
    def llm_model(self) -> str:
        if self.azure_openai_deployment:
            return f"azure/{self.azure_openai_deployment}"
        return self.openai_model


settings = Settings()


# ────────────────────────────────────────────────
# PowerPoint COM 컨텍스트
# ────────────────────────────────────────────────
@contextmanager
def powerpoint():
    """PowerPoint Application 인스턴스 (WithWindow=False)."""
    app = win32com.client.DispatchEx("PowerPoint.Application")
    try:
        yield app
    finally:
        try:
            app.Quit()
        except com_error:
            pass


@contextmanager
def open_presentation(app, path: Path, read_only: bool = False):
    pres = app.Presentations.Open(
        str(Path(path).resolve()),
        WithWindow=False,
        ReadOnly=read_only,
    )
    try:
        yield pres
    finally:
        try:
            pres.Close()
        except com_error:
            pass


# ────────────────────────────────────────────────
# Shape 텍스트 순회
# ────────────────────────────────────────────────
def _iter_text_runs(shape, path: list[int]):
    """Shape 안의 모든 텍스트 Run 을 (path, run) 으로 yield."""
    # 그룹: 재귀
    if shape.Type == 6:  # msoGroup
        for i, child in enumerate(shape.GroupItems, start=1):
            yield from _iter_text_runs(child, path + [i])
        return

    # 표
    if shape.HasTable:
        table = shape.Table
        for r in range(1, table.Rows.Count + 1):
            for c in range(1, table.Columns.Count + 1):
                cell_shape = table.Cell(r, c).Shape
                if cell_shape.HasTextFrame and cell_shape.TextFrame.HasText:
                    tf = cell_shape.TextFrame.TextRange
                    for ri, run in enumerate(tf.Runs(), start=1):
                        yield path + [r, c, ri], run
        return

    # 텍스트 프레임
    if getattr(shape, "HasTextFrame", False) and shape.TextFrame.HasText:
        tr = shape.TextFrame.TextRange
        for ri, run in enumerate(tr.Runs(), start=1):
            yield path + [ri], run


def _collect_slide_segments(slide, slide_no: int) -> list[dict]:
    out: list[dict] = []
    for sh_idx, shape in enumerate(slide.Shapes, start=1):
        for path, run in _iter_text_runs(shape, [sh_idx]):
            text = run.Text or ""
            if not text.strip():
                continue
            out.append(
                {
                    "slide": slide_no,
                    "path": path,
                    "text": text,
                }
            )

    # 노트 슬라이드
    try:
        notes_tf = slide.NotesPage.Shapes.Placeholders(2).TextFrame.TextRange
        for ri, run in enumerate(notes_tf.Runs(), start=1):
            text = run.Text or ""
            if text.strip():
                out.append({"slide": slide_no, "path": ["notes", ri], "text": text})
    except com_error:
        pass

    return out


# ────────────────────────────────────────────────
# EXTRACT
# ────────────────────────────────────────────────
def extract(pptx_path: Path) -> list[dict]:
    segments: list[dict] = []
    with powerpoint() as app, open_presentation(app, pptx_path, read_only=True) as pres:
        for i, slide in enumerate(pres.Slides, start=1):
            segments.extend(_collect_slide_segments(slide, i))
    return segments


# ────────────────────────────────────────────────
# TM (SQLite)
# ────────────────────────────────────────────────
def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _tm_connect() -> sqlite3.Connection:
    settings.tm_db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.tm_db_path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tm (
            src_hash TEXT PRIMARY KEY,
            src TEXT NOT NULL,
            tgt TEXT NOT NULL,
            model TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    return conn


def tm_lookup(src: str) -> str | None:
    with _tm_connect() as conn:
        row = conn.execute("SELECT tgt FROM tm WHERE src_hash=?", (_hash(src),)).fetchone()
        return row[0] if row else None


def tm_store(src: str, tgt: str, model: str = "") -> None:
    with _tm_connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO tm (src_hash, src, tgt, model) VALUES (?, ?, ?, ?)",
            (_hash(src), src, tgt, model),
        )


def tm_import_csv(csv_path: Path) -> int:
    n = 0
    with _tm_connect() as conn, csv_path.open(encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 2:
                continue
            conn.execute(
                "INSERT OR IGNORE INTO tm (src_hash, src, tgt) VALUES (?, ?, ?)",
                (_hash(row[0]), row[0], row[1]),
            )
            n += 1
    return n


# ────────────────────────────────────────────────
# 용어집
# ────────────────────────────────────────────────
def load_glossary() -> dict[str, dict]:
    if not settings.glossary_path.exists():
        return {}
    out: dict[str, dict] = {}
    with settings.glossary_path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            term = (row.get("term") or "").strip()
            if not term:
                continue
            out[term] = {
                "translation": (row.get("translation") or "").strip(),
                "protected": (row.get("protected") or "").strip().lower() in ("1", "true", "yes"),
            }
    return out


# ────────────────────────────────────────────────
# TRANSLATE
# ────────────────────────────────────────────────
_BATCH = 30


def translate_segments(segments: list[dict]) -> list[dict]:
    gloss = load_glossary()
    results: list[dict] = []
    pending: list[dict] = []

    for seg in segments:
        cached = tm_lookup(seg["text"])
        if cached is not None:
            results.append({**seg, "translated": cached})
        else:
            pending.append(seg)

    for i in range(0, len(pending), _BATCH):
        batch = pending[i : i + _BATCH]
        translations = _call_llm([s["text"] for s in batch], gloss)
        for seg, tgt in zip(batch, translations, strict=True):
            tm_store(seg["text"], tgt, model=settings.llm_model)
            results.append({**seg, "translated": tgt})

    results.sort(key=lambda x: (x["slide"], _path_key(x["path"])))
    return results


def _path_key(path: list) -> tuple:
    return tuple(str(p) for p in path)


def _call_llm(texts: list[str], gloss: dict[str, dict]) -> list[str]:
    from litellm import completion

    glossary_lines = [
        f"- {t}: {info['translation']}" + (" (protected)" if info["protected"] else "")
        for t, info in gloss.items()
    ]
    system = (
        f"You translate {settings.source_lang} to {settings.target_lang}.\n"
        "Return JSON: {\"translations\": [...]} matching input order. "
        "Do not translate (protected) terms. Keep numbers, URLs, code unchanged.\n"
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
        for v in parsed.values():
            if isinstance(v, list):
                parsed = v
                break
    if not isinstance(parsed, list) or len(parsed) != len(texts):
        raise ValueError(f"LLM 응답 형식 오류: {content[:200]}")
    return [str(x) for x in parsed]


# ────────────────────────────────────────────────
# APPLY (COM 으로 텍스트만 교체)
# ────────────────────────────────────────────────
def _resolve_run(shape, path: list):
    """path 를 따라 Shape → Run 까지 도달한다. 표/그룹/노트 처리."""
    # 노트
    if path and path[0] == "notes":
        return None  # caller 가 별도 처리

    p = list(path)
    # 그룹 따라가기 (HasTable 전까지 정수 index 만 GroupItems 로 간주)
    while shape.Type == 6 and len(p) >= 2:
        shape = shape.GroupItems(p.pop(0))

    # 표
    if shape.HasTable and len(p) >= 3:
        r, c, ri = p[-3], p[-2], p[-1]
        cell_shape = shape.Table.Cell(r, c).Shape
        return cell_shape.TextFrame.TextRange.Runs(ri)

    # 일반 텍스트 프레임
    if getattr(shape, "HasTextFrame", False) and p:
        return shape.TextFrame.TextRange.Runs(p[-1])

    return None


def apply(src_pptx: Path, translated: list[dict], out_pptx: Path) -> None:
    out_pptx = out_pptx.resolve()
    out_pptx.parent.mkdir(parents=True, exist_ok=True)

    # 원본 복사
    import shutil

    shutil.copyfile(src_pptx, out_pptx)

    # slide → [(path, translated)]
    by_slide: dict[int, list[tuple[list, str]]] = {}
    for item in translated:
        by_slide.setdefault(item["slide"], []).append((item["path"], item["translated"]))

    with powerpoint() as app, open_presentation(app, out_pptx) as pres:
        for slide_no, items in by_slide.items():
            slide = pres.Slides(slide_no)
            for path, text in items:
                try:
                    if path and path[0] == "notes":
                        notes_tf = slide.NotesPage.Shapes.Placeholders(2).TextFrame.TextRange
                        run = notes_tf.Runs(path[1])
                    else:
                        shape = slide.Shapes(path[0])
                        run = _resolve_run(shape, path[1:])
                    if run is None:
                        continue
                    run.Text = text
                    try:
                        run.Font.Name = settings.kr_font
                        run.Font.NameFarEast = settings.kr_font
                    except com_error:
                        pass
                except com_error as e:
                    console.log(f"[yellow]skip slide{slide_no} path={path}: {e}[/yellow]")
        pres.Save()


# ────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────
app = typer.Typer(help="PPTX 번역 (PowerPoint COM)")


@app.command()
def run(pptx: Path, output: Path | None = None) -> None:
    """전체 파이프라인 실행."""
    work = settings.work_dir / pptx.stem
    work.mkdir(parents=True, exist_ok=True)

    console.print("[bold]EXTRACT[/bold]")
    segments = extract(pptx)
    (work / "segments.json").write_text(
        json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    console.print(f"  세그먼트 {len(segments)}건")

    console.print("[bold]TRANSLATE[/bold]")
    translated = translate_segments(segments)
    (work / "translated.json").write_text(
        json.dumps(translated, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    console.print("[bold]APPLY[/bold]")
    out = output or pptx.with_stem(f"{pptx.stem}_{settings.target_lang.upper()}")
    apply(pptx, translated, out)
    console.print(f"[green]완료:[/green] {out}")


@app.command()
def extract_cmd(pptx: Path, out: Path = Path("work/segments.json")) -> None:
    """EXTRACT 만 실행."""
    out.parent.mkdir(parents=True, exist_ok=True)
    segments = extract(pptx)
    out.write_text(json.dumps(segments, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"[green]저장:[/green] {out}")


app.command(name="extract")(extract_cmd)


@app.command()
def translate(segments_path: Path, out: Path = Path("work/translated.json")) -> None:
    """TRANSLATE 만 실행."""
    out.parent.mkdir(parents=True, exist_ok=True)
    segments = json.loads(segments_path.read_text(encoding="utf-8"))
    translated = translate_segments(segments)
    out.write_text(json.dumps(translated, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"[green]저장:[/green] {out}")


@app.command()
def apply_cmd(pptx: Path, translated_path: Path, out: Path | None = None) -> None:
    """APPLY 만 실행."""
    translated = json.loads(translated_path.read_text(encoding="utf-8"))
    out = out or pptx.with_stem(f"{pptx.stem}_{settings.target_lang.upper()}")
    apply(pptx, translated, out)
    console.print(f"[green]완료:[/green] {out}")


app.command(name="apply")(apply_cmd)


tm_app = typer.Typer(help="Translation Memory")
app.add_typer(tm_app, name="tm")


@tm_app.command("import")
def tm_import(csv_path: Path) -> None:
    """CSV (src,tgt) 를 TM 에 가져오기."""
    n = tm_import_csv(csv_path)
    console.print(f"[green]TM {n}건 추가[/green]")


if __name__ == "__main__":
    app()
