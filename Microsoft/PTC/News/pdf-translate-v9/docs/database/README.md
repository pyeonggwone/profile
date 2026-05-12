# database

SQLite 기반 상태 저장 설계를 설명하는 디렉토리다.

v9의 기준 데이터는 JSON 파일이다. SQLite는 JSON을 대체하지 않고, job 상태 조회와 Translation Memory 조회를 빠르게 하기 위한 보조 저장소로 사용한다.

## 기존 프로젝트 참고

```text
pdf-translate-v2: work/tm.sqlite, better-sqlite3, src/tm/store.mjs
docs-translate-v2: work/tm.sqlite, sqlite3, Translation Memory
```

## v9 저장 대상

```text
job 상태
pipeline step 진행 상태
translation memory
term memory
실패/검증 index
```

PDF 복원 기준인 raw-pdf-text-state.json과 pdf-input-text-state.json은 SQLite에만 저장하지 않는다. 복원 가능한 원본 상태는 파일 JSON으로 남긴다.
