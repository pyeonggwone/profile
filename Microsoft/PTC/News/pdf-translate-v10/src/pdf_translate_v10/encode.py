from __future__ import annotations

from dataclasses import dataclass, field

from .models import EncodeStatus, PdfInputTextRun, PdfInputTextState, RawPdfTextState, ReportIssue, TextPayload, TranslationResults


@dataclass
class EncodeReport:
    ok: bool
    total: int
    okCount: int = 0
    failedCount: int = 0
    methods: dict[str, int] = field(default_factory=dict)
    issues: list[ReportIssue] = field(default_factory=list)


def build_pdf_input_state(raw: RawPdfTextState, translations: TranslationResults) -> tuple[PdfInputTextState, EncodeReport]:
    by_id = {item.id: item.translated for item in translations.items}
    runs: list[PdfInputTextRun] = []
    report = EncodeReport(ok=True, total=0)
    for page in raw.pages:
        for content in page.contents:
            for run in content.textRuns:
                report.total += 1
                translated = by_id.get(run.id, run.textPayload.decodedOriginal or "")
                payload = TextPayload(
                    encodedOriginal=run.textPayload.encodedOriginal,
                    decodedOriginal=run.textPayload.decodedOriginal,
                    decodedTranslated=translated,
                    replacementEncoded=None,
                )
                issues: list[str] = []
                status = "failed"
                method = "unavailable"
                original = run.textPayload.decodedOriginal or ""
                if translated == original:
                    status = "skipped"
                    method = "reuse-original"
                elif run.restoreOptions.operandRange is None:
                    if run.restoreOptions.textState.textMatrix:
                        payload.replacementEncoded = translated.encode("utf-16-be").hex()
                        status = "ok"
                        method = "text-compose"
                        report.okCount += 1
                    else:
                        issues.append("ENCODE_REQUIRES_TEXT_COMPOSE_MATRIX")
                        report.failedCount += 1
                        report.ok = False
                        report.issues.append(
                            ReportIssue(
                                "ENCODE_TEXT_COMPOSE_MATRIX_MISSING",
                                "warning",
                                "Text run has no verified byte range and no layout matrix, so text composition cannot place the translation.",
                                id=run.id,
                                stage="encode",
                                recoverable=True,
                            )
                        )
                else:
                    payload.replacementEncoded = translated.encode("utf-8").hex()
                    status = "ok"
                    method = "utf8-hex-placeholder"
                    report.okCount += 1
                report.methods[method] = report.methods.get(method, 0) + 1
                runs.append(PdfInputTextRun(run.id, run.restoreOptions, payload, EncodeStatus(method, status, issues)))
    return PdfInputTextState(runs), report