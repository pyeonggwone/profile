[ppt list]

- Microsoft Databases narrative L100
https://microsoft.seismic.com/Link/Content/DCTR2FgpQ8qVM87MfGgPJRdFbmPG

---

# PPTX 한글 번역 및 설명자료 생성 파이프라인 요구사항 정의

## 목적

영어 PPTX 파일을 LLM으로 분석하여 문서 성격을 파악하고, 한글 번역 파일과 별도의 설명자료 PPTX를 자동 생성한다. 다른 PPTX 파일에도 반복 적용 가능한 범용 구조로 설계한다.

---

## 전체 파이프라인

```
[STEP 1] PPTX 로드
    └─ python-pptx 로 파일 읽기

[STEP 2] 텍스트 추출 → .txt 저장
    └─ 가능한 모든 텍스트 (텍스트박스, 제목, 표, 노트)
    └─ 슬라이드 번호 포함하여 구조화된 텍스트 파일로 저장

[STEP 3] LLM 문서 성격 분석
    └─ 추출된 텍스트 전체를 LLM에 전달
    └─ 분석 항목:
        - PPT 유형 (기술 발표 / 마케팅 자료 / 제품 설명 / 고객 제안 등)
        - 도메인 (클라우드, 데이터베이스, AI, 보안 등)
        - 전반적인 문서 톤 (기술적/설명적/설득적)
        - 사용 폰트 종류 및 역할별 대표 스타일 (크기, bold, 색상)
        - 번역 시 주의할 고유 용어 목록 (Microsoft 제품명, 약어 등)
    └─ 분석 결과는 JSON으로 저장하여 이후 단계에서 재사용

[STEP 4] PPT 유형 기반 번역 프로세스
    └─ STEP 3 분석 결과를 system prompt에 포함
    └─ 번역 사전(translation_dict.json) 참조
    └─ 슬라이드 단위 순회, Paragraph 단위 번역
    └─ 번역 완료 후 사전 자동 업데이트
    └─ 출력: {원본파일명}_KO.pptx

[STEP 5] 설명자료 PPTX 생성
    └─ 사전에 정의된 템플릿 .pptx 파일 로드
    └─ STEP 3 분석 결과를 바탕으로 LLM이 슬라이드 구성 자동 생성
    └─ PPT 유형에 맞는 구조로 자동 구성 (요약, 핵심 메시지, 슬라이드별 설명 등)
    └─ 출력: {원본파일명}_GUIDE.pptx
```

---

## 오픈소스 및 라이브러리

| 기능 | 라이브러리 |
|------|-----------|
| PPTX 읽기/쓰기 | `python-pptx` |
| LLM 호출 | `openai` (Azure OpenAI 또는 OpenAI API) |
| 환경변수 관리 | `python-dotenv` |
| 진행률 표시 | `tqdm` |
| 사전/분석결과 관리 | 표준 `json` |

---

## 파일 구조

```
ppt_eng/
├── translate_pptx.py          # 메인 실행 스크립트
├── .env                       # 환경변수 (git 제외)
├── .env.example               # 환경변수 템플릿
├── translation_dict.json      # 번역 사전 (누적 관리)
├── template_guide.pptx        # 설명자료 생성용 템플릿
├── modules/
│   ├── loader.py              # PPTX 로드
│   ├── extractor.py           # 텍스트 추출 및 .txt 저장
│   ├── analyzer.py            # LLM 문서 성격 분석
│   ├── translator.py          # LLM 번역 (슬라이드별)
│   └── doc_generator.py       # 설명자료 PPTX 생성
└── output/
    ├── extracted_text/        # STEP 2 출력 .txt
    ├── analysis/              # STEP 3 분석 결과 .json
    ├── translated/            # STEP 4 번역된 _KO.pptx
    └── guide/                 # STEP 5 설명자료 _GUIDE.pptx
```

---

## 환경변수 (.env)

```
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_MODEL=gpt-4o
TRANSLATION_DICT_PATH=./translation_dict.json
GUIDE_TEMPLATE_PATH=./template_guide.pptx
```

---

## 번역 사전 (translation_dict.json)

```json
{
  "version": 1,
  "entries": {
    "database modernization": "데이터베이스 현대화",
    "workload": "워크로드"
  },
  "protected_terms": [
    "Azure", "Microsoft", "SQL", "Copilot", "Fabric", "OpenAI"
  ]
}
```

- `entries`: 실행마다 LLM이 새 용어를 추출하여 자동 추가
- `protected_terms`: 번역하지 않는 고유명사 목록

---

## STEP 4 번역 처리 범위

### 포함 (번역 대상)

| 요소 | 처리 방식 |
|------|----------|
| 일반 텍스트 박스 | Paragraph > Run 병합 후 번역, 첫 번째 Run에 삽입, 나머지 Run 비움 |
| 슬라이드 제목 | 동일 |
| 표(Table) 셀 | 셀별 동일 처리 |
| 슬라이드 노트(Notes) | 동일 |

### 제외 (스킵)

| 요소 | 이유 |
|------|------|
| 이미지 | 원위치 유지 |
| SmartArt 텍스트 | XML 구조 복잡 |
| 차트 레이블 | 임베디드 Excel 형태 |

---

## STEP 5 설명자료 구성 (LLM 자동 생성)

PPT 유형에 따라 LLM이 아래 슬라이드 구성을 자동 결정:

| PPT 유형 | 설명자료 구성 예시 |
|---------|-----------------|
| 기술 발표 | 개요 → 핵심 기술 요약 → 아키텍처 설명 → 주요 용어 정리 |
| 제품 설명 / 마케팅 | 제품 개요 → 핵심 메시지 → 고객 가치 → 다음 단계 |
| 고객 제안 | 배경 → 솔루션 요약 → 기대 효과 → 참고 슬라이드 목록 |

템플릿 `.pptx`의 레이아웃/테마가 그대로 적용되고, LLM이 내용만 채운다.

---

## 실행 방식

```bash
# 전체 파이프라인 실행
python translate_pptx.py --input "Microsoft Databases narrative L100.PPTX"

# 번역만 실행 (설명자료 스킵)
python translate_pptx.py --input "..." --skip-guide

# 분석 재사용 (이미 분석 결과 있을 때 속도 향상)
python translate_pptx.py --input "..." --skip-analysis
```

| 옵션 | 설명 |
|------|------|
| `--input` | 번역할 PPTX 파일 경로 |
| `--dict` | 번역 사전 경로 (기본값: `./translation_dict.json`) |
| `--template` | 설명자료 템플릿 경로 (기본값: `.env`의 `GUIDE_TEMPLATE_PATH`) |
| `--skip-analysis` | STEP 3 스킵 (분석 결과 json이 이미 있는 경우) |
| `--skip-guide` | STEP 5 스킵 (번역만 필요한 경우) |














