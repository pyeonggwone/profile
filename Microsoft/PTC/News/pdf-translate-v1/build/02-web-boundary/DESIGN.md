# Web Boundary 설계

## 목적

사용자 PDF 업로드와 편집 결과 PDF 다운로드를 연결하는 HTTP/API 경계를 설계한다. 이 영역은 PDF를 해석하지 않고 서버의 core engine을 호출하는 orchestration layer다.

## 기준 기술

| 영역 | 기술 | 기준 버전 |
|---|---|---:|
| HTTP server | Rust `axum` | `0.7.x` |
| Async I/O | `tokio` | `1.37+` |
| Multipart upload | `multer` 또는 `axum-extra` multipart | 구현 시 확정 |
| JSON serialization | `serde_json` | `1.0.x` |
| Temporary file | OS filesystem API | Windows 기준 |
| Web frontend | React `18.3.x` + TypeScript `5.4+` + Vite `5.2+` | 설계 기준 |

## API 구조

초기 API는 다음 형태로 둔다.

| Method | Path | 역할 |
|---|---|---|
| `POST` | `/api/documents` | PDF 업로드, session 생성 |
| `GET` | `/api/documents/{documentId}` | 문서 metadata 조회 |
| `GET` | `/api/documents/{documentId}/pages/{pageNumber}` | 페이지 표시용 render plan 조회 |
| `GET` | `/api/documents/{documentId}/assets/{assetId}` | 이미지/폰트 preview asset 조회 |
| `POST` | `/api/documents/{documentId}/edits` | 웹 편집 operation 추가 |
| `GET` | `/api/documents/{documentId}/download` | Incremental Update 적용 PDF 다운로드 |
| `DELETE` | `/api/documents/{documentId}` | session 및 임시 파일 정리 |

## 업로드 흐름

```text
1. Browser가 PDF를 multipart로 전송
2. Server가 임시 저장소에 원본 bytes 저장
3. pdf_reader가 header/xref/trailer/object index를 생성
4. document model이 원본 byte range와 object map을 만든다
5. Server가 documentId와 기본 metadata를 반환
6. Browser가 page render plan을 요청한다
```

## 다운로드 흐름

```text
1. Browser가 edit operation을 서버에 저장
2. Server가 document model에 변경분을 적용
3. pdf_incremental이 새 객체와 새 xref/trailer를 생성
4. 원본 PDF bytes 뒤에 변경분을 append
5. Server가 `application/pdf`로 다운로드 응답
```

## 편집 Operation 모델

웹 UI는 PDF 객체를 직접 조작하지 않는다. 대신 의미 기반 operation을 서버로 보낸다.

예시 operation은 다음과 같다.

```json
{
  "type": "addText",
  "page": 1,
  "position": { "x": 120.0, "y": 240.0 },
  "text": "Sample",
  "font": { "family": "Base14-Helvetica", "size": 12.0 },
  "color": "#111111"
}
```

서버는 operation을 PDF content stream 변경으로 변환한다. 이 변환은 `pdf_writer`와 `pdf_incremental` 영역에서 수행한다.

## 파일 저장 설계

초기 구현은 로컬 파일 시스템 기반 session store를 사용한다.

```text
workdir/
  sessions/
    {documentId}/
      original.pdf
      document.json
      edits.jsonl
      cache/
        page-1.render.json
        image-{id}.bin
```

SQLite를 사용할 경우 다음 metadata만 저장한다.

- `documentId`
- 원본 파일 경로
- 업로드 시각
- PDF version
- page count
- encrypted 여부
- parse status

PDF 원본 bytes는 DB에 넣지 않고 파일로 보관한다.

## 보안 및 제한

- 업로드 파일 크기 제한을 둔다. 초기 기준은 `100 MB`다.
- content type만 믿지 않고 PDF header `%PDF-`를 확인한다.
- 임시 파일 경로는 documentId 기반으로 격리한다.
- 다운로드 filename은 사용자 입력을 그대로 사용하지 않는다.
- JavaScript action, embedded file, launch action은 분석만 하고 실행하지 않는다.
- 암호화 PDF는 초기 구현에서 owner/user password 입력 흐름이 없으면 명시적 오류로 처리한다.

## 오류 응답

오류는 사용자가 이해할 수 있는 code와 내부 진단용 detail을 분리한다.

```json
{
  "code": "PDF_XREF_NOT_FOUND",
  "message": "PDF cross-reference 정보를 찾을 수 없습니다.",
  "recoverable": false
}
```

내부 stack trace나 파일 경로는 응답에 포함하지 않는다.

## 완료 기준

- 업로드와 다운로드 API가 분리되어 있다.
- PDF parsing, writing은 web boundary에서 직접 처리하지 않는다.
- 편집은 의미 기반 operation으로 전달된다.
- 원본 PDF와 변경 이력은 session 단위로 추적된다.