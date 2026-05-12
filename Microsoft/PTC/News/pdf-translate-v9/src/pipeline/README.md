# pipeline

pipeline 모듈 설계를 설명하는 디렉토리다.

각 단계의 입력과 출력만 연결하고, PDF 내부 처리는 하위 모듈에 위임한다.

```text
init -> state_store -> qpdf -> extract -> readable -> terms -> translate/TM -> pdf-input -> rebuild -> validate -> publish
```

## 단계

```text
01_init_job
02_qpdf_reference
03_extract_raw_pdf_text_state
04_convert_raw_to_readable_text_state
05_extract_and_apply_job_terms
06_translate_readable_text_state
07_convert_translation_to_pdf_input_state
08_rebuild_pdf_with_extracted_options
09_qpdf_validate_output
10_publish_output
```

## 원칙

```text
각 단계는 입력 JSON과 출력 JSON을 명확히 가진다.
이전 단계 산출물을 암묵적으로 수정하지 않는다.
각 단계 시작/완료/실패 상태는 state.sqlite에 기록한다.
복원 단계는 raw JSON의 restoreOptions를 그대로 사용한다.
```

## 단계별 입출력

| 단계 | 입력 | 처리 | 출력 |
|---|---|---|---|
| 01_init_job | input PDF | 원본 PDF 복사, sha256 계산 | source.pdf, pdf-source.json |
| 02_qpdf_reference | source.pdf | qpdf QDF 변환, qpdf check | source.qdf.pdf, qpdf-check.json |
| 03_extract_raw_pdf_text_state | source.pdf, source.qdf.pdf | Rust parser가 text operator/state/font/CMap/range 추출 | raw-pdf-text-state.json |
| 04_convert_raw_to_readable_text_state | raw-pdf-text-state.json | encoded text를 decoded source로 변환 | readable-text-state.json |
| 05_extract_and_apply_job_terms | readable-text-state.json | 고유명사 후보 추출, job별 용어집 반영 | proper-noun-candidates.json, job-terms.json |
| 06_translate_readable_text_state | readable-text-state.json, job-terms.json, tm.sqlite | TM 조회 후 OpenAI id/text chunk 번역 | translation-input.json, translation-results.json, TM update |
| 07_convert_translation_to_pdf_input_state | raw state, translation results | restoreOptions와 translated text 병합, replacementEncoded 생성 | pdf-input-text-state.json |
| 08_rebuild_pdf_with_extracted_options | source.pdf, pdf-input-text-state.json | text payload만 교체 | rebuilt.pdf, rebuild-report.json |
| 09_qpdf_validate_output | rebuilt.pdf | qpdf --check | validation-report.json |
| 10_publish_output | rebuilt.pdf, validation-report.json | 검증 통과 PDF publish | output/<source-name>_V9.pdf |

## 핵심 연결

```text
qpdf는 PDF를 풀고 검증한다.
Rust는 qpdf reference와 원본 PDF를 기준으로 텍스트 상태를 추출/변환/교체한다.
SQLite는 job 상태, step 상태, TM hit/miss, artifact index를 저장한다.
OpenAI는 readable text만 번역한다.
job별 고유명사/용어집은 translation-input.json에 반영한다.
복원은 raw JSON의 restoreOptions를 그대로 적용한다.
```
