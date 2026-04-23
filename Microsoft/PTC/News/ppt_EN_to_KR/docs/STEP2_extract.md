# STEP 2: 슬라이드별 컴포넌트 직렬화

`extractor.py` + `font_analyzer.py`. LLM 미사용.

## 구현 모듈

| 엔진 | 진입점 | extractor / font_analyzer | 내부 구현 |
|------|--------|--------------------------|----------|
| python-pptx (기본) | `library/step2_extract.py` | `extractor.py` / `font_analyzer.py` | `python-pptx` |
| Microsoft 공식 | `library/step2_extract_microsoft.py` | `extractor_microsoft.py` / `font_analyzer_microsoft.py` | PowerPoint COM (`pywin32`) |

두 엔진 모두 동일한 JSON 스키마/디렉토리 구조를 산출한다.

## extractor.py

- 원본 PPTX 슬라이드별 모든 Shape를 순서대로 순회하여 상태 추출
- 컴포넌트 종류별 사전 정의 템플릿 기반 배열로 저장
- 해당 슬라이드에 존재하는 컴포넌트만 포함, 없는 컴포넌트 키는 제거
- 저장 경로: `work/components/{파일명}/slide_{N}_component.json`

### 컴포넌트별 처리

| 종류 | 추출 항목 |
|------|----------|
| 텍스트 Shape | id, left/top/width/height, paragraphs(텍스트·폰트·bold/italic/size/color) |
| 이미지 Shape | id, left/top/width/height, img_path → `work/img/{파일명}/slide_{N}/*.jpg` 로 저장 후 경로 기록 |
| 표(Table) | id, left/top/width/height, rows(셀별 텍스트·서식) |
| SmartArt·차트 | id, left/top/width/height, shape_type만 기록 (내용 직렬화 생략) |
| 슬라이드 노트 | 텍스트 추출하여 notes 필드에 저장 |

### slide_{N}_component.json 예시

```json
// work/components/Microsoft Databases narrative L100/slide_1_component.json
{
  "slide_num": 1,
  "text_boxes": [
    {
      "id": "s1_shape1",
      "left": 914400, "top": 457200, "width": 5486400, "height": 685800,
      "paragraphs": [
        {"text": "Cloud Database Modernization", "font": "Calibri", "bold": true, "italic": false, "size": 28, "color": "#000000"}
      ]
    }
  ],
  "images": [
    {"id": "s1_shape2", "left": 4572000, "top": 1828800, "width": 2743200, "height": 1828800, "img_path": "work/img/Microsoft Databases narrative L100/slide_1/image_1.jpg"}
  ],
  "tables": [
    {
      "id": "s1_shape3",
      "left": 457200, "top": 2286000, "width": 8229600, "height": 1371600,
      "rows": [
        [{"text": "Feature", "font": "Calibri", "bold": true, "size": 11, "color": "#FFFFFF"}, {"text": "Description", "font": "Calibri", "bold": true, "size": 11, "color": "#FFFFFF"}],
        [{"text": "High Availability", "font": "Calibri", "bold": false, "size": 11, "color": "#000000"}, {"text": "99.99% SLA", "font": "Calibri", "bold": false, "size": 11, "color": "#000000"}]
      ]
    }
  ],
  "smartarts": [
    {"id": "s1_shape4", "left": 914400, "top": 3657600, "width": 3657600, "height": 1828800, "shape_type": 6}
  ],
  "charts": [],
  "notes": "Speaker notes text here."
}
```

---

## font_analyzer.py

- python-pptx로 각 Shape의 Run 폰트명을 수집하여 슬라이드별 사용 폰트 목록 추출
- 전역 `font.json`과 대조:
  - 이미 등록된 폰트 → 해당 매핑 사용
  - 신규 폰트 → LLM이 한글 지원 폰트 후보에서 1:1 대응 폰트 선택 후 `font.json`에 저장
- 폰트가 `None`(테마 상속)인 경우: `__default__` 키 값 적용
- 슬라이드별 폰트맵 저장 경로: `work/components/{파일명}/slide_{N}_font.json`

### 한글 지원 폰트 후보 (Windows 기본 탑재)

| 영어 폰트 성격 | 대응 한글 폰트 |
|--------------|-------------|
| 기본 본문 (Calibri, Segoe UI 등) | `맑은 고딕 (Malgun Gothic)` ← **기본값** |
| 고딕/모던 (Arial, Helvetica 등) | `나눔고딕` |
| 제목/강조 (Segoe UI Semibold, Arial Black 등) | `맑은 고딕` |
| 슬림/라이트 (Segoe UI Light 등) | `맑은 고딕 Light` |
| 명조/세리프 (Times New Roman, Georgia 등) | `바탕 (Batang)` |
| 코드/고정폭 (Consolas, Courier 등) | `굴림체 (GulimChe)` |

### font.json (전역, 누적)

```json
{
  "Segoe UI": "맑은 고딕",
  "Segoe UI Semibold": "맑은 고딕",
  "Calibri": "맑은 고딕",
  "Arial": "나눔고딕",
  "Times New Roman": "바탕",
  "Consolas": "굴림체",
  "__default__": "맑은 고딕"
}
```

- 전체 프로젝트 공통 누적 관리 (여러 PPT 파일에 걸쳐 재사용)
- `__default__`: 폰트 `None` 시 사용할 기본 폰트

### slide_{N}_font.json

```json
// work/components/Microsoft Databases narrative L100/slide_1_font.json
{
  "slide_num": 1,
  "font_map": {
    "Calibri": "맑은 고딕",
    "Arial": "나눔고딕"
  }
}
```
