# state_store

SQLite 상태 저장 모듈 설계를 설명하는 디렉토리다.

역할은 pipeline 진행 상태, artifact path, validation event, resume cursor를 SQLite에 기록하는 것이다.

PDF text state 자체의 기준 저장소는 raw JSON이다. SQLite에는 검색과 상태 조회에 필요한 index만 저장한다.
