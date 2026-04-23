"""
com_app_microsoft.py — PowerPoint COM Automation 공통 헬퍼

pywin32(win32com)로 PowerPoint 데스크톱 애플리케이션을 제어하기 위한
컨텍스트 매니저와 enum 상수를 제공한다.

전제 조건:
  - Windows 환경 (WSL 불가, Windows native Python에서 실행)
  - Microsoft PowerPoint 데스크톱 설치
  - pip install pywin32

사용 예:
    from library.com_app_microsoft import powerpoint_app, open_presentation

    with powerpoint_app() as app:
        with open_presentation(app, "C:/path/file.pptx") as prs:
            for slide in prs.Slides:
                ...
"""
from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from typing import Iterator

try:
    import pythoncom
    import win32com.client
except ImportError as e:  # pragma: no cover
    raise RuntimeError(
        "pywin32 가 필요합니다. 'pip install pywin32' 후 Windows native Python 에서 실행하세요."
    ) from e


# ──────────────────────────────────────────────
# msoTriState / 주요 PowerPoint enum
# ──────────────────────────────────────────────
MSO_TRUE  = -1
MSO_FALSE = 0

# msoShapeType (https://learn.microsoft.com/office/vba/api/office.msoshapetype)
MSO_SHAPE_AUTOSHAPE       = 1
MSO_SHAPE_CHART           = 3
MSO_SHAPE_GROUP           = 6
MSO_SHAPE_LINKED_PICTURE  = 11
MSO_SHAPE_PICTURE         = 13
MSO_SHAPE_PLACEHOLDER     = 14
MSO_SHAPE_TEXT_BOX        = 17
MSO_SHAPE_TABLE           = 19
MSO_SHAPE_SMARTART        = 24

# ppSaveAsFileType
PP_SAVE_AS_OPEN_XML_PRESENTATION = 24  # .pptx

# Export filter (Shape.Export)
PP_SHAPE_FORMAT_JPG = 1
PP_SHAPE_FORMAT_PNG = 2


# ──────────────────────────────────────────────
# 컨텍스트 매니저
# ──────────────────────────────────────────────

@contextmanager
def powerpoint_app(visible: bool = False) -> Iterator:
    """PowerPoint 애플리케이션 인스턴스를 생성하고 종료까지 보장한다.

    Parameters
    ----------
    visible : True 면 PowerPoint 창을 표시 (디버그용). 기본값 False.

    Notes
    -----
    PowerPoint는 일부 작업에서 Visible=False 시 오류가 발생할 수 있으므로,
    문제가 생기면 visible=True 로 호출하거나 WindowState 을 최소화하라.
    """
    if sys.platform != "win32":
        raise RuntimeError("PowerPoint COM Automation 은 Windows 에서만 동작합니다.")

    pythoncom.CoInitialize()
    app = None
    try:
        app = win32com.client.DispatchEx("PowerPoint.Application")
        try:
            app.Visible = MSO_TRUE if visible else MSO_FALSE
        except Exception:
            # 일부 버전은 Visible=False 설정 시 예외 발생 → 무시
            pass
        yield app
    finally:
        try:
            if app is not None:
                app.Quit()
        except Exception:
            pass
        pythoncom.CoUninitialize()


@contextmanager
def open_presentation(app, pptx_path: str, read_only: bool = False) -> Iterator:
    """프레젠테이션을 열고 닫음을 보장한다.

    Parameters
    ----------
    app       : powerpoint_app() 컨텍스트로 받은 Application 객체
    pptx_path : 절대 경로 (Windows 경로, 슬래시 양쪽 모두 허용)
    read_only : True 면 변경 저장 불가
    """
    abs_path = os.path.abspath(pptx_path).replace("/", "\\")
    prs = app.Presentations.Open(
        abs_path,
        ReadOnly  = MSO_TRUE if read_only else MSO_FALSE,
        Untitled  = MSO_FALSE,
        WithWindow= MSO_FALSE,
    )
    try:
        yield prs
    finally:
        try:
            prs.Close()
        except Exception:
            pass


# ──────────────────────────────────────────────
# 단위 변환 유틸
# ──────────────────────────────────────────────

def points_to_emu(pts: float) -> int:
    """포인트 → EMU (1 pt = 12700 EMU)."""
    return int(round(pts * 12700))


def emu_to_points(emu: int) -> float:
    """EMU → 포인트."""
    return emu / 12700.0


def color_int_to_hex(color_int: int) -> str:
    """COM 의 BGR 정수 컬러를 #RRGGBB 로 변환."""
    if color_int is None or color_int < 0:
        return None
    b = (color_int >> 16) & 0xFF
    g = (color_int >> 8) & 0xFF
    r = color_int & 0xFF
    return f"#{r:02X}{g:02X}{b:02X}"


def hex_to_color_int(hex_str: str) -> int:
    """#RRGGBB → BGR 정수."""
    s = hex_str.lstrip("#")
    r = int(s[0:2], 16)
    g = int(s[2:4], 16)
    b = int(s[4:6], 16)
    return (b << 16) | (g << 8) | r
