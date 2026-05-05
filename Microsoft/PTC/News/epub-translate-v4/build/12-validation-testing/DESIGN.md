# Validation and Testing 설계

## 목적

포맷별 번역 결과가 실제로 생성되고 열릴 수 있는지 검증하는 테스트 전략을 정의한다.

## 테스트 계층

```text
Unit test
  format detection, segment extraction, masking, metadata writer

Adapter fixture test
  epub/azw3/mobi/kfx sample 처리

Pipeline test
  input -> output -> metadata 전체 흐름

Validation test
  output file exists, same extension, reader reopen
```

## 포맷별 검증

| 포맷 | 1차 검증 | 향후 검증 |
|---|---|---|
| EPUB | 다시 열기, OPF/XHTML 확인 | EPUBCheck 연동 |
| AZW3 | adapter reader로 다시 열기 | Kindle Previewer 확인 |
| MOBI | adapter reader로 다시 열기 | Kindle/Calibre 확인 |
| KFX | 구조 재분석 | Kindle Previewer 또는 전용 검증 |

## 샘플 정책

- DRM 없는 작은 샘플만 사용한다.
- 저작권 문제가 있는 실제 도서는 repository에 넣지 않는다.
- 테스트 fixture는 직접 만든 최소 전자책을 우선한다.
- 큰 샘플은 별도 보관하고 checksum만 문서화한다.

## 완료 기준

- 각 adapter별 최소 fixture test 계획이 있다.
- pipeline 전체 성공/실패/skip 테스트가 있다.
- metadata JSON schema 검증이 있다.
- known limitation은 expected failure로 관리한다.
