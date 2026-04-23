"""
logger.py — 파이프라인 공용 로거
콘솔 출력과 파일 기록을 동시에 수행한다.
로그 저장 경로: work/logs/{stem}_{timestamp}.log
"""
import logging
import os
import sys
from datetime import datetime
from typing import Optional


_logger: Optional[logging.Logger] = None


def setup(work_dir: str, stem: str) -> logging.Logger:
    """
    파일명 기반 로거 초기화. main.py에서 파일 처리 시작 전 1회 호출.
    이후 모든 모듈에서 get()으로 동일 로거 사용.
    """
    global _logger

    log_dir = os.path.join(work_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"{stem}_{timestamp}.log")

    logger = logging.getLogger("pipeline")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    # 파일 핸들러 (DEBUG 이상 전부)
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    ))
    logger.addHandler(fh)

    # 콘솔 핸들러 (INFO 이상만)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(ch)

    logger.info(f"로그 파일: {log_path}")
    _logger = logger
    return logger


def get() -> logging.Logger:
    """초기화된 로거 반환. setup() 전에 호출하면 기본 로거 반환."""
    if _logger is None:
        return logging.getLogger("pipeline")
    return _logger
