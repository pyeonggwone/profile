# translate

OpenAI 번역 연동 모듈 설계를 설명하는 디렉토리다.

id와 text를 보내고 id와 translated text를 받는다.

PDF 내부 상태는 이 모듈에서 수정하지 않는다.

## 책임

```text
readable-text-state.json에서 source 추출
chunk 생성
OpenAI JSON 요청
id 기준 translation-results.json 저장
누락 id report 기록
```

## 원칙

```text
OpenAI에는 PDF operator/font/CMap 정보를 보내지 않는다.
OpenAI는 id와 text만 번역한다.
```
