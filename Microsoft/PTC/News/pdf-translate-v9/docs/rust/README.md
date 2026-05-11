# rust

Rust 처리 설계를 설명하는 디렉토리다.

Rust는 qpdf가 풀어준 reference와 원본 PDF를 기준으로 PDF 내부 텍스트 구조를 다룬다.

```text
content stream parser
text state tracker
font/CMap decoder
translation payload encoder
content stream payload replacer
```

Rust는 새 레이아웃을 만들지 않고 추출한 상태를 기준으로 기존 payload만 교체한다.
