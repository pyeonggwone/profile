# openai

OpenAI 번역 연동 설계를 설명하는 디렉토리다.

OpenAI에는 PDF 내부 operator, font, CMap 정보를 보내지 않는다.

```text
입력: id + decoded source text
출력: id + translated text
```

PDF 복원에 필요한 상태 정보는 Rust가 raw JSON에서 유지한다.
