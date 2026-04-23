"""PPTX = ZIP 패키지 입출력."""
from __future__ import annotations

import shutil
import zipfile
from collections.abc import Iterator
from pathlib import Path

from lxml import etree


def iter_slide_xml(pptx_path: Path) -> Iterator[tuple[str, bytes]]:
    """PPTX 내 ppt/slides/slide{N}.xml 을 (이름, 바이트) 로 yield."""
    with zipfile.ZipFile(pptx_path) as zf:
        names = sorted(
            n for n in zf.namelist()
            if n.startswith("ppt/slides/slide") and n.endswith(".xml")
        )
        for name in names:
            yield name, zf.read(name)


def copy_pptx(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def replace_xml_in_pptx(pptx_path: Path, replacements: dict[str, bytes]) -> None:
    """기존 PPTX 의 특정 XML 엔트리를 교체 (in-place)."""
    tmp = pptx_path.with_suffix(".tmp.pptx")
    with zipfile.ZipFile(pptx_path, "r") as zin, zipfile.ZipFile(
        tmp, "w", zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.infolist():
            data = replacements.get(item.filename, zin.read(item.filename))
            zout.writestr(item, data)
    tmp.replace(pptx_path)


def parse_xml(data: bytes) -> etree._Element:
    return etree.fromstring(data)


def serialize_xml(root: etree._Element) -> bytes:
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
