# pdf_reader

PDF object tree 접근 모듈 설계를 설명하는 디렉토리다.

Rust/lopdf로 page, resource, content stream, font object를 읽는 책임을 가진다.

## 책임

```text
원본 PDF 열기
page tree 순회
page /Contents stream 확인
page /Resources 확인
font resource / XObject reference 확인
```

## 원칙

```text
비텍스트 객체는 수정하지 않는다.
원본 object id와 stream xref를 raw JSON에 기록한다.
```
