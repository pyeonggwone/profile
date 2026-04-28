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
"""ppt-translate-v4 — PowerPoint COM 기반 PPT/PPTX 번역 도구.

Paragraph 단위 추출, Characters() API 기반 서식 보존, 재시도 없는 안정적 LLM 호출.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
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
    raise SystemExit("ppt-translate-v4 는 Windows native Python 전용입니다 (WSL 불가).")

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
    target_lang: str = "kr"

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


LANGUAGE_OPTIONS: dict[str, dict[str, str]] = {
    "en": {"code": "en", "name": "English", "label": "EN", "native": "English"},
    "ch": {"code": "ch", "name": "Chinese", "label": "CH", "native": "Chinese"},
    "jp": {"code": "jp", "name": "Japanese", "label": "JP", "native": "Japanese"},
    "kr": {"code": "kr", "name": "Korean", "label": "KR", "native": "Korean"},
}

LANGUAGE_ALIASES = {
    "en": "en",
    "eng": "en",
    "english": "en",
    "ch": "ch",
    "cn": "ch",
    "zh": "ch",
    "zh-cn": "ch",
    "chinese": "ch",
    "jp": "jp",
    "ja": "jp",
    "japanese": "jp",
    "kr": "kr",
    "ko": "kr",
    "korean": "kr",
}


def _normalize_lang(lang: str | None, *, default: str = "kr") -> str:
    key = (lang or default).strip().lower()
    normalized = LANGUAGE_ALIASES.get(key)
    if not normalized:
        allowed = ", ".join(LANGUAGE_OPTIONS)
        raise typer.BadParameter(f"지원 언어: {allowed}")
    return normalized


def _language_name(code: str) -> str:
    return LANGUAGE_OPTIONS[_normalize_lang(code)]["name"]


def _language_label(code: str) -> str:
    return LANGUAGE_OPTIONS[_normalize_lang(code)]["label"]


def _set_target_language(lang: str | None) -> str:
    target = _normalize_lang(lang)
    settings.target_lang = target
    return target


def _set_source_language(lang: str | None) -> str:
    source = _normalize_lang(lang, default="en")
    settings.source_lang = source
    return source


def _set_languages(in_lang: str | None = None, out_lang: str | None = None) -> tuple[str, str]:
    source = _set_source_language(in_lang)
    target = _set_target_language(out_lang)
    return source, target


def _target_font() -> str | None:
    if _normalize_lang(settings.target_lang) == "en":
        return None
    return settings.kr_font

import os  # noqa: E402

if settings.openai_api_key:
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key
if settings.azure_openai_api_key:
    os.environ["AZURE_API_KEY"] = settings.azure_openai_api_key
if settings.azure_openai_endpoint:
    os.environ["AZURE_API_BASE"] = settings.azure_openai_endpoint
if settings.azure_openai_api_version:
    os.environ["AZURE_API_VERSION"] = settings.azure_openai_api_version


# ────────────────────────────────────────────────
# PowerPoint COM
# ────────────────────────────────────────────────
@contextmanager
def powerpoint():
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
    # Mark as Final 해제 시도 (Save 거부 방지)
    if not read_only:
        try:
            pres.Final = False
        except com_error:
            pass
    try:
        yield pres
    finally:
        try:
            pres.Close()
        except com_error:
            pass


def _unblock_file(path: Path) -> None:
    """Mark-of-the-Web (Zone.Identifier ADS) 제거 → 보호된 보기 진입 방지.

    NTFS 대체 데이터 스트림 `<file>:Zone.Identifier` 를 삭제.
    실패해도 무시 (원본 이미 unblocked 이거나 권한 없으면 파워셰 로도 다시 시도)."""
    try:
        ads = Path(f"{path}:Zone.Identifier")
        if ads.exists():
            ads.unlink()
    except OSError:
        pass


def _kill_stray_powerpoint() -> None:
    """좌비 POWERPNT.EXE 프로세스 정리 (이전 실패 장아 제거)."""
    try:
        import subprocess
        subprocess.run(
            ["taskkill", "/F", "/IM", "POWERPNT.EXE", "/T"],
            check=False, capture_output=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        pass


# ────────────────────────────────────────────────
# Shape 분류 (제목/부제 휴리스틱 강화)
# ────────────────────────────────────────────────
_TITLE_PH_TYPES = {13, 15}      # ppPlaceholderTitle, ppPlaceholderCenterTitle
_SUBTITLE_PH_TYPES = {4}        # ppPlaceholderSubtitle


def _shape_max_font_size(shape) -> float:
    """Shape 의 대표 폰트 크기. 빠른 단일 COM 호출.

    TextRange.Font.Size 는 모든 문자가 동일 크기면 그 값을, 혼합되면 None/0 을 반환.
    혼합인 경우 0 을 돌려 휴리스틱이 동작하지 않게 함 (성능 우선).
    """
    try:
        if not getattr(shape, "HasTextFrame", False):
            return 0
        tf = shape.TextFrame
        if not tf.HasText:
            return 0
        size = tf.TextRange.Font.Size
        return float(size or 0)
    except (com_error, TypeError):
        return 0


def _shape_category(shape, slide_height_pt: float = 0) -> str:
    """shape → title/subtitle/body 분류.

    1) placeholder type 우선
    2) shape Name 에 'title'/'subtitle' 포함
    3) 휴리스틱: 폰트 크기 + 위치
    """
    # 1) placeholder type
    try:
        if shape.Type == 14:  # msoPlaceholder
            ph_type = shape.PlaceholderFormat.Type
            if ph_type in _TITLE_PH_TYPES:
                return "title"
            if ph_type in _SUBTITLE_PH_TYPES:
                return "subtitle"
            return "body"
    except com_error:
        pass

    # 2) Name 기반
    name = (getattr(shape, "Name", "") or "").lower()
    if "subtitle" in name:
        return "subtitle"
    if "title" in name:
        return "title"

    # 3) 휴리스틱 (폰트 크기 + 슬라이드 상단 위치)
    try:
        size = _shape_max_font_size(shape)
        top = float(getattr(shape, "Top", 0) or 0)
        # 슬라이드 상단 1/3 + 큰 폰트 → 제목
        if size >= 28 and (slide_height_pt == 0 or top < slide_height_pt / 3):
            return "title"
        if size >= 20:
            return "subtitle"
    except com_error:
        pass
    return ""


# ────────────────────────────────────────────────
# Paragraph 단위 추출 (불릿/줄바꿈/서식 보존)
# ────────────────────────────────────────────────
_BR_MARKER = "⏎"  # LLM 에 줄바꿈 보존 신호


def _font_snapshot(font) -> dict:
    """Font 객체의 주요 속성 캐시."""
    snap: dict = {}
    for attr in ("Bold", "Italic", "Underline", "Size", "Name", "NameFarEast"):
        try:
            v = getattr(font, attr)
            if v is not None:
                snap[attr] = v
        except com_error:
            pass
    try:
        snap["ColorRGB"] = int(font.Color.RGB)
    except com_error:
        pass
    return snap


def _font_apply(font, snap: dict, kr_font: str | None = None) -> None:
    """Font 객체에 스냅샷 적용. kr_font 가 주어지면 한글 폰트로 덮어쓰기."""
    for attr in ("Bold", "Italic", "Underline", "Size"):
        if attr in snap:
            try:
                setattr(font, attr, snap[attr])
            except com_error:
                pass
    # 폰트 이름은 한글 폰트 우선 적용
    if kr_font:
        try:
            font.Name = kr_font
        except com_error:
            pass
        try:
            font.NameFarEast = kr_font
        except com_error:
            pass
    if "ColorRGB" in snap:
        try:
            font.Color.RGB = snap["ColorRGB"]
        except com_error:
            pass


def _para_runs_meta(paragraph) -> list[dict]:
    """Paragraph 안의 run 별 (start, length, font snapshot, hyperlink) 메타.

    start 는 paragraph TextRange 내의 1-based char 인덱스.
    """
    meta: list[dict] = []
    try:
        runs = paragraph.Runs()
        count = int(runs.Count)
    except (com_error, AttributeError, TypeError):
        return meta
    cursor = 1
    for ri in range(1, count + 1):
        try:
            run = paragraph.Runs(ri, 1)
        except com_error:
            continue
        text = run.Text or ""
        length = len(text)
        if length == 0:
            continue
        m: dict = {
            "start": cursor,
            "length": length,
            "font": _font_snapshot(run.Font),
        }
        try:
            link = run.ActionSettings(1).Hyperlink
            addr = link.Address or ""
            sub = link.SubAddress or ""
            if addr or sub:
                m["hyperlink"] = (addr, sub)
        except com_error:
            pass
        meta.append(m)
        cursor += length
    return meta


def _para_bullet_meta(paragraph) -> dict:
    """Paragraph 의 불릿/들여쓰기 메타.

    원본의 Bullet.Visible 도 함께 저장 → apply 시 없었던 paragraph 에 bullet 자동
    부착되는 현상을 방지.
    """
    meta: dict = {}
    try:
        b = paragraph.ParagraphFormat.Bullet
        # Visible: msoTrue=-1, msoFalse=0, msoTriStateMixed=-2
        try:
            meta["bullet_visible"] = int(b.Visible)
        except com_error:
            meta["bullet_visible"] = 0
        try:
            meta["bullet_type"] = int(b.Type)
        except com_error:
            pass
        try:
            meta["bullet_char"] = b.Character
        except com_error:
            pass
        try:
            meta["bullet_size"] = float(b.RelativeSize)
        except com_error:
            pass
    except com_error:
        pass
    try:
        meta["indent_level"] = int(paragraph.IndentLevel)
    except com_error:
        pass
    try:
        meta["alignment"] = int(paragraph.ParagraphFormat.Alignment)
    except com_error:
        pass
    return meta


def _iter_text_frames(shape, path: list):
    """Shape 안의 (text_frame, path_prefix, kind) 를 yield."""
    try:
        shape_type = shape.Type
    except com_error:
        return

    if shape_type == 6:  # msoGroup
        try:
            count = int(shape.GroupItems.Count)
        except (com_error, AttributeError, TypeError):
            return
        for i in range(1, count + 1):
            try:
                child = shape.GroupItems(i)
            except com_error:
                continue
            yield from _iter_text_frames(child, path + [i])
        return

    has_smart = 0
    try:
        has_smart = getattr(shape, "HasSmartArt", 0)
    except com_error:
        has_smart = 0
    if has_smart == -1:
        try:
            nodes = shape.SmartArt.AllNodes
            ncount = int(nodes.Count)
        except (com_error, AttributeError, TypeError):
            return
        for ni in range(1, ncount + 1):
            try:
                node = nodes.Item(ni)
                tf2 = node.TextFrame2
                if not (tf2.TextRange.Text or "").strip():
                    continue
            except com_error:
                continue
            yield tf2, path + ["smartart", ni], "tf2"
        return

    has_table = False
    try:
        has_table = bool(shape.HasTable)
    except com_error:
        has_table = False
    if has_table:
        try:
            table = shape.Table
            rows = int(table.Rows.Count)
            cols = int(table.Columns.Count)
        except (com_error, AttributeError, TypeError):
            return
        for r in range(1, rows + 1):
            for c in range(1, cols + 1):
                try:
                    cell_shape = table.Cell(r, c).Shape
                    if cell_shape.HasTextFrame and cell_shape.TextFrame.HasText:
                        yield cell_shape.TextFrame, path + [r, c], "tf"
                except com_error:
                    continue
        return

    try:
        if getattr(shape, "HasTextFrame", False) and shape.TextFrame.HasText:
            yield shape.TextFrame, path, "tf"
    except com_error:
        return


def _extract_paragraphs(text_frame, path_prefix: list, kind: str) -> list[dict]:
    """TextFrame/TextFrame2 → paragraph 단위 세그먼트 리스트."""
    out: list[dict] = []
    try:
        tr = text_frame.TextRange
        count = int(tr.Paragraphs().Count)
    except (com_error, AttributeError, TypeError):
        return out
    for pi in range(1, count + 1):
        try:
            para = tr.Paragraphs(pi, 1)
            text = para.Text or ""
        except com_error:
            continue
        clean = text.rstrip("\r\n\v")
        if not clean.strip():
            continue
        text_for_llm = clean.replace("\v", _BR_MARKER)
        seg: dict = {
            "path": path_prefix + ["p", pi],
            "text": text_for_llm,
            "raw_text": clean,
            "kind": kind,
        }
        if kind == "tf":
            try:
                seg["runs_meta"] = _para_runs_meta(para)
            except com_error:
                pass
            try:
                seg["bullet"] = _para_bullet_meta(para)
            except com_error:
                pass
        out.append(seg)
    return out


def _collect_slide_segments(slide, slide_no: int, slide_h_pt: float) -> list[dict]:
    out: list[dict] = []
    try:
        shapes_count = int(slide.Shapes.Count)
    except (com_error, AttributeError, TypeError):
        shapes_count = 0
    for sh_idx in range(1, shapes_count + 1):
        try:
            shape = slide.Shapes(sh_idx)
        except com_error:
            continue
        try:
            category = _shape_category(shape, slide_h_pt)
        except com_error:
            category = ""
        try:
            for tf, path_prefix, kind in _iter_text_frames(shape, [sh_idx]):
                for seg in _extract_paragraphs(tf, path_prefix, kind):
                    seg["slide"] = slide_no
                    if category:
                        seg["category"] = category
                    out.append(seg)
        except com_error:
            continue

    # 노트 (있을 때만)
    try:
        if bool(getattr(slide, "HasNotesPage", False)):
            notes_tf = slide.NotesPage.Shapes.Placeholders(2).TextFrame
            for seg in _extract_paragraphs(notes_tf, ["notes"], "tf"):
                seg["slide"] = slide_no
                out.append(seg)
    except com_error:
        pass

    return out


def extract(pptx_path: Path) -> list[dict]:
    segments: list[dict] = []
    with powerpoint() as app, open_presentation(app, pptx_path, read_only=True) as pres:
        try:
            slide_h = float(pres.PageSetup.SlideHeight)
        except com_error:
            slide_h = 0.0
        try:
            slide_count = int(pres.Slides.Count)
        except (com_error, AttributeError, TypeError):
            slide_count = 0
        console.print(f"  슬라이드 {slide_count}장 추출 시작")
        for i in range(1, slide_count + 1):
            try:
                slide = pres.Slides(i)
            except com_error:
                continue
            before = len(segments)
            segments.extend(_collect_slide_segments(slide, i, slide_h))
            console.print(f"  [{i}/{slide_count}] 세그먼트 +{len(segments) - before} (누적 {len(segments)})")
    return segments


_DETECT_RE = {
    "kr": re.compile(r"[\uac00-\ud7a3]"),
    "jp": re.compile(r"[\u3040-\u30ff]"),
    "ch": re.compile(r"[\u4e00-\u9fff]"),
    "en": re.compile(r"[A-Za-z]"),
}


def detect_source_language(segments: list[dict]) -> str:
    text = "\n".join(str(seg.get("text") or "") for seg in segments)
    counts = {code: len(pattern.findall(text)) for code, pattern in _DETECT_RE.items()}
    if counts["jp"]:
        return "jp"
    if counts["kr"] >= max(counts["ch"], 1):
        return "kr"
    if counts["ch"]:
        return "ch"
    if counts["en"]:
        return "en"
    return _normalize_lang(settings.source_lang, default="en")


def _set_source_language_from_segments(segments: list[dict]) -> str:
    source = detect_source_language(segments)
    settings.source_lang = source
    return source


# ────────────────────────────────────────────────
# TM
# ────────────────────────────────────────────────
def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _tm_hash(text: str) -> str:
    source = _normalize_lang(settings.source_lang, default="en")
    target = _normalize_lang(settings.target_lang)
    return _hash(f"{source}\0{target}\0{text}")


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
        row = conn.execute("SELECT tgt FROM tm WHERE src_hash=?", (_tm_hash(src),)).fetchone()
        if row is None and _normalize_lang(settings.target_lang) == "kr":
            row = conn.execute("SELECT tgt FROM tm WHERE src_hash=?", (_hash(src),)).fetchone()
        return row[0] if row else None


def tm_store(src: str, tgt: str, model: str = "") -> None:
    with _tm_connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO tm (src_hash, src, tgt, model) VALUES (?, ?, ?, ?)",
            (_tm_hash(src), src, tgt, model),
        )


def tm_import_csv(csv_path: Path) -> int:
    n = 0
    with _tm_connect() as conn, csv_path.open(encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) < 2:
                continue
            conn.execute(
                "INSERT OR IGNORE INTO tm (src_hash, src, tgt) VALUES (?, ?, ?)",
                (_tm_hash(row[0]), row[0], row[1]),
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
# 오염 감지/정화
# ────────────────────────────────────────────────
_DICT_LEAK_RE = re.compile(r"\{['\"]text['\"]\s*:\s*['\"](?P<inner>[^'\"]*)['\"]\}")


def _sanitize_source(text: str) -> str:
    if not text:
        return text
    prev, cur = None, text
    while prev != cur:
        prev = cur
        cur = _DICT_LEAK_RE.sub(lambda m: m.group("inner"), cur)
        cur = re.sub(r"^\s*\{['\"]text['\"]\s*:\s*['\"]?", "", cur)
        cur = re.sub(r"['\"]?\}\s*$", "", cur)
    return cur.strip()


def _is_corrupted(text: str) -> bool:
    if not text:
        return False
    return bool(re.search(r"\{['\"]text['\"]", text))


# ────────────────────────────────────────────────
# 제목 후처리 (어미 제거)
# ────────────────────────────────────────────────
_TITLE_BAD_ENDINGS = (
    "하십시오", "하십시요", "하세요", "되세요", "되십시오",
    "합니다", "입니다", "됩니다", "갑니다",
    "하기", "되기",
    "해요", "되요", "예요", "에요",
)
_TITLE_TRAILING_PUNCT = (".", "!", "?", "。", "！", "？")


_SENTENCE_PUNCT_RE = re.compile(r"[.,;:!?。，；：！？]")
# 문장형 신호 패턴 (주어+동사, 조동사, 동명사 구문, 의문사 등)
_SENTENCE_HINT_RE = re.compile(
    r"\b("
    r"is|are|was|were|be|been|being|am|"
    r"do|does|did|don't|doesn't|didn't|"
    r"can|could|will|would|should|shall|may|might|must|"
    r"have|has|had|haven't|hasn't|hadn't|"
    r"you|your|we|our|they|their|i'll|we'll|you'll|"
    r"how to|what is|why|when|where|which|who|whose|"
    r"let's|let us|here's|there's|it's"
    r")\b",
    re.IGNORECASE,
)


def _looks_like_sentence(src_text: str) -> bool:
    """원문이 문장형이면 True (제목 다듬기 비활성화).

    구분 기준:
    - 문장 부호(. , ; : ! ?) 포함
    - 단어 6개 이상
    - 40자 이상 (긴 구문 안전)
    - 주어/조동사/의문사 등 문장형 힌트 단어 + 단어 4개 이상
    """
    t = (src_text or "").strip()
    if not t:
        return False
    if _SENTENCE_PUNCT_RE.search(t):
        return True
    words = t.split()
    if len(words) >= 6:
        return True
    if len(t) >= 40:
        return True
    if len(words) >= 4 and _SENTENCE_HINT_RE.search(t):
        return True
    return False


def _polish_title(text: str) -> str:
    """제목/부제 명사형 변환: 동사 어미 제거 + 끝 문장부호 제거."""
    t = text.strip()
    for _ in range(3):
        changed = False
        for end in _TITLE_BAD_ENDINGS:
            if t.endswith(end):
                t = t[: -len(end)].rstrip()
                changed = True
                break
        for p in _TITLE_TRAILING_PUNCT:
            if t.endswith(p):
                t = t[: -len(p)].rstrip()
                changed = True
        if not changed:
            break
    # 조사 정리: '를/을/이/가/에/에서' 끝나면 그대로 두는 게 자연스러우므로 건드리지 않음
    return t


# ────────────────────────────────────────────────
# TRANSLATE — 번호 매김 텍스트 블록 + 재시도 없음
# ────────────────────────────────────────────────
_BATCH = 5
_TITLE_MAX_CHARS = 20  # 절대 상한

_BLOCK_RE = re.compile(r"^===\s*(\d+)\s*===\s*$")


def _title_examples_for_target(target_lang: str) -> str:
    if target_lang == "kr":
        return (
            "Examples (title noun-phrase conversion):\n"
            "  EN: Get started today  ->  KR: 지금 시작\n"
            "  EN: Stop legacy        ->  KR: 레거시 중단\n"
            "  EN: Modernize your apps -> KR: 앱 현대화\n"
            "  EN: Why Azure?         ->  KR: Azure 선택 이유\n"
        )
    return (
        "For titles and subtitles, keep translations concise and presentation-ready.\n"
        "Use natural wording for the target language, not word-for-word literal output.\n"
    )


def _format_input_block(batch: list[dict]) -> tuple[str, str]:
    """LLM 에 보낼 system prompt 와 user 텍스트 블록 생성."""
    gloss = load_glossary()
    source_name = _language_name(settings.source_lang)
    target_lang = _normalize_lang(settings.target_lang)
    target_name = _language_name(target_lang)
    glossary_lines = [
        f"- {t}: {info['translation']}" + (" (protected)" if info["protected"] else "")
        for t, info in gloss.items()
    ]

    rules: list[str] = []
    for idx, seg in enumerate(batch, start=1):
        cat = seg.get("category") or ""
        src = seg["text"]
        sentence_form = _looks_like_sentence(src)
        if cat == "title":
            if sentence_form:
                rules.append(
                    f"  #{idx} TITLE (sentence): preserve sentence form, natural {target_name}. "
                    "Keep punctuation if present in source."
                )
            else:
                limit = min(max(int(len(src) * 1.0), 6), _TITLE_MAX_CHARS)
                rules.append(
                    f"  #{idx} TITLE: NOUN PHRASE only, ending with a noun. "
                    f"<= {limit} {target_name} chars. NO trailing punctuation. "
                    "Do not turn it into a full sentence."
                )
        elif cat == "subtitle":
            if sentence_form:
                rules.append(
                    f"  #{idx} SUBTITLE (sentence): preserve sentence form, natural {target_name}."
                )
            else:
                limit = min(max(int(len(src) * 1.1), 6), _TITLE_MAX_CHARS + 5)
                rules.append(
                    f"  #{idx} SUBTITLE: concise phrase. <= {limit} {target_name} chars. "
                    "Prefer noun ending. No trailing period."
                )

    examples = _title_examples_for_target(target_lang)

    system = (
        f"You translate {source_name} to {target_name} for slide decks.\n"
        "INPUT FORMAT: Numbered blocks like `=== 1 ===` followed by source text on the next line(s).\n"
        "OUTPUT FORMAT: Same number of blocks in same order. ONLY translated text under each header.\n"
        f"Do NOT include the {source_name} source. Do NOT add JSON, brackets, or commentary.\n"
        f"Preserve `{_BR_MARKER}` line-break markers exactly where they appear.\n"
        "Do not translate (protected) glossary terms. Keep numbers, URLs, file paths, code unchanged.\n"
        + (("\nPer-item rules:\n" + "\n".join(rules) + "\n") if rules else "")
        + "\n" + examples
        + "\nGlossary:\n" + ("\n".join(glossary_lines) if glossary_lines else "(none)")
    )

    parts: list[str] = []
    for idx, seg in enumerate(batch, start=1):
        parts.append(f"=== {idx} ===")
        parts.append(seg["text"])
    user = "\n".join(parts)
    return system, user


def _parse_output_block(content: str, expected: int) -> list[str] | None:
    """`=== N ===` 헤더를 분리해 N개 항목으로 반환. 실패 시 None."""
    buckets: dict[int, list[str]] = {}
    current: int | None = None
    for line in content.splitlines():
        m = _BLOCK_RE.match(line)
        if m:
            current = int(m.group(1))
            buckets.setdefault(current, [])
            continue
        if current is not None:
            buckets[current].append(line)

    if not buckets or set(buckets.keys()) != set(range(1, expected + 1)):
        return None

    out: list[str] = []
    for i in range(1, expected + 1):
        text = "\n".join(buckets[i]).strip("\n")
        out.append(text)
    return out


def _call_llm_block(batch: list[dict]) -> list[str]:
    """단 한 번 호출. 실패하면 ValueError 를 raise (재시도 없음)."""
    from litellm import completion

    system, user = _format_input_block(batch)
    resp = completion(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0,
        max_tokens=4096,
    )
    content = resp["choices"][0]["message"]["content"] or ""
    parsed = _parse_output_block(content, len(batch))
    if parsed is None:
        raise ValueError(f"블록 파싱 실패 (expected={len(batch)}): {content[:200]}")

    # 오염 검증
    for i, t in enumerate(parsed):
        if _is_corrupted(t):
            raise ValueError(f"응답에 dict 조각 포함 (idx={i}): {t[:120]}")
    return parsed


def translate_segments(segments: list[dict]) -> list[dict]:
    results: list[dict] = []
    pending: list[dict] = []

    # sanitize + cache lookup
    for seg in segments:
        cleaned_for_llm = _sanitize_source(seg["text"])
        if _is_corrupted(cleaned_for_llm):
            console.log(f"[yellow]오염 세그먼트 건너뜀: {cleaned_for_llm[:80]}[/yellow]")
            results.append({**seg, "translated": cleaned_for_llm})
            continue
        seg2 = {**seg, "text": cleaned_for_llm}
        cached = tm_lookup(cleaned_for_llm)
        if cached is not None and not _is_corrupted(cached):
            results.append({**seg2, "translated": _post_process(seg2, cached)})
        else:
            if cached is not None and _is_corrupted(cached):
                try:
                    with _tm_connect() as conn:
                        conn.execute("DELETE FROM tm WHERE src_hash=?", (_tm_hash(cleaned_for_llm),))
                except sqlite3.Error:
                    pass
            pending.append(seg2)

    total = len(pending)
    done = 0
    for i in range(0, total, _BATCH):
        batch = pending[i : i + _BATCH]
        try:
            translations = _call_llm_block(batch)
        except Exception as e:
            console.log(f"[red]번역 실패 (원문 유지) {len(batch)}건: {e}[/red]")
            translations = [s["text"] for s in batch]
        for seg, tgt in zip(batch, translations, strict=True):
            tgt = _post_process(seg, tgt)
            tm_store(seg["text"], tgt, model=settings.llm_model)
            results.append({**seg, "translated": tgt})
        done += len(batch)
        console.print(f"  [cyan]{done}/{total}[/cyan]")

    results.sort(key=lambda x: (x["slide"], _path_key(x["path"])))
    return results


def _post_process(seg: dict, translated: str) -> str:
    """번역 후 정리: 제목/부제는 어미·문장부호 제거 (단, 원문이 문장형이면 유지)."""
    if seg.get("category") in ("title", "subtitle"):
        if _looks_like_sentence(seg.get("text", "")):
            return translated.strip()
        if _normalize_lang(settings.target_lang) != "kr":
            return translated.strip()
        return _polish_title(translated)
    return translated


def _path_key(path: list) -> tuple:
    return tuple(str(p) for p in path)


# ────────────────────────────────────────────────
# APPLY (Characters() API + run 메타 복원)
# ────────────────────────────────────────────────
def _resolve_paragraph(slide, path: list):
    """path → (text_frame, paragraph_index, kind). 실패 시 (None, None, None)."""
    if not path:
        return None, None, None

    if path[0] == "notes":
        try:
            tf = slide.NotesPage.Shapes.Placeholders(2).TextFrame
        except com_error:
            return None, None, None
        # ["notes", "p", pi]
        if len(path) >= 3 and path[1] == "p":
            return tf, int(path[2]), "tf"
        return None, None, None

    try:
        shape = slide.Shapes(path[0])
    except com_error:
        return None, None, None
    p = list(path[1:])

    # 그룹 따라가기
    while shape.Type == 6 and len(p) >= 2 and isinstance(p[0], int):
        try:
            shape = shape.GroupItems(p.pop(0))
        except com_error:
            return None, None, None

    # SmartArt: ["smartart", ni, "p", pi]
    if len(p) >= 4 and p[0] == "smartart" and p[2] == "p":
        try:
            node = shape.SmartArt.AllNodes.Item(int(p[1]))
            return node.TextFrame2, int(p[3]), "tf2"
        except com_error:
            return None, None, None

    # 표: [r, c, "p", pi]
    if len(p) >= 4 and p[2] == "p":
        try:
            cell_shape = shape.Table.Cell(int(p[0]), int(p[1])).Shape
            return cell_shape.TextFrame, int(p[3]), "tf"
        except com_error:
            return None, None, None

    # 일반: ["p", pi]
    if len(p) >= 2 and p[0] == "p":
        try:
            return shape.TextFrame, int(p[1]), "tf"
        except com_error:
            return None, None, None

    return None, None, None


def _apply_paragraph_text(text_frame, para_index: int, kind: str, new_text: str,
                          runs_meta: list[dict] | None, target_font: str | None) -> None:
    """Paragraph 텍스트 교체 + Characters() API 로 서식 비례 복원."""
    # 줄바꿈 마커 → \v
    new_text = new_text.replace(_BR_MARKER, "\v")

    if kind == "tf2":
        # SmartArt: paragraph 객체에 직접 Text 대입
        try:
            paras = text_frame.TextRange.Paragraphs(para_index, 1)
            paras.Text = new_text
            if target_font:
                try:
                    paras.Font.Name.NameComplexScript = target_font
                except com_error:
                    pass
                try:
                    paras.Font.NameFarEast = target_font
                except com_error:
                    pass
                try:
                    paras.Font.Name = target_font
                except com_error:
                    pass
        except com_error:
            pass
        return

    # 일반 TextFrame
    tr = text_frame.TextRange
    para = tr.Paragraphs(para_index, 1)
    old_len = len(para.Text or "")
    # paragraph 의 시작 인덱스 (1-based) 계산
    para_start = 1
    for pi in range(1, para_index):
        try:
            para_start += len(tr.Paragraphs(pi, 1).Text or "")
        except com_error:
            pass

    # 교체 (CR 제외 길이 사용)
    body_len = len(para.Text.rstrip("\r\n\v"))
    chars = text_frame.TextRange.Characters(para_start, body_len)
    chars.Text = new_text
    new_len = len(new_text)

    applied = None
    if target_font:
        try:
            applied = text_frame.TextRange.Characters(para_start, new_len)
            applied.Font.Name = target_font
        except com_error:
            pass
        try:
            applied.Font.NameFarEast = target_font
        except (com_error, AttributeError):
            pass

    # run 별 서식 비례 복원
    if runs_meta:
        old_total = sum(m["length"] for m in runs_meta) or old_len or 1
        cursor = 0
        for m in runs_meta:
            ratio = m["length"] / old_total
            seg_len = max(int(round(new_len * ratio)), 0)
            if seg_len == 0:
                continue
            seg_start = para_start + cursor
            # 마지막 run 은 잔여 전부
            if m is runs_meta[-1]:
                seg_len = max(new_len - cursor, 0)
            if seg_len <= 0:
                continue
            try:
                ch = text_frame.TextRange.Characters(seg_start, seg_len)
            except com_error:
                continue
            _font_apply(ch.Font, m["font"], kr_font=target_font)
            if "hyperlink" in m:
                addr, sub = m["hyperlink"]
                try:
                    link = ch.ActionSettings(1).Hyperlink
                    link.Address = addr
                    link.SubAddress = sub
                except com_error:
                    pass
            cursor += seg_len

        # Bold 강제 적용: paragraph 내 첨 run 이 bold 면 paragraph 전체를 bold 처리
        # (Characters().Font.Name 일괄 적용으로 bold 가 reset 되는 현상 방지)
        try:
            first_bold = runs_meta[0]["font"].get("Bold")
            if first_bold in (-1, True, 1):
                applied_all = text_frame.TextRange.Characters(para_start, new_len)
                applied_all.Font.Bold = True
        except (com_error, IndexError, KeyError):
            pass


def _apply_bullet(text_frame, para_index: int, bullet: dict) -> None:
    if not bullet:
        return
    try:
        para = text_frame.TextRange.Paragraphs(para_index, 1)
    except com_error:
        return
    if "indent_level" in bullet:
        try:
            para.IndentLevel = bullet["indent_level"]
        except com_error:
            pass
    if "alignment" in bullet:
        try:
            para.ParagraphFormat.Alignment = bullet["alignment"]
        except com_error:
            pass
    # 원본에 bullet 이 없었다면 명시적으로 끔 (마스터 상속 차단)
    visible = bullet.get("bullet_visible")
    if visible == 0:
        try:
            para.ParagraphFormat.Bullet.Visible = 0
        except com_error:
            pass
        try:
            para.ParagraphFormat.Bullet.Type = 0  # ppBulletNone
        except com_error:
            pass
        return
    # 원본에 bullet 이 있었던 경우만 복원
    if visible == -1 or "bullet_type" in bullet:
        if "bullet_type" in bullet and bullet["bullet_type"] not in (0, -2):
            try:
                para.ParagraphFormat.Bullet.Type = bullet["bullet_type"]
            except com_error:
                pass
        if "bullet_char" in bullet:
            try:
                para.ParagraphFormat.Bullet.Character = bullet["bullet_char"]
            except com_error:
                pass
        if "bullet_size" in bullet:
            try:
                para.ParagraphFormat.Bullet.RelativeSize = bullet["bullet_size"]
            except com_error:
                pass
        try:
            para.ParagraphFormat.Bullet.Visible = -1
        except com_error:
            pass


# ────────────────────────────────────────────────
# 폰트 휴리스틱 축소 (한/영 길이 비율 기반)
# ────────────────────────────────────────────────
_HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")
_LATIN_WORD_RE = re.compile(r"[A-Za-z]{3,}")


def _shrink_font_if_needed(text_frame, para_start: int, new_len: int,
                           src_text: str, dst_text: str,
                           abs_min_size: float = 10.0) -> None:
    """KO/EN 길이 비율이 1.3 초과면 폰트 비율만큼 축소.

    하한: max(원본폰트의 85%, abs_min_size). 이미 작은 글자는 거의 줄이지 않음.
    """
    src_len = max(len(src_text), 1)
    dst_len = max(len(dst_text), 1)
    ratio = dst_len / src_len
    if ratio <= 1.3:
        return
    try:
        ch = text_frame.TextRange.Characters(para_start, new_len)
        cur = float(ch.Font.Size or 0)
        if cur <= 0:
            return
        floor_size = max(cur * 0.85, abs_min_size)
        new_size = max(cur / ratio, floor_size)
        if abs(new_size - cur) >= 0.5:
            ch.Font.Size = new_size
    except com_error:
        pass


# ────────────────────────────────────────────────
# APPLY 메인
# ────────────────────────────────────────────────
def _is_mostly_english(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < 3 or not _LATIN_WORD_RE.search(t):
        return False
    hangul = len(_HANGUL_RE.findall(t))
    latin = sum(1 for c in t if "A" <= c <= "z" and c.isalpha())
    return hangul < latin and latin / max(len(t), 1) >= 0.3


def apply(src_pptx: Path, translated: list[dict], out_pptx: Path) -> None:
    out_pptx = out_pptx.resolve()
    src_pptx = Path(src_pptx).resolve()
    out_pptx.parent.mkdir(parents=True, exist_ok=True)

    if src_pptx != out_pptx:
        shutil.copyfile(src_pptx, out_pptx)

    # MOTW 해제 (보호된 보기 방지)
    _unblock_file(out_pptx)

    by_slide: dict[int, list[dict]] = {}
    for item in translated:
        by_slide.setdefault(item["slide"], []).append(item)

    with powerpoint() as app, open_presentation(app, out_pptx) as pres:
        for slide_no, items in by_slide.items():
            try:
                slide = pres.Slides(slide_no)
            except com_error:
                continue
            touched_shape_idx: set = set()

            for item in items:
                path = item["path"]
                tf, p_idx, kind = _resolve_paragraph(slide, path)
                if tf is None:
                    continue
                try:
                    # paragraph 시작 인덱스 (서식·축소용)
                    para_start = 1
                    if kind == "tf":
                        tr_all = tf.TextRange
                        for pi in range(1, p_idx):
                            try:
                                para_start += len(tr_all.Paragraphs(pi, 1).Text or "")
                            except com_error:
                                pass

                    _apply_paragraph_text(
                        tf, p_idx, kind, item["translated"],
                        item.get("runs_meta"), _target_font(),
                    )

                    if kind == "tf":
                        # 불릿/들여쓰기 복원
                        if item.get("bullet"):
                            _apply_bullet(tf, p_idx, item["bullet"])

                        # 폰트 휴리스틱 축소
                        new_len_for_size = len(item["translated"].replace(_BR_MARKER, "\v"))
                        _shrink_font_if_needed(
                            tf, para_start, new_len_for_size,
                            item.get("raw_text", ""), item["translated"],
                        )

                    if isinstance(path[0], int):
                        touched_shape_idx.add(path[0])
                except com_error as e:
                    console.log(f"[yellow]skip slide{slide_no} path={path}: {e}[/yellow]")

            # 제목/부제 shape WordWrap 만 보장 (폭 조정 미적용)
            for sh_idx in touched_shape_idx:
                try:
                    shape = slide.Shapes(sh_idx)
                    if not getattr(shape, "HasTextFrame", False):
                        continue
                    try:
                        shape.TextFrame.WordWrap = True
                    except com_error:
                        pass
                except com_error:
                    pass

        # Save 시도. "Presentation cannot be modified" 에러 발생 시 SaveAs 폴백.
        try:
            pres.Save()
        except com_error as e:
            console.log(f"[yellow]Save 실패, SaveAs 재시도: {e}[/yellow]")
            tmp_out = out_pptx.with_name(f"{out_pptx.stem}.tmp{out_pptx.suffix}")
            try:
                # ppSaveAsOpenXMLPresentation = 24
                pres.SaveAs(str(tmp_out), 24)
                # 닫고 교체
                try:
                    pres.Close()
                except com_error:
                    pass
                shutil.move(str(tmp_out), str(out_pptx))
            except com_error as e2:
                raise RuntimeError(
                    f"Save/SaveAs 모두 실패: {e2}. 원본이 IRM/암호보호 되었을 수 있음."
                ) from e2


# ────────────────────────────────────────────────
# VERIFY
# ────────────────────────────────────────────────
def verify_and_fix(pptx_path: Path, work: Path, max_passes: int = 1) -> int:
    if _normalize_lang(settings.source_lang, default="en") != "en":
        return 0
    if _normalize_lang(settings.target_lang) == "en":
        return 0
    total_fixed = 0
    for pass_no in range(1, max_passes + 1):
        console.print(f"[bold]VERIFY pass {pass_no}[/bold]")
        current = extract(pptx_path)
        leftover = [s for s in current if _is_mostly_english(s["text"])]
        if not leftover:
            console.print("  [green]잔여 영문 없음[/green]")
            break
        console.print(f"  잔여 {len(leftover)}건 재번역")
        for seg in leftover:
            try:
                with _tm_connect() as conn:
                    conn.execute("DELETE FROM tm WHERE src_hash=?", (_tm_hash(seg["text"]),))
            except sqlite3.Error:
                pass
        retranslated = translate_segments(leftover)
        (work / f"verify_pass{pass_no}.json").write_text(
            json.dumps(retranslated, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        apply(pptx_path, retranslated, pptx_path)
        total_fixed += len(leftover)
    return total_fixed


# ────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────
app = typer.Typer(help="PPTX 번역 (PowerPoint COM)")


@app.callback()
def main(
    in_lang: str = typer.Option("en", "--in-lang", "--in_lang", "-in_lang", help="입력 언어: en, kr, ch, jp (기본 en)"),
    out_lang: str = typer.Option("kr", "--out-lang", "--out_lang", "-out_lang", help="출력 언어: en, kr, ch, jp (기본 kr)"),
    lang: str | None = typer.Option(None, "--lang", "-lang", help="호환용 대상 언어 옵션. out_lang 과 동일"),
) -> None:
    _set_languages(in_lang, lang or out_lang)


def _move_to_done(pptx: Path) -> Path | None:
    src = pptx.resolve()
    if not src.exists():
        return None
    done_dir = src.parent / "done"
    done_dir.mkdir(parents=True, exist_ok=True)
    dst = done_dir / src.name
    if dst.exists():
        dst = done_dir / f"{src.stem}_{int(src.stat().st_mtime)}{src.suffix}"
    shutil.move(str(src), str(dst))
    return dst


@app.command()
def run(
    pptx: Path,
    output: Path | None = None,
    in_lang: str | None = typer.Option(None, "--in-lang", "--in_lang", "-in_lang", help="입력 언어: en, kr, ch, jp"),
    out_lang: str | None = typer.Option(None, "--out-lang", "--out_lang", "-out_lang", help="출력 언어: en, kr, ch, jp"),
    lang: str | None = typer.Option(None, "--lang", "-lang", help="호환용 대상 언어 옵션. out_lang 과 동일"),
    move_done: bool = typer.Option(True, "--move-done/--no-move-done"),
    verify: bool = typer.Option(True, "--verify/--no-verify"),
) -> None:
    """전체 파이프라인. pptx 가 디렉토리면 안의 모든 파일을 순차 처리."""
    if in_lang is not None:
        _set_source_language(in_lang)
    if lang is not None or out_lang is not None:
        _set_target_language(lang or out_lang)
    pptx = Path(pptx)
    if pptx.is_dir():
        _run_directory(pptx, move_done=move_done, verify=verify)
        return
    _run_one(pptx, output=output, move_done=move_done, verify=verify)


def _collect_input_files(directory: Path) -> list[Path]:
    files: list[Path] = []
    for p in sorted(directory.iterdir()):
        if not p.is_file() or p.name.startswith("~$"):
            continue
        if p.suffix.lower() not in (".pptx", ".ppt"):
            continue
        files.append(p)
    return files


def _run_directory(directory: Path, *, move_done: bool, verify: bool) -> None:
    files = _collect_input_files(directory)
    if not files:
        console.print(f"[yellow]대상 파일 없음:[/yellow] {directory}")
        return
    # 좌비 PowerPoint 프로세스 정리 (이전 실패 장아 제거)
    _kill_stray_powerpoint()
    console.print(f"[bold cyan]배치 실행: {len(files)}건[/bold cyan]")
    ok = 0
    failed: list[tuple[Path, str]] = []
    for i, f in enumerate(files, start=1):
        console.rule(f"[{i}/{len(files)}] {f.name}")
        try:
            _run_one(f, output=None, move_done=move_done, verify=verify)
            ok += 1
        except Exception as e:
            console.print(f"[red]실패:[/red] {f.name} ({e})")
            failed.append((f, str(e)))
            # 실패 시 좌비 PowerPoint 정리 후 다음 파일 진행
            _kill_stray_powerpoint()
    console.rule("배치 종료")
    console.print(f"[green]성공 {ok}/{len(files)}[/green]")
    if failed:
        console.print(f"[red]실패 {len(failed)}건[/red]")
        for f, msg in failed:
            console.print(f"  - {f.name}: {msg}")


def _run_one(pptx: Path, *, output: Path | None, move_done: bool, verify: bool) -> None:
    work = settings.work_dir / pptx.stem
    work.mkdir(parents=True, exist_ok=True)

    # 원본 MOTW 해제 (보호된 보기 방지)
    _unblock_file(pptx)

    if output is None:
        out_dir = pptx.parent.parent / "output" if pptx.parent.name.lower() == "input" else pptx.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{pptx.stem}_{_language_label(settings.target_lang)}{pptx.suffix}"
    else:
        out = output

    console.print("[bold]EXTRACT[/bold]")
    segments = extract(pptx)
    console.print(f"  언어: {_language_label(settings.source_lang)} → {_language_label(settings.target_lang)}")
    (work / "segments.json").write_text(
        json.dumps(segments, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    console.print(f"  세그먼트 {len(segments)}건")

    console.print("[bold]TRANSLATE[/bold]")
    translated = translate_segments(segments)
    (work / "translated.json").write_text(
        json.dumps(translated, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    console.print("[bold]APPLY[/bold]")
    apply(pptx, translated, out)
    console.print(f"[green]적용 완료:[/green] {out}")

    if verify:
        fixed = verify_and_fix(out, work)
        if fixed:
            console.print(f"[green]잔여 영문 {fixed}건 재번역 적용[/green]")

    if move_done:
        moved = _move_to_done(pptx)
        if moved:
            console.print(f"[green]입력 이동:[/green] {moved}")


def extract_cmd(pptx: Path, out: Path = Path("work/segments.json")) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    segments = extract(pptx)
    out.write_text(json.dumps(segments, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    console.print(f"[green]저장:[/green] {out}")


app.command(name="extract")(extract_cmd)


@app.command()
def translate(
    segments_path: Path,
    out: Path = Path("work/translated.json"),
    in_lang: str | None = typer.Option(None, "--in-lang", "--in_lang", "-in_lang", help="입력 언어: en, kr, ch, jp"),
    out_lang: str | None = typer.Option(None, "--out-lang", "--out_lang", "-out_lang", help="출력 언어: en, kr, ch, jp"),
    lang: str | None = typer.Option(None, "--lang", "-lang", help="호환용 대상 언어 옵션. out_lang 과 동일"),
) -> None:
    if in_lang is not None:
        _set_source_language(in_lang)
    if lang is not None or out_lang is not None:
        _set_target_language(lang or out_lang)
    out.parent.mkdir(parents=True, exist_ok=True)
    segments = json.loads(segments_path.read_text(encoding="utf-8"))
    console.print(f"  언어: {_language_label(settings.source_lang)} → {_language_label(settings.target_lang)}")
    translated = translate_segments(segments)
    out.write_text(json.dumps(translated, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    console.print(f"[green]저장:[/green] {out}")


def apply_cmd(
    pptx: Path,
    translated_path: Path,
    out: Path | None = None,
    out_lang: str | None = typer.Option(None, "--out-lang", "--out_lang", "-out_lang", help="출력 언어: en, kr, ch, jp"),
    lang: str | None = typer.Option(None, "--lang", "-lang", help="호환용 대상 언어 옵션. out_lang 과 동일"),
) -> None:
    if lang is not None or out_lang is not None:
        _set_target_language(lang or out_lang)
    translated = json.loads(translated_path.read_text(encoding="utf-8"))
    out = out or pptx.with_stem(f"{pptx.stem}_{_language_label(settings.target_lang)}")
    apply(pptx, translated, out)
    console.print(f"[green]완료:[/green] {out}")


app.command(name="apply")(apply_cmd)


tm_app = typer.Typer(help="Translation Memory")
app.add_typer(tm_app, name="tm")


@tm_app.command("import")
def tm_import(csv_path: Path) -> None:
    n = tm_import_csv(csv_path)
    console.print(f"[green]TM {n}건 추가[/green]")


@tm_app.command("clean")
def tm_clean() -> None:
    if not settings.tm_db_path.exists():
        console.print("[yellow]TM 없음[/yellow]")
        return
    with _tm_connect() as conn:
        rows = conn.execute("SELECT src_hash, src, tgt FROM tm").fetchall()
        bad = [h for h, s, t in rows if _is_corrupted(s) or _is_corrupted(t)]
        for h in bad:
            conn.execute("DELETE FROM tm WHERE src_hash=?", (h,))
    console.print(f"[green]오염 항목 {len(bad)}건 제거[/green]")


if __name__ == "__main__":
    app()
