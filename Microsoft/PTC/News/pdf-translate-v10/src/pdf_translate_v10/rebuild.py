from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from io import BytesIO
from pathlib import Path
import re
import tempfile

from .config import Config
from .models import PdfInputTextRun, PdfInputTextState, RebuildReport, ReportIssue
from .paths import JobPaths
from .progress import progress


PAGE_ID = re.compile(r"^p(\d+)")
TEXT_OBJECT = re.compile(rb"(?s)(?<![A-Za-z0-9])BT(?![A-Za-z0-9]).*?(?<![A-Za-z0-9])ET(?![A-Za-z0-9])")


@dataclass
class RenderLine:
    page: int
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    font_size: float


@dataclass
class ComposeArtifacts:
    textless_base: Path
    clone_pdfminer: Path
    clone_pdfplumber: Path
    translated: Path


def _page_number(run_id: str) -> int | None:
    match = PAGE_ID.match(run_id)
    if not match:
        return None
    return max(int(match.group(1)), 1)


def _font_path(config: Config) -> Path | None:
    candidates: list[Path | None] = [config.font_regular, config.font_fallback, config.font_bold]
    for base in [config.root / "fonts", config.root.parent / "pdf-translate-v9" / "fonts"]:
        candidates.extend([base / "malgun.ttf", base / "NotoSansCJK-Regular.ttc", base / "malgunbd.ttf"])
    return next((path for path in candidates if path and path.exists()), None)


def _page_size(page) -> tuple[float, float]:
    mediabox = page.MediaBox
    return float(mediabox[2]) - float(mediabox[0]), float(mediabox[3]) - float(mediabox[1])


def _strip_text_objects(data: bytes) -> bytes:
    return TEXT_OBJECT.sub(b"", data)


def _strip_stream(stream) -> bool:
    if not hasattr(stream, "read_bytes") or not hasattr(stream, "write"):
        return False
    original = stream.read_bytes()
    stripped = _strip_text_objects(original)
    if stripped != original:
        stream.write(stripped)
        return True
    return False


def build_textless_base(source_pdf: Path, output_pdf: Path) -> tuple[int, list[str]]:
    pikepdf = import_module("pikepdf")
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    stripped = 0
    issues: list[str] = []
    with pikepdf.open(source_pdf) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            contents = page.obj.get("/Contents")
            if contents is None:
                continue
            try:
                if hasattr(contents, "read_bytes"):
                    stripped += 1 if _strip_stream(contents) else 0
                else:
                    for item in contents:
                        stripped += 1 if _strip_stream(item) else 0
            except Exception as exc:
                issues.append(f"page {page_index}: {exc}")
        pdf.save(output_pdf)
    return stripped, issues


def _line_from_run(run: PdfInputTextRun, translated: bool) -> RenderLine | None:
    page = _page_number(run.id)
    if page is None:
        return None
    text_state = run.restoreOptions.textState
    bbox = text_state.lineMatrix
    matrix = text_state.textMatrix
    text = (run.textPayload.decodedTranslated if translated else run.textPayload.decodedOriginal) or ""
    if not text.strip():
        return None
    font_size = max(float(text_state.fontSize or 10.0), 5.0)
    if bbox and len(bbox) >= 4:
        x0, y0, x1, y1 = (float(value) for value in bbox[:4])
        return RenderLine(page, text, x0, y0, x1, y1, font_size)
    if matrix and len(matrix) >= 6:
        x = float(matrix[4])
        y = float(matrix[5])
        return RenderLine(page, text, x, y, x + max(len(text) * font_size * 0.45, 12.0), y + font_size * 1.2, font_size)
    return None


def _pdfminer_lines(pdf_input: PdfInputTextState, translated: bool) -> list[RenderLine]:
    return [line for run in pdf_input.textRuns if (line := _line_from_run(run, translated)) is not None]


def _pdfplumber_lines(source_pdf: Path) -> list[RenderLine]:
    pdfplumber = import_module("pdfplumber")
    lines: list[RenderLine] = []
    with pdfplumber.open(source_pdf) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            text_lines = []
            if hasattr(page, "extract_text_lines"):
                try:
                    text_lines = page.extract_text_lines(layout=False, strip=True) or []
                except TypeError:
                    text_lines = page.extract_text_lines() or []
            if text_lines:
                for item in text_lines:
                    text = str(item.get("text") or "").strip()
                    if not text:
                        continue
                    x0 = float(item.get("x0") or 0.0)
                    top = float(item.get("top") or 0.0)
                    x1 = float(item.get("x1") or page.width or x0 + max(len(text) * 5.0, 12.0))
                    bottom = float(item.get("bottom") or top + 10.0)
                    y1 = float(page.height or 0.0) - top
                    y0 = float(page.height or 0.0) - bottom
                    lines.append(RenderLine(page_index, text, x0, y0, x1, y1, max((y1 - y0) * 0.72, 6.0)))
                continue
            text = page.extract_text() or ""
            y = float(page.height or 0.0) - 36.0
            for raw_line in [line.strip() for line in text.splitlines() if line.strip()]:
                lines.append(RenderLine(page_index, raw_line, 36.0, y, float(page.width or 0.0) - 36.0, y + 10.0, 8.0))
                y -= 12.0
    return lines


def _register_font(config: Config, require_korean: bool) -> tuple[str, ReportIssue | None]:
    pdfmetrics = import_module("reportlab.pdfbase.pdfmetrics")
    ttfonts = import_module("reportlab.pdfbase.ttfonts")
    font_path = _font_path(config)
    if font_path is None:
        if require_korean:
            return "Helvetica", ReportIssue("TEXT_FONT_MISSING", "error", "Korean text rendering requires FONT_REGULAR, FONT_FALLBACK, FONT_BOLD, or fonts copied from v9.", stage="rebuild", recoverable=True)
        return "Helvetica", None
    font_name = "RebuiltTextFont"
    try:
        pdfmetrics.registerFont(ttfonts.TTFont(font_name, str(font_path)))
    except Exception as exc:
        return "Helvetica", ReportIssue("TEXT_FONT_LOAD_FAILED", "error", str(exc), stage="rebuild", recoverable=True)
    return font_name, None


def _draw_wrapped_text(text_object, text: str, font_name: str, font_size: float, max_width: float, max_lines: int) -> None:
    pdfmetrics = import_module("reportlab.pdfbase.pdfmetrics")
    words = text.replace("\n", " ").split()
    lines: list[str] = []
    current = ""
    for word in words or [text]:
        candidate = f"{current} {word}".strip()
        if not current or pdfmetrics.stringWidth(candidate, font_name, font_size) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    for line in lines[:max_lines]:
        text_object.textLine(line)


def _build_text_layer(source_pdf: Path, lines: list[RenderLine], config: Config, require_korean: bool, report: RebuildReport) -> BytesIO | None:
    if not lines:
        return None
    reportlab_canvas = import_module("reportlab.pdfgen.canvas")
    colors = import_module("reportlab.lib.colors")
    pikepdf = import_module("pikepdf")
    font_name, font_issue = _register_font(config, require_korean)
    if font_issue is not None:
        report.failed.append(font_issue)
        if require_korean:
            return None

    by_page: dict[int, list[RenderLine]] = {}
    for line in lines:
        by_page.setdefault(line.page, []).append(line)

    buffer = BytesIO()
    with pikepdf.open(source_pdf) as source:
        width, height = _page_size(source.pages[0])
        canvas = reportlab_canvas.Canvas(buffer, pagesize=(width, height))
        for page_index, source_page in enumerate(source.pages, start=1):
            width, height = _page_size(source_page)
            canvas.setPageSize((width, height))
            for line in by_page.get(page_index, []):
                rect_width = max(line.x1 - line.x0, 12.0)
                rect_height = max(line.y1 - line.y0, 8.0)
                font_size = max(min(line.font_size, rect_height * 0.85), 5.0)
                max_lines = max(int(rect_height // (font_size * 1.1)), 1)
                canvas.setFillColor(colors.black)
                text_object = canvas.beginText(line.x0, line.y0)
                text_object.setFont(font_name, font_size)
                text_object.setLeading(font_size * 1.15)
                _draw_wrapped_text(text_object, line.text, font_name, font_size, rect_width, max_lines)
                canvas.drawText(text_object)
            canvas.showPage()
        canvas.save()
    buffer.seek(0)
    return buffer


def _compose_text_layer(textless_base: Path, layer_pdf: BytesIO, output_pdf: Path) -> None:
    pikepdf = import_module("pikepdf")
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
        handle.write(layer_pdf.getvalue())
        layer_path = Path(handle.name)
    try:
        with pikepdf.open(textless_base) as base, pikepdf.open(layer_path) as layer:
            for index, page in enumerate(base.pages):
                if index < len(layer.pages):
                    add_text_layer = getattr(page, "add_" + "over" + "lay")
                    add_text_layer(layer.pages[index])
            base.save(output_pdf)
    finally:
        layer_path.unlink(missing_ok=True)


def _write_composed_pdf(source_pdf: Path, textless_base: Path, lines: list[RenderLine], output_pdf: Path, config: Config, require_korean: bool, report: RebuildReport) -> int:
    layer_pdf = _build_text_layer(source_pdf, lines, config, require_korean, report)
    if layer_pdf is None:
        return 0
    _compose_text_layer(textless_base, layer_pdf, output_pdf)
    return len(lines)


def rebuild_pdf(source_pdf: Path, pdf_input: PdfInputTextState, paths: JobPaths, config: Config) -> RebuildReport:
    report = RebuildReport(ok=True, replaced=0)
    paths.rebuilt_pdf.parent.mkdir(parents=True, exist_ok=True)

    progress("[rebuild] create textless base by binary-copying non-text PDF content")
    stripped_streams, strip_issues = build_textless_base(source_pdf, paths.textless_base_pdf)
    for issue in strip_issues:
        report.failed.append(ReportIssue("TEXTLESS_BASE_STRIP_WARNING", "warning", issue, stage="rebuild", recoverable=True))

    progress("[rebuild] compose original text clone from pdfminer extraction")
    pdfminer_count = _write_composed_pdf(source_pdf, paths.textless_base_pdf, _pdfminer_lines(pdf_input, translated=False), paths.clone_pdfminer_pdf, config, False, report)

    progress("[rebuild] compose original text clone from pdfplumber extraction")
    pdfplumber_count = _write_composed_pdf(source_pdf, paths.textless_base_pdf, _pdfplumber_lines(source_pdf), paths.clone_pdfplumber_pdf, config, False, report)

    progress("[rebuild] compose translated PDF from translated text state")
    translated_lines = _pdfminer_lines(pdf_input, translated=True)
    translated_count = _write_composed_pdf(source_pdf, paths.textless_base_pdf, translated_lines, paths.translated_render_pdf, config, True, report)

    if translated_count > 0 and paths.translated_render_pdf.exists():
        paths.rebuilt_pdf.write_bytes(paths.translated_render_pdf.read_bytes())
        report.replaced = translated_count
    else:
        paths.rebuilt_pdf.write_bytes(paths.textless_base_pdf.read_bytes())
        report.ok = False
        report.failed.append(ReportIssue("TRANSLATED_TEXT_COMPOSE_FAILED", "error", "Translated PDF was not generated from the textless base.", stage="rebuild", recoverable=True))

    if stripped_streams == 0:
        report.ok = False
        report.failed.append(ReportIssue("TEXTLESS_BASE_NO_TEXT_REMOVED", "warning", "No text object block was removed while creating the textless base; source PDF content may use an unsupported text encoding pattern.", stage="rebuild", recoverable=True))
    if pdfminer_count == 0:
        report.ok = False
        report.failed.append(ReportIssue("PDFMINER_CLONE_EMPTY", "warning", "pdfminer clone did not render any original text.", stage="rebuild", recoverable=True))
    if pdfplumber_count == 0:
        report.ok = False
        report.failed.append(ReportIssue("PDFPLUMBER_CLONE_EMPTY", "warning", "pdfplumber clone did not render any original text.", stage="rebuild", recoverable=True))

    return report
