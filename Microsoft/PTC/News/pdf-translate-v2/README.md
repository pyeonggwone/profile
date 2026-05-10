# pdf-translate-v2

`pdf-translate-v1` 의 Rust PDF 엔진을 그대로 사용하면서, `epub-translate-v5` / `ppt-translate-v4` 와 동일한 운영 패턴 (input/output/work/done + glossary + .env + 단일 진입 스크립트) 으로 PDF 파일을 자동 번역하는 프로젝트.

## 기준

- `pdf-translate-v1` 은 수정하지 않는다.
- 실행 환경은 `epub-translate-v5` 처럼 Linux/bash + Node.js 20+ 를 1차 타겟으로 한다.
- v1 의 Rust workspace 는 자식 프로세스(`pdftr` CLI) 로 호출한다 (PLAN Phase 1 옵션 B).
- LLM 호출은 OpenAI / Azure OpenAI 를 epub-v5 와 동일한 환경 변수로 분기한다.
- 동일 문장은 SQLite 기반 Translation Memory (`work/tm.sqlite`) 로 한 번만 호출한다.
- 용어집(`glossary.csv`) 의 protected 항목은 placeholder 로 보호되어 그대로 유지된다.

## 실행

```bash
chmod +x run-translate.sh
cp .env.example .env
vi .env
./run-translate.sh
```

자세한 설치 단계는 [INSTALL.md](INSTALL.md) 참조.

## 입력과 출력

```text
input/sample.pdf  -> output/sample_KR.pdf
input/done/sample.pdf  (성공 시 원본 자동 이동)
work/sample/segments.json   (EXTRACT 산출)
work/sample/translated.json (TRANSLATE 산출)
work/sample/edits.json      (APPLY 입력 — EditOperation 배열)
work/tm.sqlite              (Translation Memory)
```

## 디렉토리

```text
pdf-translate-v2/
├── run-translate.sh
├── package.json
├── .env.example
├── glossary.csv
├── README.md
├── INSTALL.md
├── TODO.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── PIPELINE.md
│   ├── FILE-runtime-dirs.md
│   ├── FILE-env.md
│   ├── FILE-glossary-csv.md
│   └── FILE-pdf-engine.md
├── src/
│   ├── index.mjs
│   ├── pipeline.mjs
│   ├── pdf/
│   ├── translate/
│   ├── glossary/
│   ├── tm/
│   └── util/
├── crates/                # (옵션 A 채택 시 v1 의 crate path 의존)
├── pdf-engine/            # v1 의 pdftr CLI 빌드 산출물 (옵션 B)
├── input/
│   └── done/
├── output/
└── work/
    └── tm.sqlite
```

## CLI

```bash
./run-translate.sh                                # input/ 일괄 처리
./run-translate.sh --in-lang en --out-lang kr
./run-translate.sh --in-lang en --out-lang jp input/sample.pdf

./run-translate.sh extract input/sample.pdf
./run-translate.sh translate work/sample/segments.json --in-lang en --out-lang kr
./run-translate.sh apply input/sample.pdf work/sample/translated.json --out-lang kr

./run-translate.sh tm import legacy.csv
./run-translate.sh --reset-tm
```

언어 코드 표기는 `ppt-translate-v4` 와 동일: `en`, `kr`, `ch`, `jp` (대소문자 구분 없음).

## PDF 엔진

`pdf-translate-v1` 의 `pdftr` CLI 를 자식 프로세스로 호출한다.

- `pdftr text <input>` : segments JSON 추출
- `pdftr edit <input> <output> --edits <edits.json>` : Incremental Update PDF 생성 (`EditOperation::AddText` 시퀀스)

원본 PDF 의 byte prefix 는 무손실 보존되며, 번역 텍스트는 incremental update 로 추가된다. (자세한 내용: [docs/FILE-pdf-engine.md](docs/FILE-pdf-engine.md))

## 제외 범위

- DRM / 암호 PDF 의 자동 우회 (지원 안 함; password 인자만 전달)
- v1 의 웹 viewer 이식 (2차 단계로 분리)
- AZW3/MOBI/KFX 등 비-PDF 포맷 (epub-translate-v5 영역)
- PowerPoint / 스프레드시트 (각각 ppt-translate-v* / docs-translate-v* 영역)
