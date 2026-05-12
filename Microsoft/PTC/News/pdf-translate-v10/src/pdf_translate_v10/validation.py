from __future__ import annotations

from pathlib import Path
from importlib import import_module

from .config import Config
from .models import ValidationReport
from .qpdf import qpdf_check


def validate_pdf(config: Config, pdf: Path) -> ValidationReport:
    qpdf_report = qpdf_check(config, pdf)
    if qpdf_report.exitCode is not None:
        return qpdf_report
    try:
        pikepdf = import_module("pikepdf")

        with pikepdf.open(pdf):
            pass
        return ValidationReport(True, "pikepdf.open", 0, "", "")
    except Exception as exc:
        return ValidationReport(False, "pikepdf.open", 1, "", str(exc))