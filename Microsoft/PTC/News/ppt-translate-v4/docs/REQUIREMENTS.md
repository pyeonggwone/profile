# 요구사항 인덱스

ppt-translate-v3 를 처음부터 다시 구현할 때 참조하는 **파일별 요구사항 명세** 의 인덱스.

## 프로젝트 목표 (Why)

영문 PPTX 슬라이드 덱을 **PowerPoint 데스크톱 엔진(COM Automation)** 으로 직접 열고 텍스트를 한국어로 in-place 치환한다. python-pptx/lxml/OOXML 직접 조작은 사용하지 않는다. 결과 PPTX 는 PowerPoint 가 만든 파일이므로 SmartArt/차트/애니메이션/마스터/그라데이션/3D/사용자 정의 레이아웃 등 모든 프레젠테이션 자산이 100% 보존된다.

## 비기능 요구사항 (전역)

- **OS**: Windows 10/11 native. WSL/Linux 불가 (PowerPoint COM 필요).
- **언어**: Python 3.11+ (Windows native 인터프리터). PEP 723 inline metadata 로 단일 파일 배포.
- **런처**: `uv run --script` (권장) 또는 `python` + `requirements.txt`.
- **외부 의존**: PowerPoint 데스크톱 (Microsoft 365 / 2019 / 2021).
- **응답 언어**: 사용자 출력은 한국어. 코드/식별자/JSON 키는 영어.
- **재현성**: 동일 입력에 대해 결정론적 결과 (LLM `temperature=0`, TM 캐시 우선).
- **격리**: 작업 산출물은 모두 `work/<basename>/` 하위. 입력은 변경하지 않고 `done/` 으로 이동.
- **에러 정책**: per-file 단위 격리. 한 파일 실패가 배치 전체를 중단시키지 않음.

## 파일별 요구사항 명세

| 파일/디렉토리 | 문서 |
|---|---|
| `ppt_translate.py` | [FILE-ppt_translate.md](FILE-ppt_translate.md) |
| `Run-Translate.ps1` | [FILE-Run-Translate.md](FILE-Run-Translate.md) |
| `glossary.csv` | [FILE-glossary-csv.md](FILE-glossary-csv.md) |
| `.env`, `.env.example` | [FILE-env.md](FILE-env.md) |
| `requirements.txt` | [FILE-requirements-txt.md](FILE-requirements-txt.md) |
| `input/`, `output/`, `work/`, `input/done/` | [FILE-runtime-dirs.md](FILE-runtime-dirs.md) |

설계 배경 / 결정 사유: [ARCHITECTURE.md](ARCHITECTURE.md)
운영 매뉴얼 (사용자용): [../MANUAL.md](../MANUAL.md)

## 빌드 우선순위

새로 구현 시 권장 순서:

1. `.env` / `.env.example` (설정 골격)
2. `ppt_translate.py` 의 **EXTRACT** (PowerPoint COM 만으로 segments.json 생성)
3. **TRANSLATE** (LiteLLM + 번호 블록 프로토콜 + TM)
4. **APPLY** (path → paragraph 해석 + Characters() API 치환)
5. **분류기/제목 정제기** (placeholder type / 휴리스틱 / sentence detector)
6. **CLI** (typer 기반 `run/extract/translate/apply/tm`)
7. **배치 모드 + done/ 이동 + verify**
