# PPTX EN→KR 번역 파이프라인 매뉴얼

## 최초 설치 (처음 한 번만)

```bash
# 1. Python 가상환경 생성 및 활성화
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # WSL/Linux

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경변수 설정
copy .env.example .env          # Windows
# cp .env.example .env          # WSL/Linux
# .env 파일을 열어 AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT
# 또는 OPENAI_API_KEY, OPENAI_MODEL 입력

# 4. 번역 대상 파일 배치
#    eng/ 폴더에 .pptx 또는 .ppt 파일 복사
```

---

## PPTX 처리 엔진 선택

| 엔진 | 옵션값 | 환경 요구사항 | 비고 |
|------|--------|--------------|------|
| python-pptx (기본) | `--engine python-pptx` | Python만 있으면 됨 (WSL/Linux 가능) | 서드파티 OSS, 빠르지만 SmartArt/차트 등 일부 OOXML 미지원 |
| Microsoft 공식 | `--engine microsoft` | Windows native Python + PowerPoint 데스크톱 설치 + `pywin32` | PowerPoint COM Automation, 모든 PPTX 기능 지원 |

> `--engine microsoft` 사용 시 `library/*_microsoft.py` 모듈이 호출된다.
> python-pptx 기반 모듈(`library/extractor.py` 등)은 그대로 유지되며,
> `--engine python-pptx` 옵션 사용 시 동일하게 동작한다.

---

## 실행 방식

```bash
# 기본 실행 (OpenAI + python-pptx)
python main.py

# Azure OpenAI 사용
python main.py --llm azure

# Microsoft PowerPoint COM Automation 사용
python main.py --engine microsoft

# Azure + Microsoft 엔진 + 설명자료(STEP 4) 포함
python main.py --llm azure --engine microsoft --step4
```

### 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--llm openai\|azure` | `openai` | LLM 백엔드 선택 |
| `--engine python-pptx\|microsoft` | `python-pptx` | PPTX 처리 엔진 선택 |
| `--step4` | (off) | 설명자료 PPTX 생성(STEP 4) 포함 (`template_guide.pptx` 필요) |

---

## 파이프라인 흐름

```
eng/ 파일 목록 수집
└─ 파일별 반복:
     STEP 1  슬라이드 클리어/복사  (step1_clear[_microsoft].py)
     STEP 2  컴포넌트 추출        (step2_extract[_microsoft].py)
     STEP 3  번역 + 재생성        (step3_translate[_microsoft].py)
    [STEP 4] 설명자료 생성        (step4_guide.py)  ← --step4 옵션 시에만
완료 파일은 eng/ → done/ 으로 이동
```

자세한 단계별 동작은 [docs/](docs/) 의 각 STEP 문서를 참고한다.

## 최초 설치 (처음 한 번만)

```bash
# 1. Python 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경변수 설정
cp .env.example .env
# .env 파일을 열어 AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT 입력

# 4. 번역 대상 파일 배치
#    eng/ 폴더에 .pptx 또는 .ppt 파일 복사
```

---

## 실행 방식

```bash
# 전체 파이프라인 실행 (eng/ 내 모든 PPT/PPTX 자동 처리)
python main.py

# 번역만 실행 (설명자료 스킵)
python main.py --skip-guide

# 분석 재사용 (이미 분석 결과 있을 때 속도 향상)
python main.py --skip-analysis
```

| 옵션 | 설명 |
|------|------|
| `--skip-analysis` | STEP 3 스킵 (work/analysis/ 에 결과 json이 이미 있는 경우) |
| `--skip-guide` | STEP 5 스킵 (번역 파일만 필요한 경우) |
