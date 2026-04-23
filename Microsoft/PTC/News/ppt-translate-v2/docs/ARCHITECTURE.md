# Architecture

## 핵심 결정

| 항목 | 선택 | 이유 |
|------|------|------|
| PPTX 처리 | `lxml` + `zipfile` 직접 | python-pptx/COM 의존 없음, 100% 크로스플랫폼 |
| 변환 방식 | **In-place 텍스트 치환** | SmartArt/차트/애니메이션/마스터 보존 |
| LLM 호출 | LiteLLM 통합 | OpenAI/Azure/Anthropic 동일 인터페이스 |
| TM | SQLite | 동일 문장 재번역 방지, 비용·일관성 ↑ |
| 배포 | Linux Docker 단일 이미지 | WSL/CI/Container Apps 모두 지원 |

## 파이프라인

```
input.pptx
  │
  ▼  EXTRACT (extract/shapes.py)
work/{stem}/segments.json     # [{slide, index, text}]
  │
  ▼  TRANSLATE (translate/llm.py + memory.py)
work/{stem}/translated.json   # [{slide, index, text, translated}]
  │
  ▼  APPLY (apply/inplace.py)
input_KO.pptx
```

## OOXML 구조 (요약)

```
input.pptx (ZIP)
├── ppt/
│   ├── slides/slide1.xml      ← <a:t> 텍스트 노드 추출 대상
│   ├── slides/slide2.xml
│   ├── slideLayouts/...
│   ├── theme/...
│   └── media/image1.png       ← 손대지 않음
└── [Content_Types].xml
```

`<a:t>` (DrawingML text run) 의 `.text` 만 교체하면 서식/위치/이미지/SmartArt 모두 보존.

## 확장 포인트

- **노트 슬라이드 번역**: `ppt/notesSlides/notesSlide{N}.xml` 도 동일 방식으로 처리 (extract 에 추가)
- **차트 텍스트**: `ppt/charts/chart{N}.xml` 의 `<c:tx>` 노드 처리
- **diagrams (SmartArt)**: `ppt/diagrams/data{N}.xml` 의 `<a:t>` 처리
- **번역 품질 검증**: APPLY 전 길이/금칙어/용어집 후처리 검증 단계 추가
