# Fixtures

이 디렉토리는 회귀 테스트용 작은 PDF 샘플을 둔다. 실제 큰 fixture는 별도 artifact storage에 두고 checksum만 문서화한다 (설계: `build/10-compatibility-testing/DESIGN.md`).

## 분류

- `basic/` — PDF 1.4, classic xref, 단순 page
- `xref-stream/` — PDF 1.5+, xref stream
- `object-stream/` — compressed object stream 포함
- `filters/` — Flate/Hex/85/RLE/LZW 단일 필터
- `incremental/` — 이미 incremental update가 있는 PDF
- `malformed/` — 의도적으로 깨진 파일

각 분류 디렉토리에 README로 fixture 출처와 의도를 적는다.

## 합성 fixture

테스트는 가능하면 합성 PDF를 사용한다. `pdf_writer::PdfFileBuilder`가 정상 동작하는지 검증하면서 동시에 reader 회귀 테스트가 된다 — 자세한 합성 헬퍼는 `crates/pdf_writer/tests`에 추가될 예정이다.
