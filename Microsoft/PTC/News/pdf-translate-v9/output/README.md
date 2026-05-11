# output

최종 PDF 산출물을 저장하는 디렉토리다.

## 역할

```text
qpdf 검증을 통과한 최종 PDF만 저장한다.
파일명 형식은 <source-name>_V9.pdf 를 기본으로 한다.
```

## 하위 디렉토리

```text
validated/  최종 검증 통과 PDF
rejected/   생성되었지만 검증 실패한 PDF
reports/    최종 처리 요약 report
```

## 원칙

```text
검증 실패 PDF는 output 으로 publish 하지 않는다.
중간 산출물은 work 디렉토리에만 둔다.
```
