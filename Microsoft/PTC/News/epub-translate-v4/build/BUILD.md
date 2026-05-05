# epub-translate-v4 실행계획

이 디렉터리는 `README.md`의 요구사항을 실제 구현 가능한 작업 단위로 나눈 실행계획 문서 모음이다. 구현은 이 문서들의 단계와 완료 조건을 기준으로 진행한다.

## 전체 원칙

- `epup-translate-v3`는 그대로 두고 참고만 하며, `epub-translate-v4`를 새 프로젝트로 구현한다.
- `epub-translate-v4`는 EPUB 전용 도구가 아니라 네이티브 멀티 포맷 전자책 번역 플랫폼으로 구현한다.
- 지원 포맷은 `epub`, `azw3`, `mobi`, `kfx`를 1차 대상으로 둔다.
- 입력 포맷과 출력 포맷은 동일해야 한다.
- 초기 MVP는 포맷별 번역 성공과 저장 성공을 우선한다.
- 장기 목표는 각 포맷의 구조, 레이아웃, 메타데이터, 리소스 보존이다.
- 번역 엔진은 포맷과 분리하고, 포맷별 native adapter가 공통 segment 모델을 사용한다.

## 실행계획 디렉터리

| 디렉터리 | 역할 |
|---|---|
| `00-requirements` | README 요구사항을 구현 기준으로 재정리 |
| `01-project-foundation` | 런타임, 패키지, 기본 디렉터리, CLI 기준 설계 |
| `02-input-format-detection` | input scan, 확장자/시그니처 기반 포맷 감지 설계 |
| `03-common-document-model` | 포맷별 reader가 반환할 공통 book/segment 모델 설계 |
| `04-translation-engine` | LLM, glossary, masking, TM, usage 수집 설계 |
| `05-epub-adapter` | EPUB native reader/writer/text 처리 계획 |
| `06-azw3-adapter` | AZW3 native reader/writer/text 처리 계획 |
| `07-mobi-adapter` | MOBI native reader/writer/text 처리 계획 |
| `08-kfx-adapter` | KFX native reader/writer/text 처리 계획 |
| `09-metadata-usage` | `ebook-metadata/` JSON, word count, token usage 설계 |
| `10-output-preservation` | 동일 포맷 저장, 원본 리소스 보존, output 정책 설계 |
| `11-drm-error-handling` | DRM 감지, 실패 처리, skip metadata 설계 |
| `12-validation-testing` | 포맷별 출력 검증, 샘플 테스트, 회귀 테스트 설계 |
| `13-delivery-roadmap` | MVP부터 완성도 개선까지 단계별 구현 순서 |

각 디렉터리의 `DESIGN.md`를 기준 문서로 사용한다.
