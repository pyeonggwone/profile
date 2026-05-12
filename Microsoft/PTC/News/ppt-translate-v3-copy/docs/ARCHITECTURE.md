# Architecture (v3)

## 핵심 결정

| 항목 | 선택 | 이유 |
|------|------|------|
| PPTX 처리 | **PowerPoint COM Automation** (`pywin32`) | Microsoft 공식 엔진 그대로. python-pptx/lxml 미사용 |
| 변환 방식 | **In-place TextRange 치환** | Shape/이미지/SmartArt/차트/애니메이션/마스터 100% 보존 |
| 실행 환경 | **Windows native PowerShell 7+ + Python** | PowerPoint 데스크톱 호출 가능, 한글 폰트 OS 탑재 |
| 배포 | **단일 .py + uv** (PEP 723) | 가상환경/컨테이너/빌드 없음. uv 가 의존성 자동 관리 |
| LLM | LiteLLM | OpenAI/Azure 통합 인터페이스 |
| TM | SQLite | 동일 문장 재번역 방지 |

## 파이프라인

```
input.pptx
  │
  ▼  EXTRACT  (PowerPoint.Application.Open + Slides/Shapes/Runs 순회)
work/{stem}/segments.json
  │           [{slide, path, text}]
  │           path = [shape_idx, (group/table 좌표...), run_idx]
  │
  ▼  TRANSLATE  (TM 조회 → 미스만 LiteLLM 배치 호출)
work/{stem}/translated.json
  │
  ▼  APPLY  (원본 복사 → 동일 path 의 Run.Text 만 교체, Font.Name 만 한글로)
input_KO.pptx
```

## Shape 순회 규칙

| Shape 종류 | 처리 |
|-----------|------|
| TextFrame | `TextRange.Runs(i).Text` 수집 |
| Group (Type=6) | 재귀적으로 GroupItems 진입 |
| Table | `Table.Cell(r,c).Shape.TextFrame.TextRange.Runs(i)` 수집 |
| 노트 | `Slide.NotesPage.Shapes.Placeholders(2).TextFrame.TextRange.Runs(i)` |
| Picture / SmartArt / Chart | 텍스트 노드 없는 Shape 는 건너뜀 (보존됨) |

## path 형식

- 일반 Shape:  `[shape_idx, run_idx]`
- 그룹 내부:   `[group_idx, child_idx, ..., run_idx]`
- 표 셀:       `[shape_idx, row, col, run_idx]`
- 노트:        `["notes", run_idx]`

## 폰트 처리

- 번역 후 `Run.Font.Name` / `Font.NameFarEast` 만 `KR_FONT` (기본 `맑은 고딕`) 로 교체
- bold/italic/size/color 등 다른 속성은 원본 유지

## 확장 포인트

- 차트 내부 텍스트 (`Shape.HasChart`) 처리
- SmartArt 노드 (`Shape.HasSmartArt`) 처리
- 슬라이드 마스터/레이아웃의 placeholder 텍스트 번역
- 번역 품질 후처리 (용어집 일치 검증)
