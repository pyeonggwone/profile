# `requirements.txt` — 요구사항 명세

`uv` 미사용 환경(일반 venv) 을 위한 fallback 의존성 목록. **권장 실행 경로는 `uv run --script ppt_translate.py`** (이 경우 PEP 723 inline metadata 사용).

## 내용

```
pywin32>=306; sys_platform == "win32"
litellm>=1.50
openai>=1.40
pydantic-settings>=2.5
typer>=0.12
rich>=13.8
```

## 각 의존성의 역할

| 패키지 | 용도 | 비고 |
|---|---|---|
| `pywin32` | PowerPoint COM Automation (`win32com.client.Dispatch`) | Windows 전용 |
| `litellm` | OpenAI/Azure OpenAI 통합 호출 | `from litellm import completion` |
| `openai` | litellm 의 underlying SDK | 직접 import 안 함 |
| `pydantic-settings` | `.env` 자동 로드 + 타입 검증 | `BaseSettings` |
| `typer` | CLI (run/extract/translate/apply/tm) | rich 와 자연스럽게 통합 |
| `rich` | console 출력 (진행률, 색상) | `Console.print` |

## 동기화 규칙

`ppt_translate.py` 의 PEP 723 블록과 **반드시 동일한 패키지 목록 + 동일한 버전 하한** 유지. 한 쪽만 바뀌면 uv 사용자와 venv 사용자 사이에 동작이 갈림.

```
# /// script 의 dependencies = [...] 와 requirements.txt 1:1 매핑 필수
```

## 비책임

- 버전 상한 명시 안 함 (LiteLLM 은 빠르게 진화 — 호환성은 런타임에 확인).
- `dev` / `lint` 의존성 분리 안 함 (단일 파일 도구라 불필요).

## 테스트 체크리스트

- [ ] 깨끗한 venv 에서 `pip install -r requirements.txt` 성공
- [ ] WSL 에서 설치 시 `pywin32` 자동 skip (sys_platform marker)
- [ ] `python ppt_translate.py --help` 동작
