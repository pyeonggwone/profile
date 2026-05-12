from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PdfSource:
    name: str
    sizeBytes: int
    sha256: str
    path: str


@dataclass
class JobState:
    jobId: str
    source: PdfSource


@dataclass
class ByteRange:
    start: int
    end: int


@dataclass
class OperatorSnapshot:
    op: str
    font: str | None = None
    size: float | None = None
    matrix: list[float] | None = None


@dataclass
class TextState:
    font: str | None = None
    fontSize: float | None = None
    textMatrix: list[float] | None = None
    lineMatrix: list[float] | None = None
    charSpacing: float = 0.0
    wordSpacing: float = 0.0
    horizontalScaling: float = 100.0
    leading: float = 0.0
    renderMode: int = 0
    rise: float = 0.0


@dataclass
class FontState:
    resourceName: str | None = None
    fontObjectRef: str | None = None
    subtype: str | None = None
    baseFont: str | None = None
    encoding: str | None = None
    toUnicodeRef: str | None = None


@dataclass
class TextPayload:
    encodedOriginal: str
    decodedOriginal: str | None = None
    decodedTranslated: str | None = None
    replacementEncoded: str | None = None


@dataclass
class RestoreOptions:
    streamXref: int | None
    operator: str
    operandRange: ByteRange | None
    textBlockRange: ByteRange | None
    operatorSequence: list[OperatorSnapshot]
    textState: TextState
    fontState: FontState
    source: str = "pdfplumber-pdfminer"


@dataclass
class RawTextRun:
    id: str
    restoreOptions: RestoreOptions
    textPayload: TextPayload


@dataclass
class RawContentStream:
    streamXref: int | None
    textRuns: list[RawTextRun]


@dataclass
class RawPage:
    page: int
    contents: list[RawContentStream]


@dataclass
class RawPdfTextState:
    pages: list[RawPage] = field(default_factory=list)


@dataclass
class RestoreOptionsRef:
    streamXref: int | None
    operator: str


@dataclass
class DecodeStatus:
    method: str
    confidence: str
    issues: list[str] = field(default_factory=list)


@dataclass
class LayoutInfo:
    matrix: list[float] | None = None
    bbox: list[float] | None = None
    estimatedWidth: float | None = None
    fontSize: float | None = None
    horizontalScaling: float | None = None
    sourceVisualUnits: float | None = None
    spacingVisualUnits: float | None = None


@dataclass
class ReadableItem:
    id: str
    page: int
    source: str
    restoreOptionsRef: RestoreOptionsRef
    decode: DecodeStatus
    layout: LayoutInfo


@dataclass
class ReadableTextState:
    items: list[ReadableItem] = field(default_factory=list)


@dataclass
class LayoutLimit:
    maxVisualUnits: float
    maxHangulChars: int
    sourceVisualUnits: float
    spacingVisualUnits: float
    fontSize: float
    safetyRatio: float


@dataclass
class JobTerm:
    term: str
    translation: str | None
    mode: str


@dataclass
class TranslationInputItem:
    id: str
    text: str
    layoutLimit: LayoutLimit | None = None


@dataclass
class TranslationInput:
    items: list[TranslationInputItem] = field(default_factory=list)
    terms: list[JobTerm] = field(default_factory=list)


@dataclass
class TranslationResultItem:
    id: str
    translated: str


@dataclass
class TranslationResults:
    items: list[TranslationResultItem] = field(default_factory=list)


@dataclass
class EncodeStatus:
    method: str
    status: str
    issues: list[str] = field(default_factory=list)


@dataclass
class PdfInputTextRun:
    id: str
    restoreOptions: RestoreOptions
    textPayload: TextPayload
    encode: EncodeStatus


@dataclass
class PdfInputTextState:
    textRuns: list[PdfInputTextRun] = field(default_factory=list)


@dataclass
class ReportIssue:
    code: str
    severity: str
    message: str
    id: str | None = None
    stage: str | None = None
    recoverable: bool = False


@dataclass
class RebuildReport:
    ok: bool
    replaced: int = 0
    failed: list[ReportIssue] = field(default_factory=list)


@dataclass
class ValidationReport:
    ok: bool
    command: str
    exitCode: int | None
    stdout: str
    stderr: str


JsonDict = dict[str, Any]


def _byte_range(data: JsonDict | None) -> ByteRange | None:
    if data is None:
        return None
    return ByteRange(int(data["start"]), int(data["end"]))


def _operator_snapshot(data: JsonDict) -> OperatorSnapshot:
    return OperatorSnapshot(data["op"], data.get("font"), data.get("size"), data.get("matrix"))


def _text_state(data: JsonDict | None) -> TextState:
    data = data or {}
    return TextState(
        font=data.get("font"),
        fontSize=data.get("fontSize"),
        textMatrix=data.get("textMatrix"),
        lineMatrix=data.get("lineMatrix"),
        charSpacing=float(data.get("charSpacing", 0.0)),
        wordSpacing=float(data.get("wordSpacing", 0.0)),
        horizontalScaling=float(data.get("horizontalScaling", 100.0)),
        leading=float(data.get("leading", 0.0)),
        renderMode=int(data.get("renderMode", 0)),
        rise=float(data.get("rise", 0.0)),
    )


def _font_state(data: JsonDict | None) -> FontState:
    data = data or {}
    return FontState(
        resourceName=data.get("resourceName"),
        fontObjectRef=data.get("fontObjectRef"),
        subtype=data.get("subtype"),
        baseFont=data.get("baseFont"),
        encoding=data.get("encoding"),
        toUnicodeRef=data.get("toUnicodeRef"),
    )


def restore_options_from_dict(data: JsonDict) -> RestoreOptions:
    return RestoreOptions(
        streamXref=data.get("streamXref"),
        operator=data.get("operator", "UNKNOWN"),
        operandRange=_byte_range(data.get("operandRange")),
        textBlockRange=_byte_range(data.get("textBlockRange")),
        operatorSequence=[_operator_snapshot(item) for item in data.get("operatorSequence", [])],
        textState=_text_state(data.get("textState")),
        fontState=_font_state(data.get("fontState")),
        source=data.get("source", "json"),
    )


def text_payload_from_dict(data: JsonDict) -> TextPayload:
    return TextPayload(
        encodedOriginal=data.get("encodedOriginal", ""),
        decodedOriginal=data.get("decodedOriginal"),
        decodedTranslated=data.get("decodedTranslated"),
        replacementEncoded=data.get("replacementEncoded"),
    )


def encode_status_from_dict(data: JsonDict) -> EncodeStatus:
    return EncodeStatus(data.get("method", "unknown"), data.get("status", "unknown"), list(data.get("issues", [])))


def pdf_input_from_dict(data: JsonDict) -> PdfInputTextState:
    return PdfInputTextState([
        PdfInputTextRun(
            item["id"],
            restore_options_from_dict(item["restoreOptions"]),
            text_payload_from_dict(item["textPayload"]),
            encode_status_from_dict(item.get("encode", {})),
        )
        for item in data.get("textRuns", [])
    ])