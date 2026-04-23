"""
ooxml_replacer.py — STEP 3-2: OOXML 직접 조작으로 PPTX 텍스트 in-place 치환

python-pptx 대신 lxml로 슬라이드 XML의 <a:t> 노드를 순서대로 1:1 교체한다.
원본 PPTX의 모든 서식(bold, italic, color, size, animation, layout 등)이 100% 보존되며,
<a:rPr>의 <a:latin>/<a:ea> typeface만 한글 폰트로 override 한다.

처리 흐름:
  1. kr/{stem}_KO.pptx 를 zip으로 읽고 임시 zip에 entry 단위로 복사
  2. ppt/slides/slideN.xml 발견 시:
     - components_kr/slide_N_component_kr.json 의 paragraphs.runs 텍스트를 평탄화
     - <p:sp> shape id 매칭 → 내부 <a:t> 1:1 교체
     - <p:graphicFrame> (table) shape id 매칭 → 셀 단위 첫 <a:t>에 텍스트 세팅
     - 모든 <a:rPr>의 typeface를 font_kr_map 기반으로 override
  3. ppt/notesSlides/notesSlideN.xml 발견 시 노트 텍스트 치환
  4. 임시 zip을 원본 경로로 이동
"""
import json
import os
import re
import shutil
import tempfile
import zipfile
from typing import List, Optional, Tuple

from lxml import etree

from library import logger


# OOXML 네임스페이스
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"

_SLIDE_RE = re.compile(r"^ppt/slides/slide(\d+)\.xml$")
_NOTES_RE = re.compile(r"^ppt/notesSlides/notesSlide(\d+)\.xml$")


def replace_pptx(kr_pptx_path: str, comp_kr_dir: str,
                 translated_dir: str, slide_limit: Optional[int] = None) -> dict:
    """kr/{stem}_KO.pptx 의 슬라이드 XML을 components_kr JSON으로 in-place 치환."""
    log = logger.get()
    statuses: dict = {}

    tmp_fd, tmp_path = tempfile.mkstemp(
        suffix=".pptx", dir=os.path.dirname(kr_pptx_path)
    )
    os.close(tmp_fd)

    try:
        with zipfile.ZipFile(kr_pptx_path, "r") as zin, \
             zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zout:

            comp_cache: dict = {}
            font_cache: dict = {}

            for item in zin.infolist():
                data = zin.read(item.filename)

                # 슬라이드 XML
                slide_idx = _match_index(item.filename, _SLIDE_RE)
                if slide_idx is not None:
                    if slide_limit and slide_idx > slide_limit:
                        zout.writestr(item, data)
                        continue
                    comp = _cache_load(
                        comp_cache, slide_idx,
                        os.path.join(comp_kr_dir, f"slide_{slide_idx}_component_kr.json"),
                    )
                    font_map = _cache_load(
                        font_cache, slide_idx,
                        os.path.join(comp_kr_dir, f"slide_{slide_idx}_font_kr.json"),
                    ) or {"__default__": "Pretendard"}

                    if comp:
                        try:
                            data, status = _process_slide_xml(data, comp, font_map)
                            statuses[slide_idx] = status
                            log.info(f"  slide_{slide_idx} XML 치환 완료 "
                                     f"(text_box {sum(1 for i in status['items'] if i['type']=='text_box')}, "
                                     f"table {sum(1 for i in status['items'] if i['type']=='table')})")
                        except Exception as e:
                            log.error(f"  slide_{slide_idx} XML 치환 실패: {e}")
                    else:
                        log.warning(f"  slide_{slide_idx}: component_kr JSON 없음, 원본 유지")

                    zout.writestr(item, data)
                    continue

                # 노트 슬라이드 XML
                notes_idx = _match_index(item.filename, _NOTES_RE)
                if notes_idx is not None:
                    if slide_limit and notes_idx > slide_limit:
                        zout.writestr(item, data)
                        continue
                    comp = _cache_load(
                        comp_cache, notes_idx,
                        os.path.join(comp_kr_dir, f"slide_{notes_idx}_component_kr.json"),
                    )
                    if comp and comp.get("notes"):
                        try:
                            data = _process_notes_xml(data, comp["notes"])
                        except Exception as e:
                            log.warning(f"  slide_{notes_idx} 노트 XML 치환 실패: {e}")
                    zout.writestr(item, data)
                    continue

                # 그 외 entry는 그대로 복사
                zout.writestr(item, data)

        shutil.move(tmp_path, kr_pptx_path)
        log.info(f"[STEP 3-2 OOXML] 저장 완료 → {kr_pptx_path}")

        # status JSON 저장
        os.makedirs(translated_dir, exist_ok=True)
        for sidx, status in statuses.items():
            with open(os.path.join(translated_dir, f"slide_{sidx}.json"),
                      "w", encoding="utf-8") as f:
                json.dump(status, f, ensure_ascii=False, indent=2)

    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise

    return statuses


# ──────────────────────────────────────────────
# XML 처리
# ──────────────────────────────────────────────

def _process_slide_xml(xml_bytes: bytes, comp: dict, font_map: dict) -> Tuple[bytes, dict]:
    log = logger.get()
    root = etree.fromstring(xml_bytes)
    slide_num = comp["slide_num"]
    status: dict = {"slide_num": slide_num, "items": []}

    tb_map = {tb["id"]: tb for tb in comp.get("text_boxes", [])}
    tbl_map = {tbl["id"]: tbl for tbl in comp.get("tables", [])}

    # 텍스트 박스(<p:sp>)
    for sp in root.iter(f"{{{P}}}sp"):
        cNvPr = sp.find(f".//{{{P}}}nvSpPr/{{{P}}}cNvPr")
        if cNvPr is None:
            continue
        sid = f"s{slide_num}_shape{cNvPr.get('id')}"
        tb = tb_map.get(sid)
        if not tb:
            continue
        try:
            translated = _flatten_runs(tb.get("paragraphs", []))
            t_nodes = sp.findall(f".//{{{A}}}t")
            _replace_t_nodes(t_nodes, translated)
            _apply_kr_font(sp, font_map)
            status["items"].append({"id": sid, "type": "text_box", "ok": True})
        except Exception as e:
            log.warning(f"    ✗ text_box {sid}: {e}")
            status["items"].append({
                "id": sid, "type": "text_box", "ok": False, "error": str(e)
            })

    # 표(<p:graphicFrame> > <a:graphic> > <a:tbl>)
    for gf in root.iter(f"{{{P}}}graphicFrame"):
        cNvPr = gf.find(f".//{{{P}}}nvGraphicFramePr/{{{P}}}cNvPr")
        if cNvPr is None:
            continue
        sid = f"s{slide_num}_shape{cNvPr.get('id')}"
        tbl = tbl_map.get(sid)
        if not tbl:
            continue
        try:
            tbl_elem = gf.find(f".//{{{A}}}tbl")
            if tbl_elem is None:
                continue
            xml_rows = tbl_elem.findall(f"{{{A}}}tr")
            json_rows = tbl.get("rows", [])
            for r_idx, tr in enumerate(xml_rows):
                if r_idx >= len(json_rows):
                    break
                xml_cells = tr.findall(f"{{{A}}}tc")
                json_cells = json_rows[r_idx]
                for c_idx, tc in enumerate(xml_cells):
                    if c_idx >= len(json_cells):
                        break
                    cell_text = _normalize_text(json_cells[c_idx].get("text", ""))
                    t_nodes = tc.findall(f".//{{{A}}}t")
                    if t_nodes:
                        t_nodes[0].text = cell_text
                        for tn in t_nodes[1:]:
                            tn.text = ""
            _apply_kr_font(gf, font_map)
            status["items"].append({"id": sid, "type": "table", "ok": True})
        except Exception as e:
            log.warning(f"    ✗ table {sid}: {e}")
            status["items"].append({
                "id": sid, "type": "table", "ok": False, "error": str(e)
            })

    new_bytes = etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    return new_bytes, status


def _process_notes_xml(xml_bytes: bytes, notes_text: str) -> bytes:
    root = etree.fromstring(xml_bytes)
    t_nodes = root.findall(f".//{{{A}}}t")
    if t_nodes:
        t_nodes[0].text = _normalize_text(notes_text)
        for tn in t_nodes[1:]:
            tn.text = ""
    return etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", standalone=True
    )


# ──────────────────────────────────────────────
# 텍스트 노드 치환
# ──────────────────────────────────────────────

def _flatten_runs(paragraphs: list) -> List[str]:
    """paragraphs JSON 내 모든 run의 text를 문서 순서대로 평탄화."""
    result: List[str] = []
    for para in paragraphs:
        runs = para.get("runs", [])
        if runs:
            for r in runs:
                result.append(_normalize_text(r.get("text", "")))
        else:
            text = _normalize_text(para.get("text", ""))
            if text:
                result.append(text)
    return result


def _replace_t_nodes(t_nodes: list, translated: List[str]) -> None:
    """슬라이드 XML 내 <a:t> 노드들과 번역 텍스트 리스트를 1:1 매칭하여 교체."""
    n_orig = len(t_nodes)
    n_new = len(translated)
    if n_orig == 0:
        return
    if n_new == 0:
        for tn in t_nodes:
            tn.text = ""
        return
    if n_new == n_orig:
        for tn, txt in zip(t_nodes, translated):
            tn.text = txt
    elif n_new > n_orig:
        # 앞쪽 1:1, 초과분은 마지막 <a:t>에 합침
        for i in range(n_orig - 1):
            t_nodes[i].text = translated[i]
        t_nodes[-1].text = "".join(translated[n_orig - 1:])
    else:
        # 번역이 더 적음 — 앞쪽 채우고 나머지는 빈 문자열
        for i, tn in enumerate(t_nodes):
            tn.text = translated[i] if i < n_new else ""


def _apply_kr_font(elem, font_map: dict) -> None:
    """elem 하위 모든 <a:rPr>/<a:defRPr>의 latin/ea typeface를 한글 폰트로 override.

    - latin이 이미 있으면 그 typeface를 font_map에서 lookup하여 한글 폰트로 교체
    - ea가 없으면 latin과 동일한 한글 폰트로 추가 (한글 표시 안정성)
    - bold/italic/color/size 등 다른 속성은 일절 건드리지 않음
    """
    default_kr = font_map.get("__default__", "Pretendard")
    for rpr_tag in ("rPr", "defRPr", "endParaRPr"):
        for rPr in elem.iter(f"{{{A}}}{rpr_tag}"):
            latin = rPr.find(f"{{{A}}}latin")
            kr_font = default_kr
            if latin is not None:
                eng_font = latin.get("typeface")
                kr_font = font_map.get(eng_font) or default_kr
                latin.set("typeface", kr_font)
            ea = rPr.find(f"{{{A}}}ea")
            if ea is not None:
                eng_ea = ea.get("typeface")
                ea.set("typeface", font_map.get(eng_ea) or kr_font)


# ──────────────────────────────────────────────
# 유틸
# ──────────────────────────────────────────────

def _match_index(filename: str, pattern: re.Pattern) -> Optional[int]:
    m = pattern.match(filename)
    return int(m.group(1)) if m else None


def _cache_load(cache: dict, key: int, path: str):
    if key in cache:
        return cache[key]
    if not os.path.exists(path):
        cache[key] = None
        return None
    with open(path, encoding="utf-8") as f:
        cache[key] = json.load(f)
    return cache[key]


def _normalize_text(s: str) -> str:
    """LLM이 escape 형태로 반환한 PowerPoint 제어 문자를 XML 호환 문자로 복원.

    XML 1.0 허용 제어문자: \t(0x09), \n(0x0A), \r(0x0D)
    그 외 0x00~0x1F 및 0x7F는 모두 제거하거나 줄바꿈으로 대체한다.
    """
    if not s:
        return ""
    # PowerPoint 제어문자 escape → 줄바꿈 (vertical tab은 XML invalid이므로 \n으로 대체)
    s = (s.replace("_x000B_", "\n")
          .replace("_x000D_", "\n")
          .replace("_x000A_", "\n"))
    # 잔여 XML invalid 제어문자 제거
    return _INVALID_XML_RE.sub("", s)


_INVALID_XML_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
