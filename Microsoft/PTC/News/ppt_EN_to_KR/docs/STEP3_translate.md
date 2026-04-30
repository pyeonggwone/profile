# STEP 3: 슬라이드별 JSON 기반 번역 + 재생성

`translator.py` + `dict_manager.py`. STEP 2 JSON을 입력으로, STEP 1에서 클리어된 `kr/` 슬라이드에 번역된 Shape를 삽입한다.

## 구현 모듈

| 엔진 | 진입점 | translator / 보조 | 내부 구현 |
|------|--------|--------------------|----------|
| python-pptx (기본) | `library/step3_translate.py` | `translator.py`, `ooxml_replacer.py` | `python-pptx` + OOXML |
| Microsoft 공식 | `library/step3_translate_microsoft.py` | `translator_microsoft.py`, `com_app_microsoft.py`, `com_replacer_microsoft.py` | PowerPoint COM (`pywin32`) |

`dict_manager.py`는 엔진과 무관하게 공용으로 사용된다.

## 처리 흐름

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
     - 텍스트 Shape → 번역된 텍스트 삽입 (Run 병합 처리), slide_{N}_font.json 대응 한글 폰트 적용
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

## LLM 번역 호출 단위

- 입력: `slide_{N}_component.json` (STEP 2 추출 결과)
- **슬라이드 1개 = LLM 1회 호출** (텍스트 Shape 전체를 JSON 배열로 일괄 전달)
- LLM 지시: "영어를 한국어로 번역하라" (단순 번역 명령)
- LLM이 번역된 텍스트를 JSON 배열로 반환 → python-pptx로 `kr/` 슬라이드에 삽입
- 번역 품질 향상을 위해 `translation_dict.json` entries를 prompt에 참조 포함
- `protected_terms` 목록 용어는 번역 제외하도록 지시

## 영어 텍스트 판별 기준

- 영어 단어가 **하나라도** 있으면 번역 대상
- 별도 필터링 없이 LLM이 판단하여 번역

## Run 병합 및 서식 처리 방식

Paragraph 내 여러 Run의 서식이 혼재하는 문제를 아래 방식으로 해결:

1. Paragraph 내 모든 Run의 텍스트를 합산하여 하나의 문자열로 LLM에 번역 요청
2. 번역 결과를 **첫 번째 Run**에 삽입
3. 나머지 Run은 텍스트를 빈 문자열(`""`)로 설정
4. 첫 번째 Run의 원본 서식(bold, italic, size, color, underline)을 그대로 유지
5. 폰트명만 `font.json` 대응 한글 폰트로 교체

> 인라인 서식 혼재(예: 단어 하나만 bold)는 번역 후 첫 Run 서식 단일화로 처리. 원본 서식 완전 보존보다 가독성 우선.

## 번역 사전 자동 업데이트

- 슬라이드 번역 완료 후 **별도 LLM 호출**로 신규 용어 추출
- 처리 흐름:
  1. `translation_dict.json`의 key만 추출하여 리스트업
  2. 원문 + key 리스트를 prompt에 포함
  3. LLM 지시: "[용어 리스트] 안에 존재하지 않는 단어가 있다면 해당 단어를 key로 사전에 추가"
- 추출된 용어를 `translation_dict.json`에 병합 저장
- 기존 `entries`와 충돌 시 기존 값 유지 (덮어쓰기 금지)

## 번역 처리 범위

| 요소 | 처리 방식 |
|------|----------|
| 텍스트 박스 / 제목 | Paragraph > Run 병합 후 번역, 첫 Run에 결과 삽입, slide_{N}_font.json 한글 폰트 적용 |
| 표(Table) 셀 | 셀별 동일 처리 |
| 슬라이드 노트(Notes) | 동일 |
| 이미지 | STEP 2에서 저장한 img_path 경로로 이미지 로드 후 삽입 |
| SmartArt | 동일 위치·크기의 사각형 Shape로 대체 (placeholder, 미구현) |
| 차트 | 동일 위치·크기의 사각형 Shape로 대체 (placeholder, 미구현) |

## 구현 상태 JSON

`work/translated/{파일명}/slide_{N}.json` — 슬라이드별 컴포넌트 단위 처리 완료 여부 기록. 검증 단계에서 STEP 2 component JSON과 비교하여 누락 식별.
