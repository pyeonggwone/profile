# architecture

v9 전체 처리 구조를 설명하는 디렉토리다.

```text
input PDF
  -> qpdf reference 생성
  -> Rust raw text state 추출
  -> readable JSON 변환
  -> OpenAI 번역
  -> PDF 입력용 JSON 변환
  -> Rust text payload 교체
  -> qpdf 최종 검증
  -> output PDF
```

핵심 원칙은 비텍스트 PDF 객체는 유지하고 텍스트 payload만 교체하는 것이다.
