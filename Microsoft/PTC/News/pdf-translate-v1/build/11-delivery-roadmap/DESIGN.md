# Delivery Roadmap 설계

## 목적

실제 구현을 진행할 때의 단계, 산출물, 완료 기준을 정의한다. 구현은 하지 않고 계획만 작성한다.

## Phase 0. 설계 고정

### 목표

요구사항, 금지 의존성, 기술 스택, 디렉토리 구조를 확정한다.

### 산출물

- `build/BUILD.md`
- 각 설계 디렉토리의 `DESIGN.md`
- 직접 구현/대체 구현 결정표
- 기준 버전 목록

### 완료 기준

- PDF 고유 로직을 대체하는 외부 엔진이 설계에 포함되지 않는다.
- 업로드와 다운로드 양방향 흐름이 모두 정의된다.

## Phase 1. 양방향 뼈대

### 목표

PDF 내용을 아직 완전히 해석하지 않더라도 업로드, session 생성, 원본 다운로드 흐름을 만든다.

### 구현 대상

- Rust workspace 생성
- `server` crate 생성
- `POST /api/documents`
- `GET /api/documents/{documentId}/download`
- session file store
- frontend upload/download 화면

### 완료 기준

- 업로드한 PDF를 원본 그대로 다시 다운로드할 수 있다.
- 파일 크기, PDF header, session metadata를 검증한다.

## Phase 2. PDF Reader MVP

### 목표

xref table 기반 PDF를 읽어 page count와 object map을 만든다.

### 구현 대상

- header parser
- startxref parser
- xref table parser
- trailer parser
- indirect object parser
- page tree traversal

### 완료 기준

- 단순 PDF 1.4 fixture의 page count를 읽는다.
- object byte range를 보존한다.

## Phase 3. Stream Filter MVP

### 목표

텍스트 content stream과 기본 이미지 stream을 처리한다.

### 구현 대상

- FlateDecode + zlib `1.3.1`
- ASCIIHexDecode 직접 구현
- ASCII85Decode 직접 구현
- RunLengthDecode 직접 구현
- filter chain 모델

### 완료 기준

- Flate content stream을 decode한다.
- 모르는 filter는 raw-preserved 상태로 유지한다.

## Phase 4. Text Analysis MVP

### 목표

페이지별 텍스트와 위치를 추출한다.

### 구현 대상

- content stream operator tokenizer
- text state model
- simple font encoding
- ToUnicode CMap parser 초기 버전
- render plan text command 생성

### 완료 기준

- 단순 PDF의 텍스트를 Unicode 문자열로 추출한다.
- Canvas에 텍스트 render plan을 표시한다.

## Phase 5. PDF Writer MVP

### 목표

새 object, 새 content stream, xref table, trailer를 작성한다.

### 구현 대상

- primitive serializer
- indirect object writer
- stream writer
- FlateEncode
- xref table writer
- trailer writer

### 완료 기준

- 새 PDF 파일 하나를 생성해 자체 reader로 다시 읽을 수 있다.
- object offset과 startxref 검증을 통과한다.

## Phase 6. Incremental Update MVP

### 목표

원본 PDF에 텍스트 추가를 append-only 방식으로 저장한다.

### 구현 대상

- dirty set
- 새 object number allocator
- page dictionary 새 revision 작성
- 새 content stream 추가
- `/Prev` trailer chain 작성

### 완료 기준

- 원본 prefix가 byte-for-byte 동일하다.
- 저장 결과가 자체 reader로 다시 열린다.
- 표준 PDF viewer에서 열린다.

## Phase 7. Web Editor MVP

### 목표

브라우저에서 텍스트를 추가하고 PDF로 다운로드한다.

### 구현 대상

- React/TypeScript/Vite app
- Canvas base layer
- overlay editing layer
- text tool
- edit operation API
- download button

### 완료 기준

- 업로드 후 페이지가 표시된다.
- 텍스트 추가 후 다운로드 PDF에 반영된다.

## Phase 8. 이미지와 주석 확장

### 목표

이미지 추가와 annotation 추가를 지원한다.

### 구현 대상

- image XObject writer
- libjpeg-turbo adapter
- soft mask 기본 처리
- annotation object writer
- `/Annots` 배열 incremental update

### 완료 기준

- JPEG 이미지를 페이지에 추가할 수 있다.
- Text annotation을 추가할 수 있다.

## Phase 9. 고급 호환성

### 목표

PDF 1.5+ 구조와 다양한 실제 PDF를 처리한다.

### 구현 대상

- xref stream reader
- object stream reader
- LZWDecode
- CCITTFaxDecode
- JPXDecode adapter
- encrypted PDF read flow

### 완료 기준

- object stream이 있는 PDF의 page tree를 읽는다.
- xref stream 기반 PDF를 읽는다.
- 미지원 기능은 문서화된 expected failure로 처리한다.

## Phase 10. 안정화

### 목표

테스트, 오류 메시지, 성능, 보안 경계를 정리한다.

### 구현 대상

- fixture suite
- Playwright canvas nonblank test
- malformed PDF fuzz-like test
- upload size limit
- cleanup job
- crash-safe temp file handling

### 완료 기준

- 주요 fixture가 CI에서 통과한다.
- 실패 케이스가 명확한 오류 code를 반환한다.
- 임시 파일이 session 종료 후 정리된다.

## 구현 우선순위 요약

1. 업로드/다운로드 뼈대
2. xref table reader
3. object parser
4. FlateDecode
5. text extraction
6. writer
7. incremental update
8. Canvas viewer/editor
9. 이미지/주석
10. xref stream/object stream/암호화 등 고급 호환성