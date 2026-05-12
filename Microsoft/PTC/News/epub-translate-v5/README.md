# epub-translate-v5

`epup-translate-v3`의 구현 방식을 기준으로 새로 만든 EPUB-first 전자책 번역 프로젝트다.

## 기준

- `epup-translate-v3`는 수정하지 않는다.
- 실행 방식은 `epup-translate-v3`처럼 Linux/bash + Node.js 20+ 기준으로 둔다.
- EPUB은 완전 구현 대상이다.
- AZW3/MOBI/KFX는 단계별 MVP로 확장한다.
- 고급 포맷 확장 작업은 `TODO.md`에 상세히 추적한다.

## 구현 상태

| MVP | 포맷 | 현재 상태 |
|---|---|---|
| MVP 1 | EPUB | native adapter 직접 구현. v3 방식의 EPUB 번역 경로 이식 |
| MVP 1 | MOBI/KFX | 감지, 지원 상태 기록, metadata JSON 생성 |
| MVP 2 | AZW3 | Calibre `ebook-convert`로 EPUB 변환 후 기존 EPUB 번역 경로 재사용 |
| MVP 3 | MOBI | TODO 대상. 제한적 텍스트 추출 및 재패키징 검토 |
| MVP 4 | KFX | TODO 대상. Calibre plugin/Kindle Previewer 연동 중심 검증 |

## 실행

```bash
chmod +x run-translate.sh
cp .env.example .env
vi .env
./run-translate.sh
```

## 입력과 출력

```text
input/book.epub  -> output/book_KR.epub
input/book.azw3  -> output/book_KR.epub (Calibre ebook-convert 필요)
input/book.mobi  -> ebook-metadata/book.json (MVP 1 status only)
input/book.kfx   -> ebook-metadata/book.json (MVP 1 status only)
```

## 디렉터리

```text
epub-translate-v5/
├── run-translate.sh
├── package.json
├── .env.example
├── glossary.csv
├── TODO.md
├── INSTALL.md
├── src/
│   ├── index.mjs
│   ├── pipeline.mjs
│   ├── epub/
│   ├── formats/
│   ├── translate/
│   └── util/
├── input/
├── output/
├── work/
└── ebook-metadata/
```

## EPUB 처리

- EPUB ZIP 로드
- `META-INF/container.xml` 읽기
- OPF spine 기반 XHTML chapter 탐색
- XHTML text node만 추출
- `script`, `style`, `code`, `pre`, `svg`, `math` 등 제외
- glossary protected term placeholder 처리
- SQLite Translation Memory 사용
- OpenAI 또는 Azure OpenAI batch 번역
- 책 단위 원문 단어 수, Translation Memory hit/miss, LLM input/output/total token metadata 기록
- OPF `dc:language`와 XHTML `html lang`, `xml:lang` 갱신
- `mimetype` 첫 엔트리 및 STORE 압축 유지
- 성공한 원본은 `input/done/`으로 이동

## AZW3 처리

AZW3는 Calibre CLI의 `ebook-convert`를 사용해 임시 EPUB으로 변환한 뒤, 기존 EPUB 번역 파이프라인을 그대로 사용한다.

- `ebook-convert`가 PATH에 있으면 자동 사용
- PATH에 없으면 `EBOOK_CONVERT_PATH` 또는 `CALIBRE_EBOOK_CONVERT`에 실행 파일 경로 지정
- 출력은 `output/{stem}_{TARGET}.epub`
- 성공한 원본 AZW3는 `input/done/`으로 이동
- DRM 또는 Calibre가 처리하지 못하는 AZW3는 실패 metadata에 reason 기록

## MOBI/KFX 처리

현재 구현은 MVP 1 범위다.

- 확장자 기반 후보 감지
- EPUB ZIP signature 확인
- AZW3/MOBI PalmDB/MOBI signature 확인
- KFX signature hint 확인
- MOBI/KFX는 번역하지 않고 `ebook-metadata/`에 skip 상태 기록

## 제외 범위

- DRM 우회 또는 제거
- MOBI/KFX EPUB 변환 기반으로 native adapter 요구사항 대체
- AZW3/MOBI/KFX writer 즉시 완성
- `epup-translate-v3` 수정