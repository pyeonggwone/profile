# text_state

PDF text state 추적 모듈 설계를 설명하는 디렉토리다.

font, size, matrix, leading, spacing, rendering mode 등 복원에 필요한 상태를 기록한다.

## 저장 항목

```text
font
fontSize
textMatrix
lineMatrix
charSpacing
wordSpacing
horizontalScaling
leading
renderMode
rise
```

## 원칙

```text
추출 시점의 text state snapshot을 restoreOptions에 저장한다.
복원 단계는 이 값을 그대로 사용한다.
```
