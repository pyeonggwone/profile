# crates

Rust workspace crate 구성을 설명하는 디렉토리다.

각 crate는 README.md와 실제 Rust 구현 파일을 함께 가진다.

## 하위 디렉토리

```text
pdf_cli/              CLI entry point 설계
pdf_qpdf/             qpdf adapter 설계
pdf_core/             PDF object/stream 접근 설계
pdf_text_state/       text operator/state 추출 설계
pdf_cmap/             CMap decode/encode 설계
pdf_terms/            job별 고유명사/용어집 처리 설계
pdf_state_db/         SQLite 상태 DB 설계
pdf_rebuild/          text payload 교체 설계
pdf_translate_openai/ OpenAI 번역 adapter 설계
pdf_models/           JSON model 설계
pdf_reports/          report writer 설계
```
