# Architecture

## 핵심 결정

| 항목 | 선택 | 이유 |
|---|---|---|
| 처리 대상 | `.docx`, `.doc` | 사용자 요청 범위: Word docs 파일 |
| 처리 엔진 | Microsoft Word COM Automation (`pywin32`) | `ppt-translate-v4`와 동일하게 Office 엔진을 직접 사용 |
| 변환 방식 | 원본 복사 후 Range.Text in-place 치환 | 문서 구조와 레이아웃 보존 |
| LLM | LiteLLM | OpenAI/Azure OpenAI 통합 |
| TM | SQLite | 동일 문장 재번역 방지 |
| 실행 | 단일 `docs_translate.py` + uv | 배포 단순화 |

## 파이프라인

```text
input/foo.docx
  │
  ▼ EXTRACT  (Word.Application + Document.StoryRanges/Paragraphs 순회)
work/<key>/segments.json
  │
  ▼ TRANSLATE (TM 조회 → LiteLLM 번호 블록 배치 호출)
work/<key>/translated.json
  │
  ▼ APPLY    (원본 복사 → 동일 Story/Paragraph Range.Text 치환)
output/foo_KR.docx
```

## Path 규약

```json
["story", story_type, story_index, "p", paragraph_index]
```

- `story_type`: Word StoryType 값
- `story_index`: linked StoryRange 순회 중 같은 story type 내 식별 보조값
- `paragraph_index`: 해당 story 안의 paragraph index (1-based)

## 보존 대상

- 표, 이미지, 머리글/바닥글, 섹션, 페이지 설정, 스타일
- URL/email/변수/protected term placeholder
- 원본 파일은 직접 수정하지 않음

## 제한

- paragraph 단위 치환이라 문단 내부의 세부 run formatting 은 단순화될 수 있음
- TOC/field code/cross-reference 문단은 손상 방지를 위해 skip 가능
