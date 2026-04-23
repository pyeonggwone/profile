# PPTX 한글 번역 및 설명자료 생성 파이프라인

## 목적

영어 PPTX 파일을 LLM으로 자동 번역하여 한글 파일을 생성한다. 다른 PPTX 파일에도 반복 적용 가능한 범용 구조로 설계한다.
STEP 4(설명자료 생성)는 구현만 완료, 기본 실행에서 제외. STEP 1~3 완성을 1차 목표로 한다.

---

## STEP별 상세 문서

| STEP | 문서 | 요약 |
|------|------|------|
| 1 | [docs/STEP1_clear.md](docs/STEP1_clear.md) | PPTX 로드 + 슬라이드 클리어 |
| 2 | [docs/STEP2_extract.md](docs/STEP2_extract.md) | 슬라이드별 컴포넌트 직렬화 + 폰트 분석 |
| 3 | [docs/STEP3_translate.md](docs/STEP3_translate.md) | 슬라이드별 JSON 기반 LLM 번역 + 재생성 |
| 4 | [docs/STEP4_guide.md](docs/STEP4_guide.md) | 설명자료 PPTX 생성 (옵션) |

### 보조 문서

- [docs/dictionary.md](docs/dictionary.md) — translation_dict.json 운영 규칙
- [docs/progress.md](docs/progress.md) — progress.json 구조

---

## 전체 파이프라인 요약

```
[STEP 1] PPTX 로드 + 슬라이드 클리어
    └─ eng/{파일명}.pptx → kr/{파일명}_KO.pptx (모든 Shape 제거된 빈 캔버스)

[STEP 2] 슬라이드별 컴포넌트 직렬화 (extractor.py + font_analyzer.py)
    └─ 원본 PPTX → work/components/{파일명}/slide_{N}_component.json
    └─ 이미지 → work/img/{파일명}/slide_{N}/*.jpg
    └─ 폰트맵 → work/components/{파일명}/slide_{N}_font.json

[STEP 3] 슬라이드별 JSON 기반 번역 + 재생성 (translator.py + dict_manager.py)
    └─ 슬라이드 단위 LLM 1회 호출로 일괄 번역
    └─ 번역 결과를 kr/ 작업본 슬라이드에 Shape로 재삽입
    └─ 신규 용어를 translation_dict.json에 자동 추가
    └─ kr/{파일명}_KO.pptx 최종 저장

[STEP 4] 설명자료 PPTX 생성 (구현 완료, 기본 실행 제외)
    └─ doc_generator.py → kr/{파일명}_GUIDE.pptx
```

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

### 라이브러리 매핑

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
├── main.py                        # 메인 실행 스크립트 (STEP 1~3 실행, STEP 4 제외)
├── requirements.txt               # 의존성 목록
├── .env                           # 환경변수 (git 제외)
├── .env.example                   # 환경변수 템플릿
├── translation_dict.json          # 번역 사전 (누적 관리)
├── font.json                      # 영어→한글 폰트 1:1 대응 누적 저장
├── template_guide.pptx            # 설명자료 생성용 템플릿 (STEP 4 전용)
├── README.md                      # 본 파일 (개요 + 링크)
├── docs/                          # STEP별 상세 명세
│   ├── STEP1_clear.md
│   ├── STEP2_extract.md
│   ├── STEP3_translate.md
│   ├── STEP4_guide.md
│   ├── dictionary.md
│   └── progress.md
├── library/
│   ├── handler_pptx.py            # .pptx 파일 처리 진입점 (STEP 1~3 순차 호출)
│   ├── handler_ppt.py             # .ppt 파일 처리 진입점 (LibreOffice → temp/ 변환 후 handler_pptx 위임)
│   ├── extractor.py               # 슬라이드별 컴포넌트 직렬화 (STEP 2)
│   ├── font_analyzer.py           # eng 폰트 수집 + slide_{N}_font.json 저장 (STEP 2)
│   ├── translator.py              # LLM 번역 + kr/ 슬라이드 재생성 (STEP 3)
│   ├── dict_manager.py            # 번역 사전 로드/업데이트 (STEP 3 보조)
│   ├── doc_generator.py           # 설명자료 PPTX 생성 (STEP 4)
│   └── progress_manager.py        # progress.json 저장/로드
├── temp/                          # .ppt → .pptx 변환 임시 (자동 삭제)
├── eng/                           # 번역 대상 원본 (.pptx / .ppt)
├── kr/                            # 번역 완료 (_KO.pptx)
├── done/                          # 번역 완료 후 원본 이동
└── work/
    ├── components/                # STEP 2 출력 (slide_{N}_component.json + slide_{N}_font.json)
    ├── img/                       # STEP 2 이미지 (.jpg)
    ├── translated/                # STEP 3 구현 상태 .json
    └── progress/                  # 파일별 progress.json
```

---

## 모듈 간 데이터 인터페이스

모듈 간에는 **파일 경로(str)만** 주고받는다. 객체를 넘기지 않는다.

| 모듈 | 함수 | 입력 (경로) | 출력 (경로) |
|------|------|------------|------------|
| `extractor` | `extract(pptx_path, work_dir)` | 원본 .pptx, work/ | slide_{N}_component.json 저장 |
| `font_analyzer` | `analyze(pptx_path, font_json_path)` | 원본 .pptx, font.json | font.json + slide_{N}_font.json 업데이트 |
| `translator` | `translate(kr_pptx_path, work_dir, dict_path, font_json_path)` | kr/ 작업본, work/, 사전, 폰트맵 | kr/ 작업본 직접 수정 |
| `dict_manager` | `update(original_text, translated_text, dict_path)` | 원문, 번역문, 사전 | translation_dict.json 업데이트 |
| `progress_manager` | `save(progress_path, data)` / `load(progress_path)` | progress 경로 | progress.json 업데이트 / Dict |

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

> 실제 키는 `.env` 파일에만 저장하고 git에 커밋하지 않는다 (`.gitignore` 등록 필수).

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
