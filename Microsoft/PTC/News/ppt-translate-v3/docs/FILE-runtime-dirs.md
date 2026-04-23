# 런타임 디렉토리 — 요구사항 명세

`input/`, `output/`, `work/`, `input/done/` 의 역할과 lifecycle.

## 디렉토리 트리

```
ppt-translate-v3/
├── input/                  # 사용자 입력 (.pptx)
│   └── done/               # 번역 완료된 원본 자동 이동
├── output/                 # 번역 결과 (<stem>_KO.pptx)
└── work/                   # 중간 산출물 + TM
    ├── tm.sqlite           # Translation Memory (전역 캐시)
    └── <stem>/             # 파일별 작업 디렉토리
        ├── segments.json   # EXTRACT 결과
        ├── translated.json # TRANSLATE 결과
        └── verify_pass1.json (선택)
```

## `input/`

- 사용자가 `.pptx` / `.ppt` 를 둠.
- 배치 모드(`run input`)는 이 디렉토리를 스캔.
- **PowerPoint 임시 파일** (`~$*.pptx`) 은 자동 제외.
- **읽기 전용 마인드**: APPLY 는 항상 출력으로 복사 후 작업. 원본은 변경되지 않고 done/ 으로 이동만 됨.

## `input/done/`

- `--move-done` (기본 활성) 시, 한 파일 처리 성공 후 즉시 이동.
- 동일 이름 충돌 시 `<stem>_<mtime>.pptx` 로 rename.
- 실패 파일은 이동하지 않음 (input/ 에 남음 → 재시도 가능).

## `output/`

- 출력 파일명: `<stem>_<TARGET_LANG.upper()>.pptx`. 기본 `<stem>_KO.pptx`.
- 부모 디렉토리 자동 생성.
- 입력이 `input/` 안에 있으면 출력은 같은 부모(`ppt-translate-v3/`) 의 `output/`. 그 외엔 입력 파일 옆.

## `work/`

### `work/tm.sqlite`

- **전역 Translation Memory**. 모든 파일이 공유.
- 스키마: [FILE-ppt_translate.md §5.2](FILE-ppt_translate.md).
- 삭제 시 다음 실행에서 전부 재번역 (모델 변경/프롬프트 변경 후 권장).

### `work/<stem>/`

- 한 파일 작업 단위. 파일명에서 확장자 제거한 이름.
- `segments.json` (EXTRACT 산출) — 디버깅/재실행 가능.
- `translated.json` (TRANSLATE 산출) — APPLY 직접 호출용.
- `verify_passN.json` (VERIFY 활성 시) — 잔여 영문 재번역 결과.
- 다음 실행 시 그대로 덮어씀 (보존 안 함).

## .gitignore 권장

```
.env
work/
input/
input/done/
output/
*.pptx
*.PPTX
~$*
```

## 라이프사이클 다이어그램

```
input/foo.pptx
  │
  ▼  EXTRACT
work/foo/segments.json
  │
  ▼  TRANSLATE   (TM hit / miss)
work/foo/translated.json   ←→  work/tm.sqlite
  │
  ▼  APPLY
output/foo_KO.pptx
  │
  ▼  VERIFY (optional pass)
output/foo_KO.pptx (overwrite)
  │
  ▼  move-done
input/done/foo.pptx
```

## 비책임

- 자동 정리(GC) 없음. `work/<stem>/` 는 사용자가 직접 관리.
- 출력 파일 덮어쓰기 경고 없음 (PowerPoint 가 열고 있으면 OS 가 거부 → exception).
- 동시 실행 안전성 보장 안 함 (단일 사용자, 단일 프로세스 가정).
