"""
main.py — PPTX 한글 번역 파이프라인

사용법:
  python main.py [--llm openai|azure] [--engine python-pptx|microsoft] [--step4]

옵션:
  --llm openai           표준 OpenAI API 사용 (OPENAI_API_KEY + OPENAI_MODEL)  [기본값]
  --llm azure            Azure OpenAI 사용 (AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT)
  --engine python-pptx   python-pptx 기반 처리 (기본값, WSL/Linux 가능)
  --engine microsoft     PowerPoint COM Automation (pywin32) 기반 처리
                         → Windows native Python + PowerPoint 데스크톱 설치 필요
  --step4                설명자료 생성(STEP 4)도 함께 실행 (template_guide.pptx 필요)

파이프라인 흐름:
  eng/ 파일 목록 수집
  └─ 파일별 반복:
       STEP 1  슬라이드 클리어/복사  (step1_clear[_microsoft].py)
       STEP 2  컴포넌트 추출        (step2_extract[_microsoft].py)
       STEP 3  번역 + 재생성        (step3_translate[_microsoft].py)
      [STEP 4] 설명자료 생성        (step4_guide.py)  ← --step4 옵션 시에만
"""
import argparse
import os
import sys

from library.config import Config
from library import step1_clear, step2_extract, step3_translate, step4_guide
from library import step1_clear_microsoft, step2_extract_microsoft, step3_translate_microsoft
from library import ppt_converter, logger
from library import progress_manager


# ──────────────────────────────────────────────
# 진입점
# ──────────────────────────────────────────────

def main() -> None:
    args = _parse_args()
    cfg  = Config.from_env(llm_backend=args.llm)
    cfg.ensure_dirs()

    print(f"[main] LLM 백엔드: {cfg.llm_backend.upper()} / 모델: {cfg.model}")
    print(f"[main] PPTX 엔진: {args.engine}")
    client = cfg.build_llm_client()

    files = _collect_files(cfg.eng_dir)
    if not files:
        print(f"[main] eng/ 에 처리할 파일이 없습니다: {cfg.eng_dir}")
        return

    print(f"[main] 처리 대상 파일 {len(files)}개\n")

    for file_path in files:
        _process_file(file_path, cfg, client, engine=args.engine, run_step4=args.step4)

    print("\n[main] 전체 처리 완료")


# ──────────────────────────────────────────────
# 파일 1개 처리
# ──────────────────────────────────────────────

def _process_file(file_path: str, cfg: Config, client, engine: str, run_step4: bool) -> None:
    filename = os.path.basename(file_path)
    ext      = os.path.splitext(filename)[1].lower()
    stem     = os.path.splitext(filename)[0]

    print(f"{'='*60}")
    print(f"처리 시작: {filename}  [engine: {engine}]")
    print(f"{'='*60}")

    # 로거 초기화 (파일별 로그 파일 생성)
    log = logger.setup(cfg.work_dir, stem)

    # .ppt → .pptx 변환 (필요 시)
    pptx_path  = _to_pptx_if_needed(file_path, ext, cfg)
    is_temp    = (pptx_path != file_path)

    # 엔진별 step 모듈 선택
    s1, s2, s3 = _select_steps(engine)

    try:
        progress_manager.init_progress(cfg.work_dir, filename, total_slides=0)

        # ── STEP 1 ──────────────────────────────
        s1.run(pptx_path, cfg, stem)
        progress_manager.update_step(cfg.work_dir, filename, "extract", "pending")

        # ── STEP 2 ──────────────────────────────
        total_slides = s2.run(pptx_path, cfg, stem, client)
        progress_manager.update_step(cfg.work_dir, filename, "extract",       "done")
        progress_manager.update_step(cfg.work_dir, filename, "font_analysis", "done")

        # ── STEP 3 ──────────────────────────────
        progress_manager.update_step(cfg.work_dir, filename, "translation", "in_progress")
        s3.run(cfg, stem, client)
        progress_manager.update_step(cfg.work_dir, filename, "translation", "done")
        progress_manager.update_step(cfg.work_dir, filename, "dict_update", "done")

        # ── STEP 4 (선택) ───────────────────────
        if run_step4:
            step4_guide.run(cfg, stem, client, total_slides)

        # 완료 처리
        _finalize(file_path, cfg, filename)
        progress_manager.mark_completed(cfg.work_dir, filename)

    except Exception as e:
        log = logger.get()
        log.error(f"[main] {filename} 처리 중 오류: {e}", exc_info=True)
        print(f"[main] {filename} 처리 중 오류: {e}", file=sys.stderr)

    finally:
        # .ppt 변환 임시 파일 삭제
        if is_temp and os.path.exists(pptx_path):
            os.remove(pptx_path)


# ──────────────────────────────────────────────
# 유틸
# ──────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PPTX 한글 번역 파이프라인")
    parser.add_argument(
        "--llm",
        choices=["openai", "azure"],
        default="openai",
        help="LLM 백엔드 선택: openai (기본값) 또는 azure",
    )
    parser.add_argument(
        "--engine",
        choices=["python-pptx", "microsoft"],
        default="python-pptx",
        help="PPTX 처리 엔진 선택: python-pptx (기본값) 또는 microsoft (PowerPoint COM)",
    )
    parser.add_argument("--step4", action="store_true", help="설명자료 생성(STEP 4) 포함")
    return parser.parse_args()


def _select_steps(engine: str):
    """엔진명에 따라 (step1, step2, step3) 모듈 튜플을 반환한다."""
    if engine == "microsoft":
        return step1_clear_microsoft, step2_extract_microsoft, step3_translate_microsoft
    return step1_clear, step2_extract, step3_translate


def _collect_files(eng_dir: str) -> "list[str]":
    """eng/ 에서 .pptx / .ppt 파일을 알파벳 순으로 수집."""
    return sorted(
        os.path.join(eng_dir, f)
        for f in os.listdir(eng_dir)
        if f.lower().endswith((".pptx", ".ppt"))
    )


def _to_pptx_if_needed(file_path: str, ext: str, cfg: Config) -> str:
    """확장자가 .ppt 이면 LibreOffice로 변환 후 임시 경로 반환."""
    if ext == ".ppt":
        return ppt_converter.to_pptx(file_path, cfg.temp_dir)
    return file_path


def _finalize(original_path: str, cfg: Config, filename: str) -> None:
    """처리 완료된 원본 파일을 eng/ → done/ 으로 이동."""
    import shutil
    os.makedirs(cfg.done_dir, exist_ok=True)
    dst = os.path.join(cfg.done_dir, filename)
    shutil.move(original_path, dst)
    print(f"[main] 원본 이동: eng/{filename} → done/")


if __name__ == "__main__":
    main()
