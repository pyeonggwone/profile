# `.env` / `.env.example` — 요구사항 명세

`pydantic-settings` 가 자동 로드하는 환경 설정 파일. `.env` 는 **gitignore 필수** (실제 키 포함), `.env.example` 은 키를 비운 템플릿으로 커밋.

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

선택 규칙: `AZURE_OPENAI_DEPLOYMENT` 가 비어있지 않으면 `azure/<deployment>`, 아니면 `OPENAI_MODEL` 사용.

### 번역 / 출력

| 키 | 기본값 | 설명 |
|---|---|---|
| `SOURCE_LANG` | `en` | LLM prompt 에 삽입되는 source 언어 코드 |
| `TARGET_LANG` | `ko` | 타겟 언어. 출력 파일명 접미사로도 사용 (`_KO.pptx`) |
| `KR_FONT` | `맑은 고딕` | apply 시 일괄 적용할 한글 폰트 (`Font.Name`, `Font.NameFarEast`) |

### 파일 경로

| 키 | 기본값 | 설명 |
|---|---|---|
| `WORK_DIR` | `work` | 중간 산출물 루트 (cwd 기준 상대) |
| `TM_DB_PATH` | `work/tm.sqlite` | Translation Memory SQLite 파일 |
| `GLOSSARY_PATH` | `glossary.csv` | 용어집 파일 (cwd 기준 상대) |

## 보안

- **`.env` 절대 git 커밋 금지** (`.gitignore` 에 등록).
- `.env.example` 에는 placeholder 만 (실제 키 절대 포함 금지).
- API 키 노출 시 즉시 로테이션.

## 파서 규칙

- `pydantic_settings.BaseSettings(env_file=".env", extra="ignore")`.
- 키 이름은 대소문자 무관 (pydantic 표준).
- 알 수 없는 키는 무시 (`extra="ignore"`).
- `.env` 의 값은 quote 불필요 (한글 폰트명도 그대로 가능).

## 테스트 체크리스트

- [ ] `.env` 미존재 → 기본값으로 동작 (LLM 호출 단계 전까지)
- [ ] `OPENAI_API_KEY` 만 있음 → OpenAI 사용
- [ ] `AZURE_OPENAI_DEPLOYMENT` 추가 → Azure 우선
- [ ] 한글 `KR_FONT` 정상 로드
