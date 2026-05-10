# TODO — pdf-translate-v3

## 통합 완료 (v1 + v2 → v3)

- [x] v1 의 8 crate (server 제외) 를 `crates/` 로 복사
- [x] v1 의 workspace `Cargo.toml` 을 v3 루트로 복사 후 server 멤버 제거
- [x] v2 의 `src/`, `docs/`, `package.json`, 진입 스크립트, 설정 파일을 v3 로 복사
- [x] `src/pdf/engine.mjs` 의 v1 외부 경로 참조 제거 (자체 `target/release/pdftr` 만 탐색)
- [x] `run-translate.sh` 가 첫 실행 시 `cargo build --release -p pdftr_cli` 자동 수행
- [x] README / INSTALL / TODO / docs 의 v1 참조 제거 또는 갱신

## Smoke test

- [ ] 작은 PDF 1 개 input/ 에 두고 전체 파이프라인 실행
- [ ] 결과 PDF 가 standard viewer 에서 열리는지 확인
- [ ] `input/done/` 이동 확인
- [ ] `work/tm.sqlite` 에 entry 가 들어가는지 확인

## 미해결 / 향후

- [ ] **한글 출력**: v1 의 `EditOperation::AddText` 가 Base14 폰트만 받아 한글이 깨짐. v1 의 `pdf_writer/font.rs` 의 TrueType subset 임베딩이 CLI 표면(`pdftr edit`) 에 노출되어야 함. 해결 방향:
    - `EditOperation` 에 `AddTextEmbedded { font_path, ... }` variant 추가
    - 또는 `--font <ttf>` CLI 옵션으로 모든 `AddText` 의 폰트를 임베디드 폰트로 교체
- [ ] JPX / JBIG2 디코드를 위한 v1 feature flag 활성화 가이드
- [ ] LLM 응답 placeholder 누락/순서 변경 시 segment 단위 재시도 (현재 batch 단위 fallback)
- [ ] 큰 PDF 의 page 단위 chunk 처리 (메모리 / 토큰 분할)
- [ ] watcher 모드 (`--watch`): 안정화 대기 후 자동 처리
- [ ] 세션 단위 비용 리포트 (input/output/total token) JSON 출력
- [ ] EXTRACT 결과의 동일 라인 좌표 클러스터링 (현재 run 단위, 의미 단위 합치기 필요)
- [ ] 원문 보존 모드 (`PDF_KEEP_ORIGINAL_LANG=true`) 의 layout 정책 (현재 동일 좌표 덧씌움)

## v1 의 historical issue (v3 에 그대로 적용된 fix)

- [x] `crates/pdf_reader/src/document.rs::resolve()` lifetime annotation 추가 (rustc 1.84+ 의 더 엄격한 lifetime 검사)
