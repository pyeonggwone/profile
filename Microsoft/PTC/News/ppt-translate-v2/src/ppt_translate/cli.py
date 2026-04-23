from pathlib import Path

import typer
from rich.console import Console

from ppt_translate.pipeline import run_apply, run_extract, run_full, run_translate

app = typer.Typer(help="PPTX in-place 번역 파이프라인")
console = Console()


@app.command()
def run(pptx: Path, output: Path | None = None) -> None:
    """전체 파이프라인 실행 (extract → translate → apply)."""
    out = run_full(pptx, output)
    console.print(f"[green]완료:[/green] {out}")


@app.command()
def extract(pptx: Path, out: Path = Path("work/segments.json")) -> None:
    """EXTRACT: PPTX 에서 번역 대상 텍스트 추출."""
    run_extract(pptx, out)
    console.print(f"[green]세그먼트 저장:[/green] {out}")


@app.command()
def translate(segments: Path, out: Path = Path("work/translated.json")) -> None:
    """TRANSLATE: 세그먼트 JSON 을 LLM 으로 번역."""
    run_translate(segments, out)
    console.print(f"[green]번역 저장:[/green] {out}")


@app.command()
def apply(pptx: Path, translated: Path, out: Path | None = None) -> None:
    """APPLY: 원본 PPTX 의 텍스트를 번역본으로 교체."""
    result = run_apply(pptx, translated, out)
    console.print(f"[green]출력:[/green] {result}")


tm_app = typer.Typer(help="Translation Memory 관리")
app.add_typer(tm_app, name="tm")


@tm_app.command("import")
def tm_import(csv_path: Path) -> None:
    """CSV (src,tgt) 를 TM 에 가져오기."""
    from ppt_translate.translate.memory import import_csv

    n = import_csv(csv_path)
    console.print(f"[green]TM {n}건 추가[/green]")


@app.command()
def diff(a: Path, b: Path) -> None:
    """두 PPTX 의 텍스트 변경분 표시."""
    from ppt_translate.tools.diff import show_diff

    show_diff(a, b)


if __name__ == "__main__":
    app()
