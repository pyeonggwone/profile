from __future__ import annotations

from pathlib import Path
from importlib import import_module
from typing import Iterable

from .models import (
    ByteRange,
    DecodeStatus,
    FontState,
    LayoutInfo,
    OperatorSnapshot,
    RawContentStream,
    RawPage,
    RawPdfTextState,
    RawTextRun,
    ReadableItem,
    RestoreOptions,
    RestoreOptionsRef,
    TextPayload,
    TextState,
)


def _iter_pdfminer_lines(source: Path) -> Iterable[tuple[int, str, tuple[float, float, float, float]]]:
    extract_pages = import_module("pdfminer.high_level").extract_pages
    layout_module = import_module("pdfminer.layout")
    LTTextContainer = layout_module.LTTextContainer
    LTTextLine = layout_module.LTTextLine

    for page_index, layout in enumerate(extract_pages(source), start=1):
        for element in layout:
            if isinstance(element, LTTextContainer):
                for line in element:
                    if isinstance(line, LTTextLine):
                        text = line.get_text().strip()
                        if text:
                            yield page_index, text, line.bbox


def _page_stream_xrefs(pdf) -> dict[int, int | None]:
    result: dict[int, int | None] = {}
    for index, page in enumerate(pdf.pages, start=1):
        contents = page.obj.get("/Contents")
        stream_xref = None
        if contents is not None and hasattr(contents, "objgen"):
            stream_xref = int(contents.objgen[0])
        result[index] = stream_xref
    return result


def extract_raw_text_state(source: Path) -> tuple[RawPdfTextState, dict[str, object]]:
    pdfplumber = import_module("pdfplumber")
    pikepdf = import_module("pikepdf")

    stream_xrefs: dict[int, int | None] = {}
    with pikepdf.open(source) as pdf:
        stream_xrefs = _page_stream_xrefs(pdf)

    miner_lines = list(_iter_pdfminer_lines(source))
    miner_by_page: dict[int, list[tuple[str, tuple[float, float, float, float]]]] = {}
    for page, text, bbox in miner_lines:
        miner_by_page.setdefault(page, []).append((text, bbox))

    pages: list[RawPage] = []
    with pdfplumber.open(source) as plumber_pdf:
        for page_index, page in enumerate(plumber_pdf.pages, start=1):
            text_runs: list[RawTextRun] = []
            lines = miner_by_page.get(page_index) or []
            if lines:
                source_lines = lines
            else:
                text = page.extract_text() or ""
                source_lines = [(line, (0.0, 0.0, page.width or 0.0, page.height or 0.0)) for line in text.splitlines() if line.strip()]
            for counter, (text, bbox) in enumerate(source_lines, start=1):
                run_id = f"p{page_index:04d}-r{counter:05d}"
                x0, y0, x1, y1 = (float(value) for value in bbox)
                font_size = max((y1 - y0) * 0.72, 6.0)
                restore = RestoreOptions(
                    streamXref=stream_xrefs.get(page_index),
                    operator="PDFMINER_TEXT_LINE",
                    operandRange=None,
                    textBlockRange=None,
                    operatorSequence=[OperatorSnapshot(op="PDFMINER_TEXT_LINE", size=font_size, matrix=[1.0, 0.0, 0.0, 1.0, x0, y0])],
                    textState=TextState(fontSize=font_size, textMatrix=[1.0, 0.0, 0.0, 1.0, x0, y0], lineMatrix=[x0, y0, x1, y1]),
                    fontState=FontState(),
                    source="pdfminer.six+pdfplumber",
                )
                payload = TextPayload(encodedOriginal=text.encode("utf-8").hex(), decodedOriginal=text)
                text_runs.append(RawTextRun(run_id, restore, payload))
            pages.append(RawPage(page_index, [RawContentStream(stream_xrefs.get(page_index), text_runs)]))

    report = {
        "ok": True,
        "pages": len(pages),
        "contentStreams": sum(len(page.contents) for page in pages),
        "textRuns": sum(len(content.textRuns) for page in pages for content in page.contents),
        "decodedMissing": 0,
        "fontResourceMissing": sum(1 for page in pages for content in page.contents for run in content.textRuns if run.restoreOptions.fontState.resourceName is None),
        "toUnicodeMissing": sum(1 for page in pages for content in page.contents for run in content.textRuns if run.restoreOptions.fontState.toUnicodeRef is None),
        "issues": [
            {
                "stage": "extract",
                "code": "BYTE_RANGE_UNAVAILABLE_FROM_LAYOUT_EXTRACTION",
                "severity": "warning",
                "message": "pdfplumber/pdfminer layout extraction does not guarantee original content stream byte ranges.",
                "recoverable": True,
            }
        ],
    }
    return RawPdfTextState(pages), report


def raw_to_readable(raw: RawPdfTextState) -> list[ReadableItem]:
    items: list[ReadableItem] = []
    for page in raw.pages:
        for content in page.contents:
            for run in content.textRuns:
                restore = run.restoreOptions
                bbox = restore.textState.lineMatrix
                source = run.textPayload.decodedOriginal or ""
                if restore.textState.fontSize:
                    width = len(source) * restore.textState.fontSize * 0.55
                else:
                    width = float(len(source))
                items.append(
                    ReadableItem(
                        id=run.id,
                        page=page.page,
                        source=source,
                        restoreOptionsRef=RestoreOptionsRef(restore.streamXref, restore.operator),
                        decode=DecodeStatus("pdfminer-text", "layout", []),
                        layout=LayoutInfo(
                            matrix=restore.textState.textMatrix,
                            bbox=bbox,
                            estimatedWidth=width,
                            fontSize=restore.textState.fontSize,
                            horizontalScaling=restore.textState.horizontalScaling,
                            sourceVisualUnits=width,
                            spacingVisualUnits=0.0,
                        ),
                    )
                )
    return items