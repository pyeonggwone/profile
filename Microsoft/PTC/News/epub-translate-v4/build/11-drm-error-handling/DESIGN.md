# DRM and Error Handling 설계

## 목적

DRM 감지, unsupported 포맷, adapter 실패, LLM 실패를 일관되게 처리한다.

## DRM 원칙

- DRM이 감지된 파일은 번역하지 않는다.
- DRM 우회, 제거, 복호화 구현은 하지 않는다.
- 원본 파일은 삭제하거나 이동하지 않는다.
- metadata JSON에 `skipped` 상태와 reason을 기록한다.

## 상태 값

| status | 의미 |
|---|---|
| `success` | 번역 및 output 생성 완료 |
| `partial` | 일부 segment 실패, output 생성 완료 |
| `skipped` | DRM 또는 unsupported 등으로 처리하지 않음 |
| `failed` | 처리 중 오류로 output 생성 실패 |

## 오류 모델

```json
{
  "code": "DRM_PROTECTED",
  "message": "DRM protected file was skipped.",
  "format": "azw3",
  "recoverable": false
}
```

## 대표 오류 코드

- `UNSUPPORTED_FORMAT`
- `FORMAT_SIGNATURE_MISMATCH`
- `DRM_PROTECTED`
- `READER_FAILED`
- `TEXT_EXTRACTION_FAILED`
- `TRANSLATION_FAILED`
- `WRITER_FAILED`
- `OUTPUT_VALIDATION_FAILED`

## 완료 기준

- 모든 실패 경로가 로그와 metadata에 남는다.
- DRM 파일은 번역 시도 전에 중단된다.
- LLM 실패는 가능한 경우 segment 원문 fallback으로 처리된다.
- writer 실패는 output 성공으로 기록되지 않는다.
