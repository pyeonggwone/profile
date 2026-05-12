# epub-translate-v2

epub.js 코어 + JSZip + cheerio 기반 EPUB 다국어 번역 도구. **Linux (AlmaLinux 9) 전용.**
원본 EPUB 을 복사한 뒤 XHTML 의 텍스트 노드만 in-place 치환하여 포맷을 100% 보존한다.

## 핵심 원칙

- **epub.js (futurepress)** 로 spine/메타데이터 파싱
- **JSZip + cheerio** 로 XHTML 텍스트 노드 in-place 치환 (포맷 보존)
- **inline 텍스트 노드 1개 = 번역 단위 1건**
- **Translation Memory (SQLite)** — 동일 문장 재번역 안 함
- **파일별 사전(dict.json)** — 번역 진행 중 발견한 고유명사 매핑을 누적
- **DRM/암호화 EPUB 자동 스킵**

## 환경 요구사항

| 항목 | 버전 |
|------|------|
| OS | AlmaLinux 9.x (RHEL 9 계열 호환) |
| Node.js | 20+ (`dnf module install nodejs:20`) |
| 빌드 도구 | gcc-c++, make, python3 (better-sqlite3 네이티브 빌드용) |
| LLM | OpenAI 또는 Azure OpenAI (`.env` 설정) |

설치 절차는 [INSTALL.md](INSTALL.md) 참조.

## 빠른 시작

```bash
cp .env.example .env
vi .env
npm install
./run-translate.sh input/sample.epub
```

## 명령

```bash
# 전체 파이프라인 (파일 또는 디렉토리)
./run-translate.sh input.epub
./run-translate.sh input
./run-translate.sh input.epub --no-move-done

# 단계별
./run-translate.sh extract input.epub
./run-translate.sh translate work/input/segments.json
./run-translate.sh apply input.epub work/input/translated.json

# TM 가져오기
./run-translate.sh tm import legacy.csv
```

`--in-lang` / `--out-lang` 으로 언어 지정 (기본: en → kr).

## 파이프라인

```
EXTRACT  : epub.js 로 spine 순회 → JSZip 으로 XHTML 읽기 → cheerio DOM walk 로 텍스트 노드 수집
TRANSLATE: TM 조회 → 미스만 LLM batch 호출 → translations + proper_nouns 동시 수신
           발견된 proper noun 은 파일별 dict.json 에 누적, 다음 batch 프롬프트에 주입
APPLY    : 원본 EPUB 복사 → 동일 path 의 텍스트 노드 in-place 치환
           content.opf 의 dc:language 갱신, mimetype STORE 압축 보장
```

## 디렉토리

```
epup-translate-v2/
├── epub_translate.mjs       # 단일 파일 진입점
├── run-translate.sh         # bash 래퍼
├── package.json
├── glossary.csv             # 글로벌 용어집
├── .env.example
├── README.md
├── INSTALL.md
├── docs/
│   ├── REQUIREMENTS.md
│   └── ARCHITECTURE.md
├── input/
│   └── done/                # 성공 시 원본 이동
├── output/
└── work/
    ├── tm.sqlite
    └── <stem>/
        ├── segments.json
        ├── translated.json
        └── dict.json
```

## 출력 파일명

`<stem>_KR.epub` (target_lang 라벨에 따라 `_EN/_JP/_CH`).

## v1 과의 차이

- **v1**: Windows / PowerShell (`Run-Translate.ps1`)
- **v2**: Linux / bash (`run-translate.sh`), AlmaLinux 9 기준 INSTALL 가이드 포함

## 비대상

- DRM 보호 EPUB (자동 스킵)
- 이미지 안의 텍스트 (`alt` 등은 추출 대상 아님)
- 원본 in-place 변경
