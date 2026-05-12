# content_parser

PDF content stream operator parser 설계를 설명하는 디렉토리다.

BT/ET, Tf, Tm, Td, Tj, TJ 같은 text 관련 operator와 operand range를 추출한다.

## 추적 대상

```text
BT, ET
Tf
Tm
Td, TD
T*
Tj, TJ
Tc, Tw, Tz, TL, Tr, Ts
q, Q, cm
```

## 산출물

```text
text block range
operator sequence
operand range
encoded text payload
current text state snapshot
```

## 입력 관계

```text
원본 source.pdf content stream
	실제 복원 대상 stream과 operandRange의 기준

qpdf/source.qdf.pdf
	사람이 확인하기 쉬운 reference
	parser 검증과 디버깅에 사용
```

raw-pdf-text-state.json의 range 값은 최종적으로 원본 source.pdf stream에 적용 가능해야 한다. qpdf reference만 보고 range를 만들지 않는다.
