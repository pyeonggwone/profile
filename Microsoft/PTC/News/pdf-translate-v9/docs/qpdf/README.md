# qpdf

qpdf 사용 방식을 설명하는 디렉토리다.

qpdf는 PDF를 번역하지 않는다. qpdf는 다음 역할만 가진다.

```text
원본 PDF 구조 확인
QDF reference 생성
최종 PDF 구조 검증
```

text operator 추출, CMap 변환, payload 교체는 Rust 쪽 책임이다.
