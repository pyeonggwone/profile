# readable

raw JSON을 사람이 읽기 좋은 번역용 JSON으로 변환하는 모듈 설계를 설명하는 디렉토리다.

PDF 내부 상태는 유지하고 번역 가능한 decoded text만 분리한다.

## 책임

```text
encodedOriginal decode
source text 생성
decode method/confidence 기록
OpenAI 번역 대상 item 생성
restoreOptions reference 유지
```

## 원칙

```text
사람이 읽기 좋은 JSON은 raw JSON을 대체하지 않는다.
raw JSON의 restoreOptions는 그대로 보존한다.
```
