# TODO

## Format Preservation

- EPUB 구조 보존 품질 검증
- AZW3 native reader/writer 완성도 개선
- MOBI native reader/writer 완성도 개선
- KFX native reader/writer 완성도 개선
- 원본 메타데이터 보존 강화
- 목차/내비게이션 보존 강화
- 이미지/폰트/CSS 리소스 보존 강화
- Kindle 전용 메타데이터 보존 검토
- KFX enhanced typesetting 정보 보존 검토

## Translation Quality

- segment 분리 품질 개선
- 문단 단위/문장 단위 번역 옵션 추가
- placeholder 검증 강화
- glossary 적용 품질 개선
- translation memory hit rate 기록

## Metadata

- 책별 token usage 기록
- 책별 word count 기록
- 책별 번역 시간 기록
- 책별 실패/스킵 사유 기록
- metadata schema version 추가

## Validation

- 포맷별 output 파일 열림 검증
- EPUBCheck 연동
- Kindle Previewer 연동 검토
- Calibre ebook-viewer 검증
- 샘플 파일 기반 regression test 추가

## CLI

- input/output/work/metadata directory 옵션 추가
- 특정 포맷만 처리하는 옵션 추가
- dry-run 옵션 추가
- metadata-only 옵션 추가
- verbose/debug 로그 옵션 추가
