"""
main.py — PPTX 한글 번역 파이프라인

사용법:
  python main.py [--llm openai|azure] [--step4]

옵션:
  --llm openai  표준 OpenAI API 사용 (OPENAI_API_KEY + OPENAI_MODEL)  [기본값]
  --llm azure   Azure OpenAI 사용 (AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT)
  --step4       설명자료 생성(STEP 4)도 함께 실행 (template_guide.pptx 필요)

파이프라인 흐름:
  eng/ 파일 목록 수집
  └─ 파일별 반복:
       STEP 1  슬라이드 클리어   (step1_clear.py)
       STEP 2  컴포넌트 추출     (step2_extract.py)
       STEP 3  번역 + 재생성     (step3_translate.py)
      [STEP 4] 설명자료 생성     (step4_guide.py)  ← --step4 옵션 시에만
"""
import argparse
import os
import sys

from library.config import Config
from library import step1_clear, step2_extract, step3_translate, step4_guide
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
    client = cfg.build_llm_client()

    files = _collect_files(cfg.eng_dir)
    if not files:
        print(f"[main] eng/ 에 처리할 파일이 없습니다: {cfg.eng_dir}")
        return

    print(f"[main] 처리 대상 파일 {len(files)}개\n")

    for file_path in files:
        _process_file(file_path, cfg, client, run_step4=args.step4)

    print("\n[main] 전체 처리 완료")


# ──────────────────────────────────────────────
# 파일 1개 처리
# ──────────────────────────────────────────────

def _process_file(file_path: str, cfg: Config, client, run_step4: bool) -> None:
    filename = os.path.basename(file_path)
    ext      = os.path.splitext(filename)[1].lower()
    stem     = os.path.splitext(filename)[0]

    print(f"{'='*60}")
    print(f"처리 시작: {filename}")
    print(f"{'='*60}")

    # 로거 초기화 (파일별 로그 파일 생성)
    log = logger.setup(cfg.work_dir, stem)

    # .ppt → .pptx 변환 (필요 시)
    pptx_path  = _to_pptx_if_needed(file_path, ext, cfg)
    is_temp    = (pptx_path != file_path)

    try:
        progress_manager.init_progress(cfg.work_dir, filename, total_slides=0)

        # ── STEP 1 ──────────────────────────────
        step1_clear.run(pptx_path, cfg, stem)
        progress_manager.update_step(cfg.work_dir, filename, "extract", "pending")

        # ── STEP 2 ──────────────────────────────
        total_slides = step2_extract.run(pptx_path, cfg, stem, client)
        progress_manager.update_step(cfg.work_dir, filename, "extract",       "done")
        progress_manager.update_step(cfg.work_dir, filename, "font_analysis", "done")

        # ── STEP 3 ──────────────────────────────
        progress_manager.update_step(cfg.work_dir, filename, "translation", "in_progress")
        step3_translate.run(cfg, stem, client)
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
    parser.add_argument("--step4", action="store_true", help="설명자료 생성(STEP 4) 포함")
    return parser.parse_args()


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
