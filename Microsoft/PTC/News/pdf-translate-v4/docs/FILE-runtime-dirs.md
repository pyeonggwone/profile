# 런타임 디렉토리 — pdf-translate-v3

`input/`, `output/`, `work/`, `input/done/` 의 역할과 lifecycle.

## 디렉토리 트리

```
pdf-translate-v3/
├── input/                  # 사용자 입력 (.pdf)
│   └── done/               # 번역 완료된 원본 자동 이동
├── output/                 # 번역 결과 (<stem>_KR.pdf)
└── work/                   # 중간 산출물 + TM
    ├── tm.sqlite           # Translation Memory (전역 캐시)
    └── <stem>/             # 파일별 작업 디렉토리
        ├── segments.json   # EXTRACT 결과
        ├── translated.json # TRANSLATE 결과 + stats
        ├── edits.json      # APPLY 입력 (EditOperation 배열)
        └── error.json      # 단계 실패 시 사유 기록
```

## `input/`

- 사용자가 `.pdf` 파일을 둠.
- 일괄 모드(`./run-translate.sh`) 는 이 디렉토리를 스캔.
- `~$*` 임시 파일은 자동 제외.
- 디렉토리/심볼릭 링크는 무시 (`isFile()` 만 처리).
- **읽기 전용 마인드**: APPLY 는 항상 incremental update 로 새 PDF 를 만들고, 원본은 변경하지 않는다.

## `input/done/`

- APPLY 성공 시 즉시 이동.
- 동일 이름 충돌 시 `<stem>_<timestamp>.pdf` 로 rename.
- 실패한 파일은 이동하지 않음 (input/ 에 남음 → 재시도 가능).
- `--keep-input` 또는 `PDF_KEEP_INPUT=true` 이면 이동하지 않음.

## `output/`

- 출력 파일명: `<stem>_<TARGET_SUFFIX>.pdf`. 기본 `<stem>_KR.pdf`.
- 부모 디렉토리 자동 생성.
- 입력이 어디에 있든 출력은 `OUTPUT_DIR` (기본 `output/`) 에 일괄 저장.

## `work/`

### `work/tm.sqlite`

- **전역 Translation Memory**. 모든 PDF 가 공유.
- 스키마: `tm(src_hash PK, src, tgt, model, source_lang, target_lang, created_at)`.
- 키: `sha256(source_lang + "\n" + target_lang + "\n" + src)`.
- 삭제 = `--reset-tm` 또는 `./run-translate.sh tm reset`. 모델 변경/프롬프트 변경 후 권장.

### `work/<stem>/`

- 한 파일 작업 단위. 파일명에서 확장자 제거 + 윈도우 금지 문자 `_` 치환.
- `segments.json` (EXTRACT 산출) — 디버깅 / 재실행 가능.
- `translated.json` (TRANSLATE 산출) — APPLY 직접 호출용.
- `edits.json` (APPLY 직전 산출) — `EditOperation::AddText` 배열.
- `error.json` (실패 시) — `{ source, reason, recordedAt }`.
- 다음 실행 시 그대로 덮어씀 (보존 안 함).

## .gitignore (요점)

```
.env
node_modules/
work/
input/*
!input/.gitkeep
!input/done/
input/done/*
!input/done/.gitkeep
output/
target/
Cargo.lock
~$*
```

## 라이프사이클

```
input/foo.pdf
  │
  ▼  EXTRACT (pdftr text)
work/foo/segments.json
  │
  ▼  TRANSLATE (TM hit / miss + LLM batch)
work/foo/translated.json   ←→  work/tm.sqlite
  │
  ▼  APPLY (pdftr edit)
work/foo/edits.json    →    output/foo_KR.pdf
  │
  ▼  DONE
input/done/foo.pdf
```

## 비책임

- 자동 정리(GC) 없음. `work/<stem>/` 는 사용자가 직접 관리.
- 출력 파일 덮어쓰기 경고 없음 (overwrite).
- 동시 실행 안전성 보장 안 함 (단일 사용자, 단일 프로세스 가정).
- DRM / 암호 PDF 자동 우회 없음 (`from_bytes` 가 거부하면 EXTRACT 단계에서 실패).
