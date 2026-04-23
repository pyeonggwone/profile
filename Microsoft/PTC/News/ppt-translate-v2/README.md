# ppt-translate

PPTX 영문→한국어 in-place 번역 파이프라인 (OOXML 직접 조작, 컨테이너 친화).

## 설계 원칙

- **OOXML 직접 조작**: `python-pptx` / PowerPoint COM 미사용. `lxml` 로 ZIP 내부 XML 직접 처리
- **In-place 치환**: 원본 PPTX 의 `<a:t>` 텍스트만 교체. SmartArt/차트/애니메이션/마스터 100% 보존
- **단일 백엔드**: 엔진 분기 없음. Linux 컨테이너 1개로 모든 환경 통합
- **Translation Memory**: SQLite 기반, 동일 문장 재번역 안 함
- **순수 함수 파이프라인**: 각 STEP = `(input_path) → output_path`

## 파이프라인

```
EXTRACT  → slide{N}.xml 의 <a:t> 만 모아 work/segments.json
TRANSLATE → TM 조회 → 미스만 LLM 배치 호출 → work/translated.json
APPLY    → 원본 PPTX 복사 → 동일 path 의 <a:t> 텍스트만 교체 → output.pptx
```

## 빠른 시작

### 로컬

```bash
uv sync
cp .env.example .env  # OPENAI_API_KEY 입력
uv run ppt-translate run input.pptx
```

### Docker

```bash
docker build -t ppt-translate .
docker run --rm -v "$PWD:/work" --env-file .env ppt-translate run input.pptx
```

## CLI

| 명령 | 설명 |
|------|------|
| `ppt-translate run <file.pptx>` | 전체 파이프라인 실행 |
| `ppt-translate extract <file.pptx>` | EXTRACT 만 |
| `ppt-translate translate <segments.json>` | TRANSLATE 만 |
| `ppt-translate apply <file.pptx> <translated.json>` | APPLY 만 |
| `ppt-translate tm import <file.csv>` | TM 가져오기 |
| `ppt-translate diff <a.pptx> <b.pptx>` | 텍스트 변경분 표시 |

자세한 내용은 [docs/](docs/) 참고.
