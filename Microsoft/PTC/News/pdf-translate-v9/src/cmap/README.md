# cmap

ToUnicode/CMap decode와 encode 모듈 설계를 설명하는 디렉토리다.

encodedOriginal을 decodedOriginal로 변환하고, translated text를 replacementEncoded로 되돌린다.

## 책임

```text
font resource에서 ToUnicode reference 확인
CMap stream parsing
encoded text -> decoded text 변환
translated text -> replacementEncoded 변환 시도
```

## 실패 원칙

```text
기존 font/CMap으로 번역문 encoding이 불가능하면 실패로 기록한다.
임의 fallback font 삽입은 기본 동작에 포함하지 않는다.
```

## 변환 방향

```text
추출 방향:
encodedOriginal + fontState/ToUnicode/CMap -> decodedOriginal

복원 방향:
decodedTranslated + fontState/ToUnicode/CMap -> replacementEncoded
```

복원 방향에서도 추출 단계에서 저장한 fontState와 CMap 옵션을 그대로 사용한다.
