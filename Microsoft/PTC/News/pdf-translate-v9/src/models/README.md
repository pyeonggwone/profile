# models

JSON schema와 내부 상태 모델 설계를 설명하는 디렉토리다.

raw state, readable state, translation state, pdf input state, report state의 필드 구조를 정의한다.

## 주요 모델

```text
PdfSource
RawPdfTextState
RawTextRun
RestoreOptions
TextPayload
ReadableTextState
TranslationInput
TranslationResults
PdfInputTextState
RebuildReport
ValidationReport
```

## 원칙

```text
restoreOptions와 textPayload를 분리한다.
번역으로 변경 가능한 필드는 textPayload에만 둔다.
```
