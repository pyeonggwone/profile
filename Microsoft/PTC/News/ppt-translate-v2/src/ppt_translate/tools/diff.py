"""두 PPTX 의 텍스트 변경분 표시."""
from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table

from ppt_translate.extract.shapes import extract_segments

console = Console()


def show_diff(a: Path, b: Path) -> None:
    sa = {(s["slide"], s["index"]): s["text"] for s in extract_segments(a)}
    sb = {(s["slide"], s["index"]): s["text"] for s in extract_segments(b)}

    table = Table(title=f"{a.name}  →  {b.name}")
    table.add_column("Slide")
    table.add_column("Idx", justify="right")
    table.add_column("Before")
    table.add_column("After")

    for key in sorted(sa.keys() | sb.keys()):
        ta, tb = sa.get(key, ""), sb.get(key, "")
        if ta != tb:
            table.add_row(key[0].split("/")[-1], str(key[1]), ta, tb)

    console.print(table)
