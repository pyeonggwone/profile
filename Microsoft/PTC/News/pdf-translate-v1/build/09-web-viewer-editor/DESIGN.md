# Web Viewer and Editor 설계

## 목적

업로드된 PDF를 브라우저에서 표시하고, 사용자가 텍스트/이미지/주석을 추가한 뒤 PDF로 다운로드할 수 있는 웹 UI를 설계한다. PDF 해석은 서버가 담당하고, 브라우저는 Canvas 렌더링과 편집 interaction을 담당한다.

## 기준 기술

| 영역 | 기술 | 기준 버전 |
|---|---|---:|
| UI framework | React | `18.3.x` |
| Language | TypeScript | `5.4+` |
| Build | Vite | `5.2+` |
| Rendering | Browser Canvas 2D API | Microsoft Edge/Chromium stable 기준 |
| State | React state + reducer | 외부 상태 라이브러리 없이 시작 |
| Icons | lucide-react | `0.468+` 기준 |

## 화면 구조

초기 화면은 도구형 앱으로 구성한다.

```text
Top toolbar
  upload, save/download, zoom, page navigation

Left panel
  page thumbnails, document outline optional

Center canvas
  PDF page rendering, selection overlay

Right panel
  selected object properties, annotations, metadata
```

랜딩 페이지는 만들지 않는다. 첫 화면은 바로 PDF 업로드와 작업 영역이다.

## 렌더링 흐름

```text
1. Browser가 page render plan 요청
2. Canvas viewport 계산
3. render plan command를 Canvas 2D API로 그림
4. 편집 overlay를 별도 layer에 그림
5. 사용자 interaction을 edit operation으로 변환
6. 저장 시 서버 API로 edit operation 전송
```

Canvas layer는 두 개로 분리한다.

- base layer: 서버 render plan 기반 PDF 표시
- overlay layer: 선택 영역, 편집 중인 텍스트 박스, guide line

## Zoom과 viewport

줌은 PDF 좌표를 바꾸지 않고 viewport transform만 바꾼다.

지원 기능은 다음과 같다.

- 50%, 75%, 100%, 125%, 150%, 200%
- fit width
- fit page
- wheel zoom optional
- page rotation 반영

PDF 좌표와 Canvas 좌표 변환은 `05-document-model`의 기준을 따른다.

## 편집 도구

초기 편집 도구는 다음으로 제한한다.

| 도구 | 생성 operation |
|---|---|
| Text | `AddText` |
| Image | `AddImage` |
| Note | `AddAnnotation` |
| Highlight | `AddHighlight` |
| Select | overlay object 선택/이동 |

텍스트 편집 속성은 다음을 제공한다.

- font family: 초기에는 Base14 font만
- font size
- color
- position
- alignment optional

이미지 편집 속성은 다음을 제공한다.

- x, y
- width, height
- maintain aspect ratio
- opacity optional

## 서버와의 데이터 계약

웹은 PDF bytes를 직접 수정하지 않는다. 모든 변경은 operation으로 서버에 전달한다.

```text
Canvas interaction
-> EditOperation
-> POST /api/documents/{documentId}/edits
-> server stores edit
-> render plan refresh
```

저장 전 미리보기는 overlay layer에서 즉시 보여준다. 서버 반영 후에는 render plan을 다시 받아 base layer와 일치시킨다.

## Asset 표시

이미지는 서버가 asset endpoint로 제공한다.

- JPEG preview는 가능한 경우 원본 bytes를 사용한다.
- Flate image는 서버가 PNG preview로 변환해서 제공할 수 있다.
- preview 실패 시 placeholder를 표시한다.

브라우저가 PDF image filter를 직접 decode하지 않는다.

## 접근성과 사용성

- 주요 toolbar button에는 tooltip을 둔다.
- 페이지 이동은 keyboard input과 button을 모두 지원한다.
- 업로드 실패, parse warning, 저장 실패는 화면 상단 status area에 표시한다.
- 긴 파일명은 UI를 밀어내지 않도록 줄임 처리한다.

## 금지 사항

- `pdf.js`로 렌더링하지 않는다.
- 브라우저에서 PDF parser를 별도로 구현하지 않는다.
- 외부 PDF SaaS preview를 iframe으로 넣지 않는다.
- 편집 결과를 Canvas screenshot PDF로 저장하지 않는다.

## 완료 기준

- 업로드 후 page render plan을 Canvas에 표시한다.
- 텍스트/이미지/주석 추가 operation을 만들 수 있다.
- 다운로드 버튼이 서버의 PDF writer 흐름과 연결된다.
- PDF 원본 구조 변경은 서버에서만 수행된다.