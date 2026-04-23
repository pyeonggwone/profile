# STEP 1: PPTX 로드 + 슬라이드 클리어

## 구현 모듈

| 엔진 | 진입점 | 내부 구현 |
|------|--------|----------|
| python-pptx (기본) | `library/step1_clear.py` | `python-pptx` Presentation |
| Microsoft 공식 | `library/step1_clear_microsoft.py` | PowerPoint COM (`pywin32`) |

## 목적

원본 PPTX를 `kr/` 경로에 복사한 뒤, 작업본의 모든 슬라이드에서 Shape를 제거하여 STEP 3에서 번역된 컴포넌트를 재삽입할 수 있는 빈 캔버스를 만든다.

## 처리 흐름

1. `eng/{파일명}.pptx`를 `kr/{파일명}_KO.pptx`로 복사
2. PPTX 엔진(python-pptx 또는 PowerPoint COM)으로 작업본 로드
3. 각 슬라이드를 순회하며 모든 Shape 제거 (슬라이드 자체와 레이아웃은 유지)
4. 작업본 저장

## 주의 사항

- 슬라이드 구조(슬라이드 수, 레이아웃, 마스터, 테마)는 보존
- 슬라이드 노트도 함께 클리어
- Shape 삭제 실패 시 해당 슬라이드 로그 후 다음 슬라이드로 진행

## 입출력

| 구분 | 경로 |
|------|------|
| 입력 | `eng/{파일명}.pptx` |
| 출력 | `kr/{파일명}_KO.pptx` (모든 슬라이드 비어 있음) |
