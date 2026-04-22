
---

# PPTX 한글 번역 및 설명자료 생성 파이프라인 요구사항 정의

## 목적

영어 PPTX 파일을 LLM으로 분석하여 문서 성격을 파악하고, 한글 번역 파일을 자동 생성한다. 다른 PPTX 파일에도 반복 적용 가능한 범용 구조로 설계한다.
설명자료 생성(STEP 5)은 구현은 되어 있으나 기본 실행에서 제외하며, STEP 1~4 완성을 1차 목표로 한다.

---

## Python 버전 및 의존성

- **Python**: 3.9.25 (WSL 환경)

### requirements.txt

```
python-pptx==0.6.23
openai==1.75.0
python-dotenv==1.1.0
tqdm==4.67.1
```

---

## 전체 파이프라인

```
[STEP 1] PPTX 로드
    └─ 원본 파일을 kr/ 경로에 복사하여 번역 작업본 생성

[STEP 2] 슬라이드별 컴포넌트 직렬화
    └─ extractor.py: 슬라이드별로 모든 Shape(텍스트박스·이미지·표 등) 순서대로 순회
    └─ 각 Shape의 위치·크기·폰트·텍스트·이미지 등 상태를 슬라이드별 JSON으로 저장
    └─ font_analyzer.py: eng 폰트 수집 → font.json 대조/신규 폰트 LLM 선택 후 저장

[STEP 3] LLM 문서 성격 분석
    └─ llm_analyzer.py: 작업본의 슬라이드를 루프로 1장씩 독립 LLM 호출
    └─ 각 슬라이드 분석 결과를 슬라이드별로 개별 저장 (합치지 않음)
    └─ 저장 경로: work/analysis/{파일명}/slide_{N}.json

[STEP 4] 슬라이드별 삭제 → 재생성 (번역 포함)
    └─ translator.py: 작업본의 슬라이드를 루프로 1장씩 처리
        4.1 해당 슬라이드의 모든 Shape를 순서대로 삭제하고 상태 보관
        4.2 삭제한 순서대로 Shape를 하나씩 재생성
        4.3 텍스트 포함 Shape → LLM으로 한글 번역 후 삽입 (사전 참조)
        4.4 이미지·표 등 비텍스트 Shape → 저장된 상태 그대로 복원
        4.5 슬라이드 완료 시 dict_manager.py로 별도 LLM 호출, 신규 용어 추출 → 사전 업데이트
    └─ 모든 슬라이드 완료 후 작업본을 _KO.pptx로 저장

[STEP 5] 설명자료 PPTX 생성 (구현 완료, 기본 실행 제외)
    └─ doc_generator.py: 템플릿 .pptx 기반, LLM이 슬라이드 내용 JSON 생성 → python-pptx로 삽입
    └─ 출력: {원본파일명}_GUIDE.pptx
```

---

## 오픈소스 및 라이브러리

| 기능 | 라이브러리 |
|------|-----------|
| PPTX 읽기/쓰기 | `python-pptx` |
| LLM 호출 | `openai` |
| 환경변수 관리 | `python-dotenv` |
| 진행률 표시 | `tqdm` |
| 사전/분석결과 관리 | 표준 `json` |

---

## 파일 구조

```
ppt_EN_to_KR/
├── main.py                        # 메인 실행 스크립트 (STEP 1~4 실행, STEP 5 제외)
├── requirements.txt               # 의존성 목록
├── .env                           # 환경변수 (git 제외)
├── .env.example                   # 환경변수 템플릿
├── translation_dict.json          # 번역 사전 (누적 관리)
├── font.json                      # 영어→한글 폰트 1:1 대응 누적 저장
├── template_guide.pptx            # 설명자료 생성용 템플릿 (STEP 5 전용)
├── library/
│   ├── handler_pptx.py            # .pptx 파일 처리 진입점 (STEP 2~5 순차 호출)
│   ├── handler_ppt.py             # .ppt 파일 처리 진입점 (LibreOffice → temp/ 변환 후 handler_pptx 위임)
│   ├── extractor.py               # 텍스트 추출 및 .txt 저장 (STEP 2)
│   ├── font_analyzer.py           # eng 폰트 수집 + font.json 관리 (STEP 2 보조)
│   ├── llm_analyzer.py            # LLM 문서 성격 분석, 슬라이드별 독립 호출 후 집계 (STEP 3)
│   ├── translator.py              # LLM 번역, 슬라이드별 JSON 응답 (STEP 4)
│   ├── dict_manager.py            # 번역 사전 로드/업데이트, 별도 LLM 호출 (STEP 4 보조)
│   ├── doc_generator.py           # 설명자료 PPTX 생성 (STEP 5, 기본 실행 제외)
│   └── progress_manager.py        # 전체 과정 기록용 progress.json 저장/로드
├── temp/                          # 임시 파일 경로 (.ppt → .pptx 변환 등, 처리 완료 후 자동 삭제)
├── eng/                           # 번역 대상 원본 파일 보관 (.pptx / .ppt)
├── kr/                            # 번역 완료 파일 저장 (_KO.pptx)
├── done/                          # 번역 완료 후 원본 이동 (eng → done)
└── work/
    ├── extracted_text/            # STEP 2 출력 .txt (파일별)
    ├── analysis/                  # STEP 3 분석 결과 .json (파일별)
    └── progress/                  # 파일별 전체 과정 기록 .json
```

---

## 모듈 간 데이터 인터페이스 정의

모듈 간에는 **파일 경로(str)만** 주고받는다. 객체를 넘기지 않는다.

| 모듈 | 함수 | 입력 (경로) | 출력 (경로) |
|------|------|------------|------------|
| `extractor` | `extract(pptx_path, work_dir)` | 작업본 .pptx 경로, work/ 경로 | 슬라이드별 상태 JSON 저장 경로 |
| `font_analyzer` | `analyze(pptx_path, font_json_path)` | 작업본 .pptx 경로, font.json 경로 | font.json 파일 직접 업데이트 |
| `llm_analyzer` | `analyze(pptx_path, work_dir)` | 작업본 .pptx 경로, work/ 경로 | 슬라이드별 분석 JSON 저장 경로 |
| `translator` | `translate(pptx_path, work_dir, dict_path, font_json_path)` | 작업본 .pptx 경로, work/ 경로, 사전 경로, 폰트맵 경로 | 번역 완료 작업본 파일 직접 수정 |
| `dict_manager` | `update(original_text, translated_text, dict_path)` | 원문, 번역문, 사전 경로 | translation_dict.json 파일 직접 업데이트 |
| `progress_manager` | `save(progress_path, data)` / `load(progress_path)` | progress 경로 | progress.json 파일 직접 업데이트 / Dict |

---

## 환경변수 (.env)

```
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_MODEL=gpt-4o
TRANSLATION_DICT_PATH=./translation_dict.json
FONT_MAP_PATH=./font.json
GUIDE_TEMPLATE_PATH=./template_guide.pptx
ENG_DIR=./eng
KR_DIR=./kr
DONE_DIR=./done
WORK_DIR=./work
TEMP_DIR=./temp
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

- `entries`: 슬라이드 번역마다 LLM이 신규 용어 추출하여 자동 추가
- `protected_terms`: 번역하지 않는 고유명사 목록
- 충돌 시 기존 값 유지 (덮어쓰기 금지)

---

## STEP 2: 텍스트 추출 + 폰트 분석

### extractor.py
- 슬라이드별 텍스트박스, 제목, 표, 노트에서 텍스트 추출
- 각 텍스트에 ID 부여 (s{N}_shape{N}_para{N})
- `work/extracted_text/{파일명}.txt` 저장

### font_analyzer.py
- python-pptx로 각 Shape의 Run 폰트명 수집
- `font.json`과 대조 → 이미 등록된 폰트: 해당 매핑 사용 / 신규 폰트: LLM이 후보 목록에서 선택 후 저장
- **폰트가 None(테마 상속)인 경우: 기본값 `맑은 고딕 (Malgun Gothic)` 적용**

### 한글 지원 폰트 후보 (Windows 기본 탑재)

| 영어 폰트 성격 | 대응 한글 폰트 |
|--------------|-------------|
| 기본 본문 (Calibri, Segoe UI 등) | `맑은 고딕 (Malgun Gothic)` ← **기본값** |
| 고딕/모던 (Arial, Helvetica 등) | `나눔고딕` |
| 제목/강조 (Segoe UI Semibold, Arial Black 등) | `맑은 고딕` |
| 슬림/라이트 (Segoe UI Light 등) | `맑은 고딕 Light` |
| 명조/세리프 (Times New Roman, Georgia 등) | `바탕 (Batang)` |
| 코드/고정폭 (Consolas, Courier 등) | `굴림체 (GulimChe)` |

### font.json 구조

```json
{
  "Segoe UI": "맑은 고딕",
  "Calibri": "맑은 고딕",
  "Arial": "나눔고딕",
  "Times New Roman": "바탕",
  "Consolas": "굴림체",
  "__default__": "맑은 고딕"
}
```

- 전체 프로젝트 공통 누적 관리 (여러 PPT 파일에 걸쳐 재사용)
- `__default__`: 폰트 None 시 사용할 기본 폰트

---

## STEP 3: LLM 문서 성격 분석 (llm_analyzer.py)

- 슬라이드 1장 = pptx/ppt의 실제 슬라이드 1장
- 파일의 전체 슬라이드 수를 먼저 파악 후 루프로 1장씩 순차 처리
- 각 슬라이드를 **독립 LLM 호출**로 분석 (컨텍스트 초과 방지)
- 슬라이드별 분석 결과를 **개별 파일로 저장** — 합치지 않음
- 저장 경로: `work/analysis/{파일명}/slide_{N}.json`

```json
// work/analysis/Microsoft Databases narrative L100/slide_1.json
{
  "slide_num": 1,
  "ppt_type": "제품 설명 / 마케팅",
  "domain": "클라우드, 데이터베이스",
  "tone": "설명적/설득적",
  "key_terms": ["database modernization", "Azure SQL"]
}
```

---

## STEP 4: 슬라이드별 삭제 → 재생성 번역 (translator.py + dict_manager.py)

### 처리 흐름

작업본 파일을 직접 수정. 슬라이드를 루프로 1장씩 처리.

```
슬라이드 루프 (slide_1 → slide_N):
  1. 현재 슬라이드의 모든 Shape를 순서대로 순회하며 상태 기록
     - 텍스트 Shape: 위치, 크기, 텍스트, 폰트, bold/italic/size/color
     - 이미지 Shape: 위치, 크기, 이미지 바이너리
     - 표/기타: 위치, 크기, 원본 XML
  2. 기록한 순서대로 Shape를 슬라이드에서 삭제
  3. 기록한 순서대로 Shape를 하나씩 재생성:
     - 텍스트 포함 Shape이고 영어 텍스트인 경우
         → LLM 호출 (translation_dict.json 참조) → 한글 번역문으로 삽입
         → 폰트명은 font.json 대응 한글 폰트로 교체 (None이면 __default__ 사용)
     - 이미지·표·SmartArt·차트 등 비텍스트 Shape
         → 저장된 상태 그대로 복원 (번역 없음)
  4. 슬라이드 완료 시 dict_manager.py 호출:
     - 해당 슬라이드 원문 + 번역문 전달
     - LLM이 신규 전문 용어 추출 → translation_dict.json 업데이트
다음 슬라이드로 이동 → 전체 슬라이드 완료까지 반복
```

### LLM 번역 호출 단위

- 텍스트 Shape 1개 = LLM 1회 호출 (Paragraph 합산 텍스트를 하나의 문자열로)
- system prompt에 포함: 해당 슬라이드 STEP 3 분석 결과 + translation_dict.json entries + protected_terms
- LLM이 `protected_terms` 목록의 용어는 번역하지 않도록 지시

### 번역 처리 범위

| 요소 | 처리 방식 |
|------|----------|
| 텍스트 박스 / 제목 | 삭제 후 한글 번역문으로 재생성, 서식 유지 |
| 표(Table) 셀 | 같은 방식, 셀별 처리 |
| 슬라이드 노트(Notes) | 동일 |
| 이미지 | 저장된 바이너리 그대로 복원 |
| SmartArt | 삭제하지 않고 원본 XML 그대로 복원 |
| 차트 | 삭제하지 않고 원본 XML 그대로 복원 |

---

## STEP 5: 설명자료 PPTX 생성 (doc_generator.py)

> **기본 실행에서 제외. 구현은 완료된 상태로 유지.**

- `template_guide.pptx` 없으면 자동 스킵
- 템플릿 파일 존재 시:
  1. 템플릿 PPTX 레이아웃/테마 정보를 LLM에 전달
  2. STEP 3 분석 결과 함께 전달
  3. LLM이 슬라이드 구성 및 내용을 JSON으로 반환:
     ```json
     {"slides": [{"layout_index": 1, "title": "개요", "body": "..."}, ...]}
     ```
  4. python-pptx가 JSON 기반으로 슬라이드 생성 → `{파일명}_GUIDE.pptx` 저장 (`kr/`)

---

## progress.json 구조 (work/progress/{파일명}.json)

모니터링 전용 기록. 재개 목적 아님.

```json
{
  "filename": "Microsoft Databases narrative L100.PPTX",
  "started_at": "2026-04-22T10:00:00",
  "completed_at": null,
  "total_slides": 44,
  "steps": {
    "extract": "done",
    "font_analysis": "done",
    "llm_analysis": "done",
    "translation": "in_progress",
    "dict_update": "pending"
  },
  "slides_translated": [1, 2, 3],
  "slides_total": 44
}
```

---

## 실행 방식

```bash
# 기본 실행 (STEP 1~4, eng/ 내 모든 PPT/PPTX 자동 처리)
python main.py

# 분석 재사용 (work/analysis/ 에 결과가 이미 있는 경우)
python main.py --skip-analysis
```

| 옵션 | 설명 |
|------|------|
| `--skip-analysis` | STEP 3 스킵 (분석 결과 json이 이미 있는 경우) |

> STEP 5는 기본 실행에서 제외. 별도 플래그 추가 후 호출 가능하도록 구현만 완료.

---

## 실행 흐름 상세

1. `eng/` 디렉토리에서 `.pptx`, `.ppt` 파일 전체 목록 스캔
2. 확장자 분기:
   - `.pptx` → `handler_pptx.py` 직접 호출
   - `.ppt` → `handler_ppt.py`: LibreOffice CLI로 `temp/`에 `.pptx` 변환 후 `handler_pptx.py` 위임, 처리 완료 후 `temp/` 파일 삭제
3. 각 파일에 대해 STEP 1~4 순차 실행 (중단 없이 처음부터 끝까지)
4. 번역 완료 파일 → `kr/` 저장
5. 모든 파일 처리 완료 후 `eng/` 내 원본 파일 → `done/` 이동

> **TODO**: API 오류 처리 (rate limit, timeout, JSON 파싱 실패 시 retry 및 fallback 정책) — STEP 1~4 번역 성공 확인 후 구현 예정

FONT_MAP_PATH=./font.json
GUIDE_TEMPLATE_PATH=./template_guide.pptx
ENG_DIR=./eng
KR_DIR=./kr
DONE_DIR=./done
WORK_DIR=./work
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

## STEP 2: 텍스트 추출 + 폰트 분석 (extractor.py + font_analyzer.py)

- 슬라이드별로 텍스트박스, 제목, 표, 노트에서 텍스트 추출 → `work/extracted_text/{파일명}.txt` 저장
- `font_analyzer.py`가 python-pptx로 직접 각 Shape의 Run 폰트명을 수집
  - 추출한 eng 폰트 목록을 `font.json`과 대조
  - 이미 대응 kr 폰트가 등록된 경우 → 해당 매핑 사용
  - 신규 폰트인 경우 → LLM이 아래 한글 지원 폰트 목록에서 1:1 대응 폰트 선택 후 `font.json`에 저장

### 한글 지원 폰트 후보 (Windows 기본 탑재)

| 영어 폰트 성격 | 대응 한글 폰트 |
|--------------|-------------|
| 기본 본문 (Calibri, Segoe UI 등) | `맑은 고딕 (Malgun Gothic)` |
| 고딕/모던 (Arial, Helvetica 등) | `나눔고딕` |
| 제목/강조 (Segoe UI Semibold, Arial Black 등) | `맑은 고딕 Bold` |
| 슬림/라이트 (Segoe UI Light 등) | `맑은 고딕 Light` |
| 명조/세리프 (Times New Roman, Georgia 등) | `바탕 (Batang)` |
| 코드/고정폭 (Consolas, Courier 등) | `굴림체 (GulimChe)` |

### font.json 구조

```json
{
  "Segoe UI": "맑은 고딕",
  "Segoe UI Semibold": "맑은 고딕",
  "Calibri": "맑은 고딕",
  "Arial": "나눔고딕",
  "Times New Roman": "바탕",
  "Consolas": "굴림체"
}
```

- 파일 단위가 아닌 **전체 프로젝트 공통 누적** 관리 (여러 PPT 파일에 걸쳐 재사용)
- 신규 폰트 등장 시 LLM이 후보 목록에서 선택 → 즉시 저장

---

## STEP 3: LLM 문서 성격 분석 (llm_analyzer.py)

- 컨텍스트 초과 방지: 전체 슬라이드 텍스트를 **한 번에 전달하지 않음**
- **슬라이드 1개씩** 순차적으로 LLM에 전달하여 분석 누적
- 최종 분석 결과를 JSON으로 저장: `work/analysis/{파일명}.json`

```json
{
  "ppt_type": "제품 설명 / 마케팅",
  "domain": "클라우드, 데이터베이스",
  "tone": "설명적/설득적",
  "key_terms": ["database modernization", "AI workload", "Azure SQL"],
  "slide_count": 44
}
```

---

## STEP 4: 번역 (translator.py + dict_manager.py)

### 번역 처리 방식

- 처리 단위: **슬라이드 1개씩** LLM 호출 (컨텍스트 초과 방지)
- LLM system prompt에 포함되는 context:
  - STEP 3 분석 결과 (문서 성격, 도메인, 톤)
  - 번역 사전 (`translation_dict.json` 전체)
  - 보호 용어 목록 (번역 금지)
- 번역 대상: 영어 텍스트만 (숫자, URL, 기호, 이미 한국어인 텍스트 원문 유지)

### Run 병합 및 서식 처리 방식

Paragraph 내 여러 Run의 서식이 혼재하는 문제를 아래 방식으로 해결:

1. Paragraph 내 모든 Run의 텍스트를 합산하여 하나의 문자열로 LLM에 번역 요청
2. 번역 결과를 **첫 번째 Run**에 삽입
3. 나머지 Run은 텍스트를 빈 문자열(`""`)로 설정
4. 첫 번째 Run의 원본 서식(bold, italic, size, color, underline)을 그대로 유지
5. 폰트명만 `font.json` 대응 한글 폰트로 교체

> 인라인 서식 혼재(예: 단어 하나만 bold)는 번역 후 첫 Run 서식 단일화로 처리. 원본 서식 완전 보존보다 가독성 우선.

### 번역 사전 자동 업데이트

- 슬라이드 번역 완료 후 **별도 LLM 호출**로 신규 용어 추출
- 요청 내용: "이 번역에서 사전에 추가할 만한 전문 용어 쌍을 JSON으로 반환"
- 반환된 용어를 `translation_dict.json`에 병합 저장
- 기존 `entries`와 충돌 시 기존 값 유지 (덮어쓰기 금지)

### 번역 처리 범위

| 요소 | 처리 방식 |
|------|----------|
| 일반 텍스트 박스 | Paragraph > Run 병합 후 번역, 첫 Run에 결과 삽입 |
| 슬라이드 제목 | 동일 |
| 표(Table) 셀 | 셀별 동일 처리 |
| 슬라이드 노트(Notes) | 동일 |
| 이미지 | 원위치 유지 (스킵) |
| SmartArt 텍스트 | 스킵 |
| 차트 레이블 | 스킵 |

---

## STEP 5: 설명자료 PPTX 생성 (doc_generator.py)

- `template_guide.pptx` 파일이 없으면 이 단계 전체 스킵
- 템플릿 파일이 존재하면:
  1. 템플릿 PPTX의 레이아웃, 테마, 슬라이드 구성을 LLM에 전달
  2. STEP 3 분석 결과(문서 성격, 도메인, 톤)도 함께 전달
  3. LLM이 템플릿 성격과 원본 PPT 내용을 종합하여 설명자료 슬라이드 구성 및 내용을 직접 판단·생성
  4. 생성된 내용을 템플릿 레이아웃에 삽입하여 `{파일명}_GUIDE.pptx` 저장

---

## progress.json 구조 (work/progress/{파일명}.json)

번역 중단 없이 처음부터 끝까지 진행. progress.json은 재개 목적이 아닌 **전체 과정 기록 및 모니터링용**.

```json
{
  "filename": "Microsoft Databases narrative L100.PPTX",
  "started_at": "2026-04-22T10:00:00",
  "completed_at": null,
  "total_slides": 44,
  "steps": {
    "extract": "done",
    "font_analysis": "done",
    "llm_analysis": "done",
    "translation": "in_progress",
    "dict_update": "pending",
    "guide_generation": "pending"
  },
  "slides_translated": [1, 2, 3],
  "slides_total": 44
}
```














