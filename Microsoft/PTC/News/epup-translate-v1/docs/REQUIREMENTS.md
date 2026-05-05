# 요구사항 인덱스

epub-translate-v1 의 파일별 요구사항 명세.

## 프로젝트 목표 (Why)

`ppt-translate-v4` / `docs-translate-v2` 와 동일한 운영 컨벤션으로 EPUB 파일을 번역한다.
**epub.js (futurepress)** 를 코어 라이브러리로 사용하여 spine/메타데이터를 파싱하고,
**JSZip + cheerio** 로 XHTML 의 텍스트 노드만 in-place 치환해 inline/block 서식을 100% 보존한다.

## 비기능 요구사항

- **OS**: Windows 10/11 권장 (PowerShell 7+ 진입), Node 자체는 크로스 플랫폼.
- **런타임**: Node.js 20+.
- **LLM**: `.env` 기반. OpenAI 또는 Azure OpenAI 둘 다 지원 (`AZURE_OPENAI_DEPLOYMENT` 가 설정되면 Azure 우선).
- **재현성**: `temperature=0`, TM 캐시 우선.
- **격리**: 작업 산출물은 모두 `work/<stem>/` 하위. 입력은 변경하지 않고 `input/done/` 으로 이동.
- **에러 정책**: per-file 단위 격리. 한 파일 실패가 배치 전체를 중단시키지 않음.
- **DRM**: `META-INF/encryption.xml` 감지 또는 epub.js 파싱 실패 시 해당 파일 skip + 로그.
- **응답 언어**: 사용자 출력 한국어, 코드/JSON 키 영어.
- **TM 독립**: `work/tm.sqlite` 자체 보유 (다른 프로젝트와 공유 안 함).

## 파일별 요구사항

| 파일/디렉토리 | 역할 |
|---|---|
| `epub_translate.mjs` | EXTRACT / TRANSLATE / APPLY / CLI 단일 파일 |
| `Run-Translate.ps1` | PowerShell thin wrapper. node 미존재 시 에러, node_modules 없으면 `npm install` 자동 |
| `package.json` | 의존성 (epubjs, jszip, cheerio, jsdom, openai, better-sqlite3, dotenv, commander, picocolors) |
| `.env`, `.env.example` | LLM 키 + 번역 설정 |
| `glossary.csv` | 글로벌 용어집 (`term, translation, protected`) |
| `input/`, `input/done/`, `output/`, `work/` | 런타임 디렉토리 |

## 번역 단위

- inline 텍스트 노드 1개 = 번역 입력 1건.
- 같은 `<p>` 안에 `<em>foo</em> bar` 가 있으면 `"foo"` 와 `" bar"` 두 건으로 분리 → 서식 100% 보존.
- skip 태그: `script`, `style`, `code`, `pre`, `kbd`, `samp`, `tt`.
- skip 패턴: 공백/숫자/기호만, URL, email.

## 파일별 dict.json

- 형식: `{ "<원문 고유명사>": "<번역>", ... }`
- LLM 응답 schema: `{"translations": [...], "proper_nouns": [{"src": "...", "tgt": "..."}]}`
- 매 batch 후 dict.json 누적 → 다음 batch 의 system prompt 에 "File dictionary" 섹션으로 주입
- 우선순위: glossary.csv > dict.json (LLM 프롬프트에서 glossary 가 위에 위치)

## CLI

```
run <file|dir> [--output PATH] [--no-move-done]
extract <epub>
translate <segments.json>
apply <epub> <translated.json> [--output PATH]
tm import <csv>
```

전역 옵션: `--in-lang en|kr|jp|ch`, `--out-lang en|kr|jp|ch`

첫 인자가 `.epub` 파일/디렉토리이면 자동으로 `run` 으로 라우팅.

## 빌드 우선순위

1. `.env` / `.env.example` / `package.json`
2. EXTRACT (epub.js opened + JSZip 로 XHTML 읽기 + cheerio DOM walker → segments.json)
3. TRANSLATE (TM + LLM batch + dict.json 누적)
4. APPLY (JSZip 복사 + cheerio path 기반 치환 + mimetype STORE 보장)
5. CLI (commander) + 배치 모드 + done/ 이동
