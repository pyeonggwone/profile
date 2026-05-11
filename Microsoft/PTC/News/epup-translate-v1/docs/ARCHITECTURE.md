# Architecture

## 핵심 결정

| 항목 | 선택 | 이유 |
|---|---|---|
| 처리 대상 | `.epub` (EPUB 2/3) | 프로젝트 범위 |
| 코어 라이브러리 | **epub.js (futurepress)** | 사용자 명시. spine 순서, OPF 경로, metadata 파싱에 사용 |
| 텍스트 추출/치환 | **JSZip + cheerio (xmlMode)** | epub.js 는 reader 라이브러리라 EPUB 쓰기 미지원. ZIP 직조작 + DOM walk 가 자연스러움 |
| Node DOM 보강 | **jsdom** | epub.js 가 Node 에서 `DOMParser`, `XMLSerializer` 등 글로벌을 요구 |
| LLM | OpenAI SDK | OpenAI / Azure OpenAI 양쪽을 동일 SDK 로 처리 (Azure 는 baseURL + api-key 헤더) |
| TM | SQLite (`better-sqlite3`) | 동일 문장 재번역 방지, 동기 API 라 단순 |
| 배포 | 단일 `epub_translate.mjs` | ppt-translate-v4 와 동일 단일 파일 컨벤션 |

## 파이프라인

```text
input/foo.epub
  │
  ▼ EXTRACT
  │   1. JSZip.loadAsync(buffer)
  │   2. META-INF/encryption.xml 존재 → 스킵 (DRM 가정)
  │   3. epub.js ePub(arrayBuffer) → book.opened
  │   4. book.spine.items 순회 → 각 spine 의 zip 내 XHTML 경로 해석
  │   5. cheerio.load(xml, { xmlMode: true }) 후 DOM walk
  │      → 텍스트 노드 path = root 부터 child index 배열
  │      → skip 태그/패턴 제외
  │   6. work/<stem>/segments.json 생성
  │
  ▼ TRANSLATE
  │   1. TM 조회 (SHA-256(원문) → tgt)
  │   2. 미스 segment 만 batch (BATCH_SIZE=10) LLM 호출
  │   3. system prompt = glossary.csv + 누적된 dict.json
  │   4. response_format=json_object, schema:
  │        {"translations": ["..."], "proper_nouns": [{"src":"...","tgt":"..."}]}
  │   5. proper_nouns 를 dict.json 에 누적 저장
  │   6. 실패 시 batch 절반 분할 재시도, 단일 항목까지 분할되면 원문 유지
  │   7. work/<stem>/translated.json 생성
  │
  ▼ APPLY
  │   1. 원본 EPUB 을 output/ 으로 복사
  │   2. JSZip.loadAsync(copy)
  │   3. translated 를 href 기준으로 group → 각 XHTML cheerio.load → path 따라 텍스트 노드만 data 교체
  │   4. content.opf 의 dc:language 를 target 언어로 갱신
  │   5. mimetype 은 STORE(무압축) 으로 재추가, generateAsync 로 zip 재작성
  │
output/foo_KR.epub
```

## Path 규약

```
[child_idx, child_idx, ..., child_idx_to_text_node]
```

- root = cheerio `$.root()[0]` (Document). 그 children 부터 0-based child index 누적.
- `tag` 노드만 자식으로 카운트하지 않고 cheerio 는 모든 노드(text/comment 포함) 를 children 으로 가지므로 **child_idx 는 모든 children 기준 index**. EXTRACT 와 APPLY 가 동일한 walker 를 사용하므로 일관됨.

## 보존 대상

- inline/block 모든 HTML 서식 (텍스트 노드 data 만 교체하므로 자동 보존)
- 이미지, 표, CSS, 폰트, 메타데이터, OPF spine 순서, NCX/nav
- 원본 파일 자체 (복사본만 수정)

## 보존 안 함 / 비대상

- 이미지 안의 텍스트 (`<img alt>` 포함)
- DRM 보호 EPUB
- 문법적으로 잘못된 XHTML (cheerio 가 파싱 실패 시 해당 spine 만 skip)

## 확장 포인트

- 노트/번역 검증 pass (잔여 영문 detect → 재번역)
- NCX/nav 의 `navLabel` 별도 번역
- 파일별 dict.json 을 사용자가 사전 편집 후 강제 적용하는 모드
- LiteLLM 채택으로 Anthropic/Gemini 등 다른 vendor 추가
