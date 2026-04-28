# Architecture

## 핵심 결정

| 항목 | 선택 | 이유 |
|---|---|---|
| 처리 대상 | Markdown `.md` | MVP 범위를 명확히 제한 |
| 추출 방식 | line/path 기반 segment | 원문 line 구조를 보존하면서 APPLY 단순화 |
| 보호 방식 | placeholder masking | 코드, URL, 변수, HTML tag 손상 방지 |
| LLM | LiteLLM | OpenAI/Azure OpenAI 통합 |
| TM | SQLite | 동일 segment 재번역 방지 |
| 실행 | 단일 `docs_translate.py` + uv | 배포 단순화 |

## 파이프라인

```text
input/foo.md
  │
  ▼ EXTRACT
work/<key>/segments.json
  │
  ▼ TRANSLATE
work/<key>/translated.json
  │
  ▼ APPLY
output/foo_KR.md
```

## Segment path

| 요소 | path 예 |
|---|---|
| Heading | `["line", 10, "heading"]` |
| Paragraph | `["line", 12, "paragraph"]` |
| List item | `["line", 15, "list_item"]` |
| Blockquote | `["line", 18, "blockquote"]` |
| Table cell | `["line", 22, "table_cell", 2]` |

## 보호 토큰

`__DOCSTR_<KIND>_<NNNN>__` 형식을 사용합니다. TRANSLATE 단계에서 source/target placeholder 집합이 다르면 해당 segment 는 원문 fallback 됩니다.

## MVP 제한

- Markdown AST 재직렬화가 아닌 line/path 기반 치환
- frontmatter 는 전체 제외
- reference link definition 은 제외
- 복잡한 MDX/HTML nested content 는 향후 확장 대상
