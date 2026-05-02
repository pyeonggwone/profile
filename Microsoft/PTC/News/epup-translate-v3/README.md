# epup-translate-v3

EPUB 포맷 보존 번역기. 원본의 ZIP 구조·XHTML 마크업·이미지/폰트/CSS를 그대로 두고 **텍스트 노드만** LLM 으로 번역합니다.

## 스택 (각 기능별 공식 권장 라이브러리)

| 기능 | 라이브러리 |
|---|---|
| EPUB(.zip) 입출력 | `jszip` (mimetype STORED 보장) |
| OPF/container.xml 파싱 | `fast-xml-parser` |
| XHTML 파싱·직렬화 | `parse5` + `parse5-htmlparser2-tree-adapter` |
| LLM 호출 (OpenAI/Azure OpenAI) | 공식 `openai` SDK |
| 환경변수 | `dotenv` |
| 번역 메모리(TM) | `better-sqlite3` |
| 용어집 CSV | `csv-parse` |
| CLI | `commander` |

## 요구사항

- AlmaLinux 9.7 (또는 호환 Linux), Node.js 20+
- OpenAI 또는 Azure OpenAI API 자격증명

## 설치 & 실행

```bash
chmod +x run-translate.sh
cp .env.example .env       # 키/모델 입력
# input/ 에 .epub 파일을 넣고
./run-translate.sh
```

처음 실행 시 `npm install` 자동 수행, 이후 `input/*.epub` 을 모두 번역하여
`output/{stem}_KR.epub` 으로 출력합니다. 처리 완료된 원본은 `input/done/` 으로 이동합니다.

## 동작 보장

- **포맷 보존**: ZIP 엔트리 순서·이미지·폰트·CSS·OPF/NCX 거의 무손실 복사
- **`mimetype` 첫 엔트리, 무압축(STORED)** — EPUB 스펙 준수
- **이미지 미번역**, `<script>/<style>/<code>/<pre>/<svg>/<math>` 등 스킵
- **DRM 감지**: `META-INF/encryption.xml` 있으면 해당 파일 스킵
- **언어 메타 갱신**: OPF `<dc:language>` 와 각 XHTML `<html lang xml:lang>` → `ko`
- **용어 보호**: `glossary.csv` 의 `protected=true` 항목은 placeholder 로 마스킹 후 복원
- **번역 메모리**: SQLite (`work/tm.sqlite`) 로 중복 호출 차단
- **placeholder 검증 실패** 또는 LLM 오류 시 해당 세그먼트는 원문 유지

## 디렉터리

```
epup-translate-v3/
├── run-translate.sh
├── package.json
├── .env / .env.example
├── glossary.csv
├── src/
│   ├── index.mjs           # CLI
│   ├── pipeline.mjs        # 오케스트레이터
│   ├── util/
│   │   ├── env.mjs
│   │   └── log.mjs
│   ├── translate/
│   │   ├── llm.mjs         # openai SDK
│   │   ├── masker.mjs
│   │   ├── glossary.mjs
│   │   └── tm.mjs
│   └── epub/
│       ├── reader.mjs      # jszip + fast-xml-parser
│       ├── xhtml.mjs       # parse5
│       └── writer.mjs      # jszip pack
├── input/   (원본 EPUB)
├── output/  ({stem}_KR.epub)
└── work/    (tm.sqlite 등)
```
