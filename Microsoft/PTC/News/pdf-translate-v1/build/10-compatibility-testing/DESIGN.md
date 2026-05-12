# Compatibility Testing 설계

## 목적

PDF 읽기, 쓰기, 라운드트립, Incremental Update가 실제 PDF 파일에서 안정적으로 동작하는지 검증하는 테스트 전략을 설계한다.

## 기준 기술

| 영역 | 기술 | 기준 버전 |
|---|---|---:|
| Rust test | `cargo test` | Rust `1.78+` |
| Snapshot | `insta` optional | `1.39+` 기준 |
| CLI 검증 | 자체 `cli_tools` | workspace 내부 |
| Frontend test | Playwright | `1.44+` 기준 |
| Browser | Microsoft Edge/Chromium | stable 기준 |

## 테스트 계층

```text
Unit test
  primitive parser, filter, writer function

Fixture test
  실제 PDF 샘플을 reader로 분석

Roundtrip test
  읽기 -> 변경 없음 저장 -> 다시 읽기

Incremental test
  편집 operation -> append 저장 -> 다시 읽기

Viewer test
  render plan -> Canvas 표시 검증
```

## Fixture 분류

PDF fixture는 기능별로 분류한다.

| 분류 | 포함할 샘플 |
|---|---|
| basic | PDF 1.0~1.4, xref table, 단순 page |
| xref-stream | PDF 1.5+, xref stream |
| object-stream | compressed object stream 포함 |
| filters | Flate, DCT, JPX, LZW, RLE, ASCII85, Hex |
| fonts | Type1, TrueType, Type0, ToUnicode |
| images | JPEG, JPEG2000, image mask, soft mask |
| annotations | Text, Link, Highlight, Widget |
| incremental | 이미 incremental update가 있는 PDF |
| encrypted | 암호화 PDF, 지원 단계에 따라 expected failure |
| malformed | offset 오류, length 불일치, EOF 이상 |

공개 가능한 작은 fixture만 repository에 넣고, 큰 파일은 외부 artifact로 관리한다.

## Reader 테스트

Reader 테스트는 다음을 확인한다.

- header version 인식
- startxref offset 검증
- xref entry count
- trailer `/Root` 확인
- page count
- object stream 내부 object index
- stream dictionary와 raw byte range
- warning 발생 여부

## Filter 테스트

Filter 테스트는 known input/output vector로 검증한다.

- ASCIIHex odd nibble
- ASCII85 `z` shortcut
- RunLength EOD
- LZW clear code, early change
- Flate predictor
- CCITT 기본 black/white run

OSS adapter는 library version을 test log에 기록한다.

## Writer 테스트

Writer 테스트는 byte-level 검증과 semantic 검증을 나눈다.

byte-level 검증은 다음을 확인한다.

- object header 형식
- stream `/Length`
- xref offset 10자리 zero padding
- trailer `/Size`
- `startxref` 위치

semantic 검증은 writer 결과를 자체 reader로 다시 읽어 확인한다.

## Roundtrip 테스트

변경 없는 저장은 두 모드로 나눈다.

| 모드 | 기대값 |
|---|---|
| no-write | reader만 실행, 원본 bytes 그대로 |
| rewrite-minimal | writer가 새 파일 생성, 의미적 동일성 확인 |

기본 제품 흐름은 incremental update이므로 “편집하지 않았으면 다운로드를 만들지 않거나 원본을 그대로 반환”하는 정책을 우선한다.

## Incremental Update 테스트

편집 operation별로 다음을 확인한다.

1. 원본 prefix가 byte-for-byte 동일한지 확인한다.
2. 새 object가 원본 뒤에 추가됐는지 확인한다.
3. 새 xref가 새 object offset을 가리키는지 확인한다.
4. trailer `/Prev`가 이전 xref를 가리키는지 확인한다.
5. 다시 읽었을 때 page count가 유지되는지 확인한다.
6. 변경 operation이 page model에 반영되는지 확인한다.

## Viewer 테스트

Playwright로 다음을 확인한다.

- 업로드 버튼 동작
- page canvas가 비어 있지 않은지 pixel check
- zoom 변경 후 canvas 크기와 text overlay 위치 유지
- text 추가 후 overlay 표시
- 다운로드 요청 발생

브라우저 테스트는 PDF 엔진 정확도보다 UI 연동과 표시 실패 방지에 초점을 둔다.

## 완료 기준

- core parser/filter/writer unit test가 있다.
- fixture 기반 reader test가 있다.
- incremental update 후 자체 reader로 재검증한다.
- viewer canvas nonblank 테스트가 있다.
- 알려진 미지원 기능은 expected failure로 명시한다.