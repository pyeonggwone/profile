# report

report 생성 모듈 설계를 설명하는 디렉토리다.

decode, encode, translation, rebuild, qpdf validation 결과를 job 단위로 정리한다.

## 기록 대상

```text
qpdf missing
qpdf check failed
ToUnicode missing
CMap parse failed
decode failed
encode failed
operandRange mismatch
translation missing id
```

## 원칙

```text
완성도 우선이므로 조용한 fallback을 두지 않는다.
모든 실패는 JSON report에 명시한다.
```
