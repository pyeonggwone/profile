from __future__ import annotations

import subprocess
from pathlib import Path

from .config import Config
from .models import ValidationReport


def find_qpdf(config: Config) -> Path | None:
    candidates = []
    qpdf_bin = config.root / "tools/qpdf/bin/qpdf"
    qpdf_exe = config.root / "tools/qpdf/bin/qpdf.exe"
    if config.root.joinpath("tools/qpdf/qpdf").exists():
        candidates.append(config.root / "tools/qpdf/qpdf")
    if config.root.joinpath("tools/qpdf/qpdf.exe").exists():
        candidates.append(config.root / "tools/qpdf/qpdf.exe")
    candidates.extend([
        qpdf_bin,
        qpdf_exe,
        config.root / "tools/bin/qpdf",
        config.root / "tools/bin/qpdf.exe",
    ])
    env_value = None
    try:
        import os

        env_value = os.environ.get("QPDF_BIN")
    except Exception:
        env_value = None
    if env_value:
        path = Path(env_value)
        candidates.insert(0, path if path.is_absolute() else config.root / path)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def qdf_reference(config: Config, source_pdf: Path, qdf_pdf: Path) -> ValidationReport:
    qpdf = find_qpdf(config)
    if qpdf is None:
        return ValidationReport(False, "qpdf --qdf", None, "", "project-local qpdf not found")
    qdf_pdf.parent.mkdir(parents=True, exist_ok=True)
    command = [str(qpdf), "--qdf", "--object-streams=disable", str(source_pdf), str(qdf_pdf)]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return ValidationReport(completed.returncode == 0, " ".join(command), completed.returncode, completed.stdout, completed.stderr)


def qpdf_check(config: Config, pdf: Path) -> ValidationReport:
    qpdf = find_qpdf(config)
    if qpdf is None:
        return ValidationReport(False, "qpdf --check", None, "", "project-local qpdf not found")
    command = [str(qpdf), "--check", str(pdf)]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return ValidationReport(completed.returncode == 0, " ".join(command), completed.returncode, completed.stdout, completed.stderr)