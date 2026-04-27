# `ppt_translate.py` — 요구사항 명세

PEP 723 inline metadata 를 가진 단일 파일 Python 스크립트. EXTRACT / TRANSLATE / APPLY 의 3단계 파이프라인 전체와 CLI 를 모두 포함한다.

## 0. 파일 머리

- PEP 723 블록으로 의존성 선언 (`pywin32`, `litellm`, `openai`, `pydantic-settings`, `typer`, `rich`).
- `requires-python = ">=3.11"`.
- 플랫폼 가드: `sys.platform != "win32"` 면 즉시 `SystemExit`.
- `from __future__ import annotations` 사용.

## 1. 설정 (Settings, pydantic-settings)

- `.env` 자동 로드 (`SettingsConfigDict(env_file=".env", extra="ignore")`).
- 키:
  - `openai_api_key`, `openai_model` (기본 `gpt-4o-mini`)
  - `azure_openai_api_key`, `azure_openai_endpoint`, `azure_openai_api_version`, `azure_openai_deployment`
  - `source_lang` (기본 `en`), `target_lang` (기본 `ko`)
  - `work_dir` (기본 `work`), `tm_db_path` (기본 `work/tm.sqlite`)
  - `glossary_path` (기본 `glossary.csv`)
  - `kr_font` (기본 `맑은 고딕`)
- `llm_model` 프로퍼티: deployment 가 있으면 `azure/<deployment>`, 아니면 `openai_model` 그대로.
- 모듈 import 직후 환경변수로 export (LiteLLM 이 읽도록).

## 2. PowerPoint COM 컨텍스트

- `powerpoint()`: `DispatchEx("PowerPoint.Application")` 로 새 프로세스. 종료 시 `app.Quit()`.
- `open_presentation(app, path, read_only)`: `Presentations.Open(WithWindow=False, ReadOnly=...)`. 종료 시 `pres.Close()`.
- 모든 COM 호출은 `pywintypes.com_error` 를 별도 catch.

## 3. Shape 분류 (제목/부제/본문)

`_shape_category(shape, slide_height_pt)` → `"title" | "subtitle" | "body" | ""`

판정 우선순위:
1. **Placeholder type** (`shape.Type == 14` 인 경우 `PlaceholderFormat.Type` 으로):
   - `13, 15` → title (ppPlaceholderTitle, CenterTitle)
   - `4` → subtitle
   - 그 외 placeholder → body
2. **Shape Name** 에 `"subtitle"` / `"title"` 포함.
3. **휴리스틱**:
   - `_shape_max_font_size` 가 ≥ 28pt 이고 슬라이드 상단 1/3 영역 → title
   - ≥ 20pt → subtitle

`_shape_max_font_size`: **빠른 단일 COM 호출**. `tf.TextRange.Font.Size` 한 번만 읽고, 혼합 폰트(0/None)면 0 반환. paragraph 순회 금지(성능).

## 4. EXTRACT (paragraph 단위)

### 4.1 트리 순회 (`_iter_text_frames`)

shape → `(text_frame, path_prefix, kind)` 튜플을 yield. **kind 는 `"tf"` (TextFrame) 또는 `"tf2"` (TextFrame2, SmartArt)**.

가드 순서 (필수 — 이거 빠지면 COM `Does not support a collection` 또는 hang):
1. `shape.Type == 6` (msoGroup) → `GroupItems` 재귀.
2. `getattr(shape, "HasSmartArt", 0) == -1` → `SmartArt.AllNodes.Item(i).TextFrame2` 순회. 빈 텍스트 노드 skip.
3. `shape.HasTable` → `Table.Cell(r,c).Shape.TextFrame` 순회. 셀 별로 `HasTextFrame & HasText` 가드.
4. 일반: `shape.HasTextFrame and shape.TextFrame.HasText`.

모든 collection 카운트는 try/except 로 0 fallback.

### 4.2 paragraph 추출 (`_extract_paragraphs`)

- `tr.Paragraphs(pi, 1)` 로 paragraph 객체 단건 획득.
- `clean = text.rstrip("\r\n\v")` 로 paragraph 끝 개행 제거.
- 빈 문자열 skip.
- LLM 전송용 텍스트는 `\v` (vertical tab, soft line break) 를 `_BR_MARKER = "⏎"` 로 치환.
- segment 스키마:
  ```json
  {
    "slide": 1,
    "path": [shape_idx, ..., "p", paragraph_idx],
    "text": "LLM 입력 텍스트 (⏎ 마커 포함)",
    "raw_text": "원본 텍스트 (\\v 그대로)",
    "kind": "tf" | "tf2",
    "category": "title" | "subtitle" | "body" | (생략),
    "runs_meta": [...],   // tf 만
    "bullet": {...}        // tf 만
  }
  ```

### 4.3 path 규약

| 종류 | path 형식 |
|---|---|
| 일반 shape paragraph | `[shape_idx, "p", pi]` |
| 그룹 내부 | `[shape_idx, child_idx, ..., "p", pi]` |
| 표 셀 | `[shape_idx, row, col, "p", pi]` |
| SmartArt 노드 | `[shape_idx, "smartart", node_idx, "p", pi]` |
| 슬라이드 노트 | `["notes", "p", pi]` |

### 4.4 run 메타 (`_para_runs_meta`)

paragraph 안의 각 run 에 대해:
- `start` (1-based char offset, paragraph 시작 기준)
- `length`
- `font` snapshot: `Bold, Italic, Underline, Size, Name, NameFarEast, ColorRGB`
- `hyperlink`: `(Address, SubAddress)` 튜플 (있을 때만)

### 4.5 bullet 메타 (`_para_bullet_meta`)

**중요**: 원본의 `Bullet.Visible` 값을 반드시 함께 저장. 없으면 0(없음) 으로 기본값.
- `bullet_visible` (-1=있음, 0=없음, -2=mixed)
- `bullet_type`, `bullet_char`, `bullet_size`, `indent_level`, `alignment`

### 4.6 노트 추출

`slide.HasNotesPage` 가드 후 `NotesPage.Shapes.Placeholders(2).TextFrame` 만 순회.

### 4.7 진행 출력

EXTRACT 시작 시 슬라이드 총수 출력, 슬라이드마다 `[i/N] 세그먼트 +X (누적 Y)` 1줄. (사용자가 멈춤 여부 판단 가능)

## 5. TRANSLATE

### 5.1 사전 처리

- `_sanitize_source`: `{'text': '...'}` 류 dict 조각 누적 제거 (이전 잘못된 번역 결과가 다음 입력에 섞여 들어가는 사태 방지).
- `_is_corrupted`: 응답에 dict 조각 포함 여부 검출.

### 5.2 TM (SQLite)

- 위치: `settings.tm_db_path` (기본 `work/tm.sqlite`).
- 스키마:
  ```sql
  CREATE TABLE tm (
    src_hash TEXT PRIMARY KEY,
    src TEXT NOT NULL,
    tgt TEXT NOT NULL,
    model TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  )
  ```
- `_hash`: `sha256(src.encode("utf-8")).hexdigest()`.
- 캐시 hit 이지만 오염된 경우(`_is_corrupted`) → 해당 row DELETE 후 재번역.

### 5.3 LLM 호출 프로토콜 (번호 블록)

**한 번 호출, 재시도 없음.**

입력 형식 (LLM 에 보내는 user 메시지):
```
=== 1 ===
First source paragraph
=== 2 ===
Second source paragraph
```

출력 형식 (LLM 응답):
```
=== 1 ===
첫 번째 번역
=== 2 ===
두 번째 번역
```

파서(`_parse_output_block`): `^===\s*(\d+)\s*===\s*$` 정규식. 기대 개수와 정확히 일치하지 않으면 `None` 반환 → `ValueError`.

`_BATCH = 5` (5개 paragraph 씩).

`_call_llm_block`:
- `litellm.completion(model=settings.llm_model, temperature=0, max_tokens=4096)`.
- 응답 파싱 실패 또는 오염 → `ValueError`. 호출자가 catch 후 원문 fallback (재번역 안 함).

### 5.4 프롬프트 규칙

system prompt 에 포함해야 할 항목 (순서 무관):
- 소스/타겟 언어, 입출력 포맷 명시.
- "Do NOT include English source. Do NOT add JSON, brackets, or commentary."
- `_BR_MARKER` 보존.
- 용어집 (`(protected)` 표시).
- 각 항목별 per-item rule:
  - **TITLE (sentence)**: `_looks_like_sentence(src)` true → "preserve sentence form, natural Korean. Keep punctuation."
  - **TITLE (noun)**: false → 명사구, ≤ N 한글 자(`min(max(src_len*1.0, 6), 20)`), 끝 부호 금지, 금지 어미 명시 (다/요/니다/합니다/입니다/하세요/되세요/하십시오/하기).
  - **SUBTITLE (sentence)**: src 가 sentence → 문장형 유지.
  - **SUBTITLE (noun)**: 짧게, 명사 어미 선호, 마침표 금지.
- title 노운프레이즈 변환 예제 4개 (Get started today → 지금 시작 등).

### 5.5 문장형 판정 (`_looks_like_sentence`)

다음 중 하나라도 true 면 sentence 로 분류:
1. 문장부호 `.,;:!?。，；：！？` 포함
2. 단어 6개 이상
3. 40자 이상
4. 단어 4개 이상 + 문장형 힌트 단어 (be/do/can/will/have/you/your/we/our/they/their/i'll/we'll/you'll/how to/what is/why/when/where/which/who/whose/let's/here's/there's/it's …)

### 5.6 후처리 (`_post_process`)

- category 가 title/subtitle 이고 src 가 sentence → 그대로(strip).
- category 가 title/subtitle 이고 src 가 noun → `_polish_title`:
  - 끝 어미 (`하세요/합니다/입니다/되세요/하십시오/하기/해요/예요/에요/...`) 제거. 최대 3회 반복.
  - 끝 문장부호 (`. ! ? 。 ！ ？`) 제거.
- 그 외 → 그대로.

### 5.7 진행 출력

배치 종료마다 `done/total` 출력.

## 6. APPLY

### 6.1 컨테이너 흐름

- 출력 경로 부모 디렉토리 mkdir.
- src ≠ out 이면 `shutil.copyfile(src, out)`.
- `powerpoint()` + `open_presentation(out, read_only=False)`.
- 슬라이드별로 segment 그룹화 → 각 항목에 대해 `_resolve_paragraph` 후 `_apply_paragraph_text`.
- 슬라이드 끝에 `pres.Save()`.

### 6.2 path 해석 (`_resolve_paragraph`)

`(text_frame, paragraph_index, kind)` 반환. 실패 시 `(None, None, None)`.

해석 순서:
1. `path[0] == "notes"` → notes TextFrame.
2. `path[0]` 정수 → `slide.Shapes(idx)`.
3. `shape.Type == 6` 이고 다음 path 가 정수 → `GroupItems(p)` 재귀.
4. `path[0] == "smartart"` → `shape.SmartArt.AllNodes.Item(ni).TextFrame2`, kind=`"tf2"`.
5. 표: `[r, c, "p", pi]` → `shape.Table.Cell(r, c).Shape.TextFrame`.
6. 일반: `["p", pi]` → `shape.TextFrame`.

### 6.3 paragraph 텍스트 치환 (`_apply_paragraph_text`)

#### 공통
- 입력 텍스트의 `_BR_MARKER` → `\v` 복원.

#### kind == `"tf2"` (SmartArt)
- `text_frame.TextRange.Paragraphs(idx, 1).Text = new_text` 만 수행.
- 한글 폰트 (`Name`, `NameFarEast`) 적용.

#### kind == `"tf"` (일반)
1. `tr.Paragraphs(para_index, 1)` 로 paragraph 객체.
2. `body_len = len(text.rstrip("\r\n\v"))`.
3. paragraph 시작 인덱스 `para_start` 계산: `1 + Σ(이전 paragraphs 의 raw text 길이)`.
4. `text_frame.TextRange.Characters(para_start, body_len).Text = new_text` ← **Characters() API 가 핵심**. paragraph 객체 자체에 `.Text =` 대입하면 단락 끝 \v 제거 등 부작용 발생.
5. 한글 폰트 일괄 적용 (Name + NameFarEast).
6. `runs_meta` 가 있으면 비례 복원:
   - `old_total = Σ runs_meta[i].length`.
   - 각 run 의 새 길이 = `round(new_len * (length / old_total))`. 마지막 run 은 잔여 전부.
   - 각 구간에 `_font_apply` (Bold/Italic/Underline/Size + 한글 폰트 + ColorRGB).
   - `hyperlink` 있으면 `ActionSettings(1).Hyperlink.Address/SubAddress` 복원.
7. **Bold 강제 후처리**: 첫 run 의 `Bold` 가 truthy 면 paragraph 전체에 `Font.Bold = True` 한 번 더. (`Characters().Font.Name` 일괄 적용으로 bold 가 reset 되는 PowerPoint COM 버그 회피)

### 6.4 bullet 적용 (`_apply_bullet`)

**중요**: 마스터 슬라이드 상속으로 bullet 이 자동 부착되는 것을 막아야 함.

- `bullet_visible == 0` (원본에 bullet 없음) → `Bullet.Visible = 0` + `Bullet.Type = 0 (ppBulletNone)` 명시. 다른 속성 적용 안 함.
- `bullet_visible == -1` 또는 `bullet_type` 존재 → 원본 속성 (`Type, Character, RelativeSize, Visible = -1`) 복원.
- `indent_level`, `alignment` 는 visible 과 무관하게 항상 복원.

### 6.5 폰트 축소 (`_shrink_font_if_needed`)

- 비율 `r = len(dst) / len(src)`.
- `r ≤ 1.3` 이면 변경 없음.
- 새 크기 = `max(cur / r, max(cur * 0.85, 10.0))`. 즉 **하한은 원본의 85% 또는 절대 10pt 중 큰 값**. 이미 작은 글자는 거의 안 줄어듦.
- 변화가 0.5pt 미만이면 적용 안 함.
- 이 함수는 `kind == "tf"` 인 경우에만 호출.

### 6.6 슬라이드 종료 처리

- 이번에 텍스트가 바뀐 shape 들 (`touched_shape_idx`) 의 `TextFrame.WordWrap = True` 만 보장.
- **AutoSize 변경 금지**, **shape Width 변경 금지** (둘 다 디자인 깨짐 발생).

## 7. VERIFY

`verify_and_fix(pptx_path, work, max_passes=1)`:
- pptx 다시 EXTRACT.
- `_is_mostly_english(text)` 인 segment 만 추려서 TM 캐시 DELETE 후 재번역.
- `_is_mostly_english`: 길이 ≥ 3, latin word 존재, hangul 수 < latin 수, latin 비율 ≥ 0.3.
- 결과를 동일 pptx 에 다시 apply.

## 8. CLI (typer)

명령:
- `run PPTX [--output PATH] [--no-move-done] [--no-verify]`
  - PPTX 가 디렉토리면 안의 모든 `.pptx/.ppt` (단, `~$` 시작 파일 제외) 순차 처리.
  - 출력 경로 미지정 시: 입력이 `input/` 안이면 `../output/<stem>_KO.pptx`, 아니면 입력 옆.
- `extract PPTX [--out PATH]`
- `translate SEGMENTS_PATH [--out PATH]`
- `apply PPTX TRANSLATED_PATH [--out PATH]`
- `tm import CSV_PATH` — `source,target` CSV 적재
- `tm clean` — 오염된 row 일괄 삭제

배치 모드:
- 한 파일 실패해도 다음 파일 계속 진행.
- 종료 시 성공/실패 카운트 + 실패 파일 목록 출력.
- 성공한 파일은 `input/done/` 으로 즉시 이동 (`--no-move-done` 으로 비활성화). 동일 이름 충돌 시 mtime 접미사.

## 9. 비결정성/멀티스레드

- 단일 프로세스, 단일 스레드. PowerPoint COM 은 STA — 멀티스레드 금지.
- `temperature=0`, TM hit 우선 → 동일 입력에 동일 출력 보장.

## 10. 테스트 체크리스트 (수동)

- [ ] 빈 placeholder 슬라이드 (텍스트 없음)
- [ ] 그룹화된 도형
- [ ] 표 (병합 셀 포함)
- [ ] SmartArt
- [ ] 노트
- [ ] 하이퍼링크 포함 run
- [ ] Bold 강조 단어가 paragraph 중간에 있는 경우
- [ ] 마스터에 bullet 정의된 layout 에 일반 텍스트 box 가 놓인 슬라이드 (bullet 자동 부착 회귀 검증)
- [ ] 매우 긴 영문 본문 (한국어로 1.3배 이상 길어지는 경우 폰트 축소 작동)
- [ ] 이미 9pt 이하 작은 글자 (축소되지 않는지 확인)
- [ ] 제목이 명사구 (`Modern Apps`)
- [ ] 제목이 의문문/sentence (`How can you migrate?`)
- [ ] 슬라이드 100장 이상 (성능)
- [ ] 동일 PPTX 재실행 (TM hit 시 LLM 호출 0)
