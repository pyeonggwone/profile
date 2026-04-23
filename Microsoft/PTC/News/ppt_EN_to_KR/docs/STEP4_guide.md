# STEP 4: 설명자료 PPTX 생성 (doc_generator.py)

> **기본 실행에서 제외. 구현은 완료된 상태로 유지.**

## 처리 흐름

- `template_guide.pptx` 없으면 자동 스킵
- 템플릿 파일 존재 시:
  1. 템플릿 PPTX 레이아웃/테마 정보를 LLM에 전달
  2. STEP 2 component JSON (슬라이드 내용) 함께 전달
  3. LLM이 슬라이드 구성 및 내용을 JSON으로 반환:
     ```json
     {"slides": [{"layout_index": 1, "title": "개요", "body": "..."}, ...]}
     ```
  4. python-pptx가 JSON 기반으로 슬라이드 생성 → `{파일명}_GUIDE.pptx` 저장 (`kr/`)
