# rebuild

PDF content stream 복원 모듈 설계를 설명하는 디렉토리다.

추출 단계에서 저장한 restoreOptions를 그대로 적용하고 text payload만 replacementEncoded로 교체한다.

## 책임

```text
원본 PDF object tree 열기
pdf-input-text-state.json 읽기
streamXref와 operandRange로 교체 위치 확인
encodedOriginal을 replacementEncoded로 교체
rebuilt.pdf 저장
```

## 원칙

```text
restoreOptions의 text state/operator/font/CMap 옵션을 그대로 적용한다.
비텍스트 object/resource/operator는 수정하지 않는다.
operandRange가 맞지 않으면 실패한다.
```

## qpdf와 Rust 역할

```text
Rust/lopdf:
	원본 PDF를 열고 content stream의 text payload를 교체한다.

qpdf:
	Rust가 저장한 rebuilt.pdf를 검증하고 정리한다.
```

qpdf가 직접 text payload를 입력하지 않는다. text payload 교체는 Rust가 수행한다.
