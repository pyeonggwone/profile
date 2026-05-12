# Output Preservation 설계

## 목적

번역 후 원본과 같은 포맷으로 output을 생성하고, 가능한 한 원본 구조와 리소스를 보존하는 정책을 정의한다.

## 공통 출력 규칙

```text
input/book.epub  -> output/book_KR.epub
input/book.azw3  -> output/book_KR.azw3
input/book.mobi  -> output/book_KR.mobi
input/book.kfx   -> output/book_KR.kfx
```

## 보존 대상

- 원본 포맷
- 본문 구조
- 목차와 navigation 정보
- 이미지
- CSS 또는 스타일 정보
- font resource
- metadata
- 내부 record 또는 fragment 순서
- 알 수 없는 리소스

## 공통 Writer 원칙

- 번역 대상 텍스트 외의 바이트나 리소스는 가능한 한 변경하지 않는다.
- 모르는 구조는 해석하지 않고 보존한다.
- 출력 전 내부 index, offset, length, checksum이 필요한 포맷은 갱신한다.
- 저장 실패 시 partial output을 최종 결과로 간주하지 않는다.

## Output 검증 정보

metadata JSON에는 다음 검증 결과를 넣을 수 있어야 한다.

- output file exists
- output file size
- output extension
- same format 여부
- adapter validation status
- external viewer validation status, 향후 항목

## 완료 기준

- 각 adapter가 동일 포맷 output path를 반환한다.
- 실패한 output은 성공으로 기록하지 않는다.
- 알 수 없는 리소스를 삭제하지 않는 정책이 adapter별 문서에 반영된다.
