# validation

검증 기준과 실패 조건을 설명하는 디렉토리다.

검증은 다음 단계에서 수행한다.

```text
원본 PDF qpdf --check
raw JSON 추출 completeness 확인
translation id 매칭 확인
replacementEncoded 생성 확인
operandRange 일치 확인
최종 PDF qpdf --check
```

검증 실패 PDF는 output으로 publish하지 않는다.
