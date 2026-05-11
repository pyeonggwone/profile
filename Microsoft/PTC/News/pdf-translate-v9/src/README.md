# src

구현 모듈을 설명하는 문서 디렉토리다.

## 주의

```text
실제 Rust 구현은 crates/*/src 아래에 둔다.
이 src 디렉토리는 모듈별 설계 README를 유지한다.
```

## 구현 모듈

```text
pipeline/          단계 실행 순서
qpdf/              qpdf 호출과 검증
pdf_reader/        lopdf 기반 PDF object 접근
content_parser/    content stream operator parser
text_state/        text state 추적
cmap/              ToUnicode/CMap decode/encode
readable/          raw JSON -> readable JSON 변환
state_store/       SQLite job 상태와 TM index 저장
terms/             job별 고유명사/용어집 처리
translate/         OpenAI 번역
rebuild/           text payload replacement
models/            JSON schema
report/            report/progress 기록
publish/           검증 완료 PDF publish
```

## 모듈 관계

```text
qpdf/
	qpdf reference와 검증

pdf_reader/ + content_parser/ + text_state/ + cmap/
	원본 PDF에서 raw-pdf-text-state.json 생성

readable/
	raw JSON을 readable-text-state.json으로 변환

state_store/
	job 상태, step 상태, TM hit/miss, artifact index를 SQLite에 기록

terms/
	job별 고유명사 후보와 확정 용어집을 translation-input.json에 반영

translate/
	OpenAI 번역 JSON 생성

cmap/ + rebuild/
	번역 결과를 replacementEncoded로 변환하고 원본 stream에 교체

report/
	모든 실패/검증 결과 기록
```
