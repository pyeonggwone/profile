# json-state

v9 JSON 상태 파일 구조를 설명하는 디렉토리다.

```text
raw-pdf-text-state.json       PDF 내부 원본 상태
readable-text-state.json      사람이 읽는 번역용 상태
translation-input.json        OpenAI 요청 입력
translation-results.json      OpenAI 응답 결과
pdf-input-text-state.json     PDF 복원 입력 상태
```

복원 단계는 raw JSON의 restoreOptions를 그대로 사용한다.
