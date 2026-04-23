
---

# PPTX 한글 번역 및 설명자료 생성 파이프라인 요구사항 정의

## 목적

영어 PPTX 파일을 LLM으로 분석하여 문서 성격을 파악하고, 한글 번역 파일을 자동 생성한다. 다른 PPTX 파일에도 반복 적용 가능한 범용 구조로 설계한다.
설명자료 생성(STEP 4)은 구현은 되어 있으나 기본 실행에서 제외하며, STEP 1~3 완성을 1차 목표로 한다.

---

## Python 버전 및 의존성

- **Python**: 3.9.25 (WSL 환경)

### requirements.txt

```
python-pptx==0.6.23
openai==1.75.0
python-dotenv==1.1.0
tqdm==4.67.1

# Microsoft 공식 엔진(--engine microsoft) 사용 시 필요
# Windows native Python + PowerPoint 데스크톱 설치 환경 전용
pywin32==306 ; sys_platform == "win32"
```

---

## PPTX 처리 엔진

두 가지 엔진 중 선택 가능 (기본값: `python-pptx`).

| 엔진 | CLI 옵션 | 사용 모듈 | 환경 |
|------|----------|----------|------|
| python-pptx (서드파티 OSS) | `--engine python-pptx` | `library/extractor.py`, `step1_clear.py`, `step2_extract.py`, `step3_translate.py`, `translator.py`, `font_analyzer.py` | WSL/Linux/Windows 모두 가능 |
| Microsoft 공식 (PowerPoint COM Automation) | `--engine microsoft` | `library/*_microsoft.py` (extractor / step1~3 / translator / font_analyzer / com_app / com_replacer) | Windows native Python + PowerPoint 데스크톱 + `pywin32` 필수 |

원본 python-pptx 모듈은 그대로 유지되며, Microsoft 엔진은 동일한 JSON 스키마/디렉토리 구조를 산출하도록 별도 `_microsoft.py` 파일로 병행 구현되어 있다.

---

## 전체 파이프라인

```
[STEP 1] PPTX 로드 + 슬라이드 클리어
    └─ 원본 파일을 kr/ 경로에 복사하여 번역 작업본 생성
    └─ kr/ 작업본의 각 슬라이드 내 모든 Shape 제거 (슬라이드 구조는 유지, 재생성 시 중복 방지)

[STEP 2] 슬라이드별 컴포넌트 직렬화 (extractor.py + font_analyzer.py)
    └─ 원본 PPTX에서 슬라이드별 모든 Shape를 순서대로 순회하여 상태 추출
    └─ 텍스트 Shape: id, 위치, 크기, paragraphs(텍스트·폰트·bold/italic/size/color)
    └─ 이미지 Shape: id, 위치, 크기 → work/img/{파일명}/slide_{N}/ 에 .jpg로 저장, 경로 기록
    └─ 표(Table): id, 위치, 크기, rows(셀별 텍스트·서식)
    └─ SmartArt·차트: id, 위치, 크기, shape_type만 기록 (내용 직렬화 생략)
    └─ 슬라이드 노트: 텍스트 추출하여 notes 필드에 저장
    └─ 출력: work/components/{파일명}/slide_{N}_component.json + slide_{N}_font.json

[STEP 3] 슬라이드별 JSON 기반 번역 + 재생성
    └─ translator.py: STEP 2 JSON을 입력으로 슬라이드를 루프로 1장씩 처리
        3.1 component JSON에서 텍스트 Shape 목록 추출 → 슬라이드 단위 LLM 1회 호출로 일괄 번역
        3.2 JSON 항목을 순서대로 kr/ 슬라이드에 Shape 삽입, 완료 항목을 상태 JSON에 기록
        3.3 이미지 → STEP 2에서 저장한 img_path 경로에서 로드하여 삽입
        3.4 SmartArt·차트 → 동일 위치·크기의 사각형 Shape로 대체 (미구현 placeholder)
        3.5 슬라이드 완료 시 dict_manager.py로 별도 LLM 호출, 신규 용어 추출 → 사전 업데이트
        3.6 모든 슬라이드 완료 후 구현 상태 JSON 검증 (미처리 항목 리스트 출력)
    └─ 모든 슬라이드 완료 후 작업본을 _KO.pptx로 저장

[STEP 4] 설명자료 PPTX 생성 (구현 완료, 기본 실행 제외)
    └─ doc_generator.py: 템플릿 .pptx 기반, LLM이 슬라이드 내용 JSON 생성 → python-pptx로 삽입
    └─ 출력: {원본파일명}_GUIDE.pptx
```

---

## 오픈소스 및 라이브러리

| 기능 | 라이브러리 |
|------|-----------|
| PPTX 읽기/쓰기 (기본) | `python-pptx` |
| PPTX 읽기/쓰기 (Microsoft 공식) | `pywin32` (PowerPoint COM Automation) |
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
│   ├── config.py                  # 환경변수 로드, LLM 클라이언트 빌드, 경로 설정
│   ├── logger.py                  # 파일별 로거 초기화
│   ├── ppt_converter.py           # .ppt → .pptx 변환 (LibreOffice)
│   ├── progress_manager.py        # 전체 과정 기록용 progress.json 저장/로드
│   ├── dict_manager.py            # 번역 사전 로드/업데이트, 별도 LLM 호출 (STEP 3 보조)
│   ├── doc_generator.py           # 설명자료 PPTX 생성 (STEP 4, 기본 실행 제외)
│   ├── # ── python-pptx 엔진 (기본) ─────────────────────
│   ├── step1_clear.py             # STEP 1 진입점
│   ├── step2_extract.py           # STEP 2 진입점
│   ├── step3_translate.py         # STEP 3 진입점
│   ├── step4_guide.py             # STEP 4 진입점 (--step4)
│   ├── extractor.py               # 슬라이드별 컴포넌트 직렬화 (STEP 2)
│   ├── font_analyzer.py           # eng 폰트 수집 + slide_{N}_font.json (STEP 2 보조)
│   ├── translator.py              # STEP 2 JSON 기반 LLM 번역 + kr/ 재생성 (STEP 3)
│   ├── ooxml_replacer.py          # OOXML 직접 치환 보조
│   ├── # ── Microsoft 엔진 (--engine microsoft) ────────
│   ├── step1_clear_microsoft.py   # STEP 1 진입점 (PowerPoint COM)
│   ├── step2_extract_microsoft.py # STEP 2 진입점 (PowerPoint COM)
│   ├── step3_translate_microsoft.py # STEP 3 진입점 (PowerPoint COM)
│   ├── extractor_microsoft.py     # COM 기반 컴포넌트 직렬화
│   ├── font_analyzer_microsoft.py # COM 기반 폰트 분석
│   ├── translator_microsoft.py    # COM 기반 번역/재생성
│   ├── com_app_microsoft.py       # PowerPoint Application 인스턴스 관리
│   └── com_replacer_microsoft.py  # COM Shape 텍스트/서식 치환 유틸
├── temp/                          # 임시 파일 경로 (.ppt → .pptx 변환 등, 처리 완료 후 자동 삭제)
├── eng/                           # 번역 대상 원본 파일 보관 (.pptx / .ppt)
├── kr/                            # 번역 완료 파일 저장 (_KO.pptx)
├── done/                          # 번역 완료 후 원본 이동 (eng → done)
└── work/
    ├── components/                # STEP 2 출력 ({파일명}/slide_{N}_component.json, slide_{N}_font.json)
    ├── img/                       # STEP 2 이미지 파일 ({파일명}/slide_{N}/*.jpg)
    ├── translated/                # STEP 3 구현 상태 .json (슬라이드별)
    └── progress/                  # 파일별 전체 과정 기록 .json
```

---

## 모듈 간 데이터 인터페이스 정의

모듈 간에는 **파일 경로(str)만** 주고받는다. 객체를 넘기지 않는다.

| 모듈 | 함수 | 입력 (경로) | 출력 (경로) |
|------|------|------------|------------|
| `extractor` | `extract(pptx_path, work_dir)` | 원본 .pptx 경로, work/ 경로 | slide_{N}_component.json, slide_{N}_font.json 저장 |
| `font_analyzer` | `analyze(pptx_path, font_json_path)` | 원본 .pptx 경로, font.json 경로 | font.json 파일 직접 업데이트 |
| `translator` | `translate(kr_pptx_path, work_dir, dict_path, font_json_path)` | kr/ 작업본 경로, work/ 경로, 사전 경로, 폰트맵 경로 | kr/ 작업본 파일 직접 수정 |
| `dict_manager` | `update(original_text, translated_text, dict_path)` | 원문, 번역문, 사전 경로 | translation_dict.json 파일 직접 업데이트 |
| `progress_manager` | `save(progress_path, data)` / `load(progress_path)` | progress 경로 | progress.json 파일 직접 업데이트 / Dict |

---

## 환경변수 (.env)

생성완료

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
- python-pptx 라이브러리로 슬라이드별 로드 가능한 모든 컴포넌트를 추출
- JSON에 컴포넌트 종류별 사전 정의 템플릿 기반으로 배열 저장
- 해당 슬라이드에 존재하는 컴포넌트만 포함, 없는 컴포넌트 키는 제거
- 저장 경로: `work/extracted_text/{파일명}/slide_{N}.json`

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

## STEP 2 출력 JSON 예시

- LLM 미사용. PPTX 엔진(python-pptx 또는 PowerPoint COM)으로 슬라이드별 모든 컴포넌트를 추출
- JSON에 컴포넌트 종류별 사전 정의 템플릿이 존재하며, 컴포넌트 이름별 배열로 저장
- 해당 슬라이드에 존재하는 컴포넌트만 저장, 없는 컴포넌트 키는 제거
- 저장 경로: `work/components_en/{파일명}/slide_{N}_component_en.json`

```json
// work/analysis/Microsoft Databases narrative L100/slide_1.json
{
  "slide_num": 1,
  "text_boxes": [
    {
      "id": "s1_shape1",
      "left": 100, "top": 50, "width": 600, "height": 80,
      "paragraphs": [
        {"text": "Cloud Database Modernization", "font": "Calibri", "bold": true, "size": 28, "color": "#000000"}
      ]
    }
  ],
  "images": [
    {"id": "s1_shape2", "left": 400, "top": 200, "width": 300, "height": 200}
  ],
  "tables": [],
  "notes": ""
}
```

---

## STEP 3: 슬라이드별 JSON 기반 번역 + 재생성 (translator.py + dict_manager.py)

### 처리 흐름

STEP 2 JSON을 입력으로, STEP 1에서 클리어된 kr/ 슬라이드에 Shape를 삽입한다.

```
[전제] STEP 1에서 kr/ 슬라이드 Shape 클리어 완료
       STEP 2에서 슬라이드별 component JSON 추출 완료

슬라이드 루프 (slide_1 → slide_N):
  1. slide_{N}_component.json, slide_{N}_font.json 로드
  2. component JSON의 텍스트 Shape 목록 전체를 슬라이드 단위로 LLM 1회 호출하여 일괄 번역
     - LLM에 텍스트 Shape 목록을 JSON 배열로 전달 → 번역된 JSON 배열 반환
     - translation_dict.json entries를 prompt에 참조 포함
     - protected_terms 번역 제외
     - 영어 단어가 하나라도 있으면 번역 (LLM이 판단)
  3. JSON 항목을 순서대로 하나씩 kr/ 슬라이드에 Shape 삽입 (python-pptx):
     - 텍스트 Shape → 번역된 텍스트 삽입, slide_{N}_font.json 대응 한글 폰트 적용
     - 이미지 Shape → img_path 경로에서 이미지 로드 후 삽입
     - 표(Table) → 번역된 셀 텍스트로 표 재생성
     - 슬라이드 노트 → 번역된 텍스트 삽입
     - SmartArt·차트 → 동일 위치·크기의 사각형 Shape로 대체 (미구현 placeholder)
     - 각 항목 완료 시 구현 상태를 work/translated/{파일명}/slide_{N}.json에 기록
  4. 슬라이드 완료 시 dict_manager.py 호출:
     - translation_dict.json의 key 목록 추출
     - 원문 + key 목록을 prompt에 포함
     - LLM 지시: 리스트에 없는 단어가 있으면 key로 사전에 추가
다음 슬라이드로 이동 → 전체 슬라이드 완료까지 반복

[검증] 모든 슬라이드 완료 후:
  - work/translated/ 구현 상태 JSON과 STEP 2 component JSON 비교
  - 미처리 항목(누락 Shape 등) 리스트 출력
```

### LLM 번역 호출 단위

- 입력: slide_{N}_component.json (STEP 2 추출 결과)
- **슬라이드 1개 = LLM 1회 호출** (텍스트 Shape 전체를 JSON 배열로 일괄 전달)
- LLM 지시: "영어를 한국어로 번역하라" (단순 번역 명령)
- LLM이 번역된 텍스트를 JSON 배열로 반환 → python-pptx로 kr/ 슬라이드에 삽입
- 번역 품질 향상을 위해 `translation_dict.json` entries를 prompt에 참조 포함
- `protected_terms` 목록 용어는 번역 제외하도록 지시

### 영어 텍스트 판별 기준

- 영어 단어가 **하나라도** 있으면 번역 대상
- 별도 필터링 없이 LLM이 판단하여 번역

### 번역 처리 범위

| 요소 | 처리 방식 |
|------|----------|
| 텍스트 박스 / 제목 | 번역된 텍스트로 Shape 삽입, slide_{N}_font.json 대응 한글 폰트 적용 |
| 표(Table) 셀 | 번역된 셀 텍스트로 표 재생성 |
| 슬라이드 노트(Notes) | 번역된 텍스트 삽입 |
| 이미지 | STEP 2에서 저장한 img_path 경로로 이미지 로드 후 삽입 |
| SmartArt | 동일 위치·크기의 사각형 Shape로 대체 (placeholder, 미구현) |
| 차트 | 동일 위치·크기의 사각형 Shape로 대체 (placeholder, 미구현) |

---

## STEP 4: 설명자료 PPTX 생성 (doc_generator.py)

> **기본 실행에서 제외. 구현은 완료된 상태로 유지.**

- `template_guide.pptx` 없으면 자동 스킵
- 템플릿 파일 존재 시:
  1. 템플릿 PPTX 레이아웃/테마 정보를 LLM에 전달
  2. STEP 2 component JSON (슬라이드 내용) 함께 전달
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
# 기본 실행 (STEP 1~3, eng/ 내 모든 PPT/PPTX 자동 처리)
python main.py

# 컴포넌트 추출 재사용 (work/components/ 에 결과가 이미 있는 경우)
python main.py --skip-extract
```

| 옵션 | 설명 |
|------|------|
| `--skip-extract` | STEP 2 스킵 (component JSON이 이미 있는 경우) |

> STEP 4는 기본 실행에서 제외. 별도 플래그 추가 후 호출 가능하도록 구현만 완료.

---

## 실행 흐름 상세

1. `eng/` 디렉토리에서 `.pptx`, `.ppt` 파일 전체 목록 스캔
2. 확장자 분기:
   - `.pptx` → `handler_pptx.py` 직접 호출
   - `.ppt` → `handler_ppt.py`: LibreOffice CLI로 `temp/`에 `.pptx` 변환 후 `handler_pptx.py` 위임, 처리 완료 후 `temp/` 파일 삭제
3. 각 파일에 대해 STEP 1~3 순차 실행 (중단 없이 처음부터 끝까지)
4. 번역 완료 파일 → `kr/` 저장
5. 모든 파일 처리 완료 후 `eng/` 내 원본 파일 → `done/` 이동

> **TODO**: API 오류 처리 (rate limit, timeout, JSON 파싱 실패 시 retry 및 fallback 정책) — STEP 1~3 번역 성공 확인 후 구현 예정

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

## STEP 2: 컴포넌트 추출 및 폰트 분석 (extractor.py + font_analyzer.py)

- python-pptx 라이브러리로 슬라이드별 로드 가능한 모든 컴포넌트를 추출
- JSON에 컴포넌트 종류별 사전 정의 템플릿 기반으로 배열 저장 (없는 컴포넌트 키 제거)
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

## STEP 3: 슬라이드 컴포넌트 직렬화 (llm_analyzer.py)

- LLM 미사용. python-pptx 라이브러리로 슬라이드별 모든 컴포넌트를 추출
- 슬라이드 수만큼 순차 처리, 슬라이드별 개별 JSON 파일로 저장
- 저장 경로: `work/analysis/{파일명}/slide_{N}.json`

```json
{
  "slide_num": 1,
  "text_boxes": [
    {
      "id": "s1_shape1",
      "left": 100, "top": 50, "width": 600, "height": 80,
      "paragraphs": [
        {"text": "Cloud Database Modernization", "font": "Calibri", "bold": true, "size": 28, "color": "#000000"}
      ]
    }
  ],
  "images": [],
  "tables": [],
  "notes": ""
}
```

---

## STEP 4: 번역 (translator.py + dict_manager.py)

### 번역 처리 방식

- 입력: 슬라이드별 JSON (STEP 3 추출 결과)
- **슬라이드 1개 = LLM 1회 호출** (텍스트 Shape 전체를 JSON 배열로 일괄 전달)
- LLM 지시: "영어를 한국어로 번역하라" (단순 번역 명령)
- LLM이 번역된 JSON 배열 반환 → python-pptx로 PPTX에 적용
- 번역 품질 향상을 위해 `translation_dict.json` entries를 prompt에 참조 포함
- 보호 용어 목록(`protected_terms`) 번역 제외

### 영어 텍스트 판별 기준

- 영어 단어가 **하나라도** 있으면 번역 대상
- 별도 필터링 없이 LLM이 판단하여 번역

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
- 처리 흐름:
  1. `translation_dict.json`의 key만 추출하여 리스트업
  2. 원문 + key 리스트를 prompt에 포함
  3. LLM 지시: "[용어 리스트] 안에 존재하지 않는 단어가 있다면 해당 단어를 key로 사전에 추가"
- 추출된 용어를 `translation_dict.json`에 병합 저장
- 기존 `entries`와 충돌 시 기존 값 유지 (덮어쓰기 금지)

### 번역 처리 범위

| 요소 | 처리 방식 |
|------|----------|
| 일반 텍스트 박스 | Paragraph > Run 병합 후 번역, 첫 Run에 결과 삽입 |
| 슬라이드 제목 | 동일 |
| 표(Table) 셀 | 셀별 동일 처리 |
| 슬라이드 노트(Notes) | 동일 |
| 이미지 | work/img/ 디렉토리에 .jpg로 저장, 경로를 JSON에 기록 후 복원 |
| SmartArt | 동일 위치·크기의 사각형 Shape로 대체 (placeholder, 미구현) |
| 차트 | 동일 위치·크기의 사각형 Shape로 대체 (placeholder, 미구현) |

---

## STEP 5: 설명자료 PPTX 생성 (doc_generator.py)

- `template_guide.pptx` 파일이 없으면 이 단계 전체 스킵
- 템플릿 파일이 존재하면:
  1. 템플릿 PPTX의 레이아웃, 테마, 슬라이드 구성을 LLM에 전달
  2. STEP 2 component JSON (슬라이드 내용)도 함께 전달
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














