# pdf_state_db

SQLite 상태 DB crate 설계를 설명하는 디렉토리다.

v9에서는 Rust 구현 시 rusqlite 또는 sqlx sqlite를 후보로 둔다.

## 책임

```text
state.sqlite schema 관리
job status 기록
pipeline step status 기록
artifact index 기록
resume cursor 기록
validation event 기록
```

raw PDF text state의 원본 저장은 JSON 파일이 담당한다.
