# PIPELINE — pdf-translate-v3

`runPipeline()` 의 단계별 명세.

## DETECT

- `INPUT_DIR` 의 `.pdf` 파일을 수집한다.
- `~$*` 임시 파일은 제외한다.
- 디렉토리/심볼릭 링크는 무시한다 (`fs.statSync().isFile()`).

## EXTRACT

- 각 PDF 에 대해 `pdftr text <pdf> --json` 호출.
- 응답: `Vec<PageText>` (`{ page, width, height, runs: [{ text, x, y, font_size, font_resource }] }`).
- `pdf_analysis::extract` 가 ToUnicode CMap 까지 적용한 텍스트 런을 반환.
- `pipeline.flattenSegments` 가 빈 텍스트 런을 거르고 `{ id, page, runIndex, x, y, fontSize, text }` 형태로 평탄화한다.
- 결과: `work/<stem>/segments.json`.

세그먼트가 0개인 PDF (스캔 이미지만 있는 등) 는 `error.json` 에 사유를 기록하고 `skipped` 로 처리한다.

## TRANSLATE

- `glossary.csv` 의 protected term 을 placeholder 로 치환 (`__PDFSTR_TERM_NNNN__`).
- URL / Email / 변수 (`{{...}}`, `${...}`) 도 같은 방식으로 보호.
- 각 segment 에 대해 `tmGet()` 으로 캐시 조회.
- 캐시 miss 만 모아 `BATCH_SIZE` 단위로 LLM 호출.
- LLM 응답이 `=== N === ... === N+1 ===` 형식을 어기면 segment 단위로 재시도.
- 모든 재시도 실패 시 해당 segment 는 untranslated 로 기록되고 출력에는 포함되지 않는다.
- placeholder 누락/순서 변경 시 원문 fallback (TM 에 저장하지 않음).
- 성공 segment 는 `tmPut()` 으로 SQLite 에 저장.
- 결과: `work/<stem>/translated.json` (segments + stats: hits/misses/untranslated/usage).

## APPLY

- 번역된 segment 에 대해 `EditOperation::AddText` 객체를 생성:
    - `page` = segment.page
    - `x`, `y` = segment 의 PDF 사용자 공간 좌표 (extract 결과 그대로)
    - `text` = 번역문 (placeholder 복원 후)
    - `font` = `Helvetica` (Base14, 현재 제약)
    - `size` = 원본 run 의 font_size
- 결과: `work/<stem>/edits.json`.
- `pdftr edit <input> <output> --edits <work>/edits.json` 호출.
- `pdf_incremental::IncrementalWriter` 가 원본 PDF 의 byte prefix 를 그대로 두고 incremental update section 을 append.
- 결과: `output/<stem>_<TARGET>.pdf`.

`PDF_KEEP_ORIGINAL_LANG=true` 이면 동일 좌표에 번역문이 덧씌워져 두 텍스트가 겹친다 (현재 별도 layout 정책 없음, TODO).

## DONE

- APPLY 성공 시, 원본 PDF 를 `DONE_DIR` 로 이동.
- 동일 이름 충돌 시 `<stem>_<timestamp>.pdf` 로 rename.
- `--keep-input` 또는 `PDF_KEEP_INPUT=true` 이면 이동하지 않는다.

## 실패 처리

- 어느 단계에서든 실패하면 `work/<stem>/error.json` 에 `{ source, reason, recordedAt }` 기록.
- 원본은 `input/` 에 남는다 (재시도 가능).
- 전체 PDF 1개의 실패는 다음 PDF 처리를 막지 않는다 (`runPipeline` 은 파일 단위 try/catch).

## 단계별 CLI

`run-translate.sh` 의 subcommand 로 단계만 실행 가능.

```bash
./run-translate.sh extract input/sample.pdf
./run-translate.sh translate work/sample/segments.json
./run-translate.sh apply input/sample.pdf work/sample/translated.json
```

각 단계는 독립적이며, 중간 산출물(`segments.json`, `translated.json`, `edits.json`) 을 직접 편집해 재실행할 수 있다.
