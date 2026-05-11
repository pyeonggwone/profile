# Input Format Detection 설계

## 목적

`input/` 내부 파일을 스캔하고, 확장자와 파일 시그니처를 기준으로 실제 전자책 포맷을 감지한다.

## 처리 흐름

```text
input scan
  -> candidate file filter
  -> extension check
  -> binary signature check
  -> format confidence 결정
  -> adapter routing
```

## 지원 확장자

| 확장자 | 포맷 |
|---|---|
| `.epub` | EPUB |
| `.azw3` | AZW3 / Kindle KF8 |
| `.mobi` | MOBI |
| `.kfx` | KFX |

## 감지 기준

확장자만 믿지 않고 내부 시그니처도 확인한다.

- EPUB: ZIP 구조, `mimetype`, `META-INF/container.xml`
- AZW3/MOBI: Palm database header, MOBI/KF8 관련 header 정보
- KFX: KFX container signature와 fragment 구조 존재 여부
- 알 수 없는 파일: unsupported로 기록하고 처리하지 않음

## 결과 모델

```json
{
  "filePath": "input/book.azw3",
  "extension": ".azw3",
  "format": "azw3",
  "confidence": "high",
  "reason": "extension and header matched"
}
```

## 완료 기준

- 지원 포맷 파일만 pipeline에 전달한다.
- 확장자와 내부 포맷이 불일치하면 warning을 남긴다.
- unsupported 파일은 metadata 또는 summary에 기록된다.
- adapter routing이 format string 하나로 결정된다.
