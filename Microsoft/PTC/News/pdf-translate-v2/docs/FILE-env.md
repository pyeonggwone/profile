# `.env` / `.env.example` — pdf-translate-v2

`dotenv` 가 자동 로드하는 환경 설정. `.env` 는 **gitignore 필수**, `.env.example` 은 키를 비운 템플릿으로 커밋.

## 키 정의

### LLM 백엔드 (둘 중 하나 필수)

| 키 | 기본값 | 설명 |
|---|---|---|
| `OPENAI_API_KEY` | "" | OpenAI 또는 호환 백엔드 키 |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI 모델명 |
| `AZURE_OPENAI_API_KEY` | "" | Azure OpenAI 키 |
| `AZURE_OPENAI_ENDPOINT` | "" | `https://<resource>.openai.azure.com/` |
| `AZURE_OPENAI_API_VERSION` | `2024-08-01-preview` | API 버전 |
| `AZURE_OPENAI_DEPLOYMENT` | "" | 배포명 (값 있으면 Azure 우선) |

선택 규칙: `AZURE_OPENAI_API_KEY` 가 있으면 Azure 우선, 아니면 OpenAI.

### 번역

| 키 | 기본값 | 설명 |
|---|---|---|
| `SOURCE_LANG` | `en` | source 언어. CLI `--in-lang` 로 override |
| `TARGET_LANG` | `kr` | target 언어. 출력 접미사 = uppercase (`_KR`) |
| `BATCH_SIZE` | `8` | 한 번의 LLM 호출에 포함할 segment 수 |
| `MAX_TOKENS` | `4096` | 응답 토큰 상한 |
| `TEMPERATURE` | `0` | 결정적 출력을 위해 기본 0 |

언어 코드 표기는 ppt-translate-v4 와 동일: `en`, `kr`, `ch`, `jp`. 입력은 `ko/Korean/zh/japanese` 등 다양한 alias 를 허용 (`util/lang.mjs::normalizeLang`).

### 파일 경로

| 키 | 기본값 | 설명 |
|---|---|---|
| `WORK_DIR` | `work` | 중간 산출물 루트 (cwd 기준 상대) |
| `INPUT_DIR` | `input` | 일괄 모드 스캔 대상 |
| `OUTPUT_DIR` | `output` | 결과 PDF 저장 위치 |
| `DONE_DIR` | `input/done` | 성공한 원본 이동 위치 |
| `TM_DB_PATH` | `work/tm.sqlite` | Translation Memory SQLite 파일 |
| `GLOSSARY_PATH` | `glossary.csv` | 용어집 파일 |

### PDF 엔진

| 키 | 기본값 | 설명 |
|---|---|---|
| `PDF_ENGINE_BIN` | "" | `pdftr` 바이너리 절대 경로. 비우면 자동 탐색 |
| `PDF_FONT_PATH` | "" | 한글 등 비-Latin 출력용 TrueType 폰트 경로 (현재 v1 CLI 가 미수신, TODO) |
| `PDF_KEEP_ORIGINAL_LANG` | `false` | true 면 원본 위에 번역문을 덧씌움 (layout 정책 없음, 실험용) |
| `PDF_KEEP_INPUT` | `false` | true 면 input/ 의 원본을 done/ 으로 이동하지 않음 |

## 보안

- **`.env` 절대 git 커밋 금지** (`.gitignore` 에 등록).
- `.env.example` 에는 placeholder 만.
- API 키 노출 시 즉시 로테이션.

## 파서 규칙

- `dotenv/config` 가 자동 로드 (`process.env`).
- `util/env.mjs::loadConfig(options)` 가 정수/실수/boolean 변환을 담당.
- CLI 옵션이 환경변수보다 우선 (`--in-lang`, `--out-lang`, `--keep-input`, `--reset-tm`).
- 알 수 없는 키는 무시 (dotenv 가 그대로 `process.env` 에 둠).
