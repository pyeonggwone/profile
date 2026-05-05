# TODO

## MVP 1. EPUB 완전 구현 대상

- EPUB native adapter를 `epup-translate-v3` 수준으로 유지한다.
- ZIP 구조, `mimetype`, `META-INF/container.xml`, OPF, XHTML spine 구조를 보존한다.
- XHTML text node만 번역한다.
- 이미지, 폰트, CSS, script/style/code/pre/svg/math 영역은 보존한다.
- OPF `dc:language`를 target language로 갱신한다.
- XHTML `html lang`, `xml:lang`을 target language로 갱신한다.
- `output/{stem}_{TARGET}.epub` 파일을 생성한다.
- 성공한 원본 EPUB은 `input/done/`으로 이동한다.
- DRM EPUB은 번역하지 않고 metadata JSON에 `skipped`로 기록한다.
- placeholder 검증 실패 시 해당 segment는 원문 fallback한다.
- LLM 실패 시 batch 단위 원문 fallback한다.
- 작은 DRM 없는 EPUB fixture로 output 열림을 검증한다.
- v3와 동일한 입력 EPUB에 대해 v5 output 구조가 EPUB reader에서 열리는지 확인한다.

## MVP 1. AZW3/MOBI/KFX 감지와 상태 기록

- `.azw3`, `.mobi`, `.kfx` 확장자를 input scan 대상에 포함한다.
- 확장자와 내부 signature가 불일치하면 warning을 기록한다.
- AZW3/MOBI는 PalmDB header와 MOBI signature를 확인한다.
- KFX는 `CONTBOUNDARY`, `KFX`, `kindle` 등 signature hint를 확인한다.
- EPUB이 아닌 포맷은 현재 단계에서 번역하지 않는다.
- EPUB이 아닌 포맷은 `ebook-metadata/{stem}.json`에 `skipped` 상태로 기록한다.
- metadata에는 `format`, `status`, `reason`, `mvpStage`, `confidence`, `warnings`를 포함한다.
- DRM 또는 암호화 의심 파일은 처리하지 않고 skip reason을 기록한다.
- adapter interface는 추후 reader/writer 분리 구현이 가능하도록 유지한다.

## MVP 2. AZW3 제한적 텍스트 추출

- Calibre의 AZW3 처리 방식과 KindleUnpack 구조를 참고한다.
- 외부 도구를 그대로 black box로 의존할지, 참고 구현으로 내부 parser를 작성할지 결정한다.
- PalmDB record table을 안정적으로 파싱한다.
- MOBI header, KF8 boundary, EXTH metadata를 읽는다.
- DRM/암호화 여부를 더 정확히 판정한다.
- KF8 HTML payload 후보 record를 식별한다.
- 압축되지 않은 또는 단순 압축 payload부터 제한적으로 텍스트를 추출한다.
- 추출한 HTML fragment에서 번역 가능한 text node를 segment로 만든다.
- MVP 2에서는 writer 완성보다 추출 정확도와 metadata 기록을 우선한다.
- 출력 생성이 어렵다면 `metadata-only` 결과와 제한사항을 기록한다.
- 샘플 AZW3별로 추출된 segment 수, 실패 record 수, 미지원 압축 방식을 기록한다.

## MVP 3. MOBI 제한적 텍스트 추출 및 재패키징 검토

- PalmDOC/MOBI header를 파싱한다.
- record offset table과 text record 범위를 계산한다.
- text encoding과 압축 방식을 확인한다.
- 비압축 또는 단순 PalmDOC 압축 MOBI를 우선 대상으로 둔다.
- HUFF/CDIC 등 복잡한 압축은 별도 제한사항으로 기록한다.
- text stream에서 HTML 또는 markup 후보를 추출한다.
- 추출한 text stream을 segment로 변환한다.
- 번역 후 record 길이 변화가 offset table에 미치는 영향을 분석한다.
- 재패키징 시 record 재분할 정책을 설계한다.
- EXTH metadata 보존과 language 갱신 가능성을 검토한다.
- MVP 3 완료 전까지는 원본 MOBI를 손상시킬 수 있는 writer를 기본 활성화하지 않는다.
- 샘플 MOBI별 output 생성 가능 여부를 metadata에 기록한다.

## MVP 4. KFX 검증 중심 처리

- KFX는 native writer 완성보다 검증과 분석을 우선한다.
- Calibre KFX 관련 plugin 동작 범위를 조사한다.
- Kindle Previewer를 output 검증 도구로 사용할 수 있는지 확인한다.
- KFX container signature와 fragment boundary를 더 정확히 감지한다.
- metadata fragment와 text fragment 후보를 구분한다.
- enhanced typesetting 정보 보존 가능성을 검토한다.
- 위치 정보, checksum, fragment index 갱신 필요성을 조사한다.
- 처리 불가 variant는 명확한 skip reason으로 기록한다.
- 가능한 샘플은 분석 metadata를 생성하고, output 생성은 별도 feature flag 뒤에 둔다.
- Kindle Previewer 또는 Calibre 기반 검증 결과를 `ebook-metadata/`에 남기는 schema를 추가한다.

## 공통 Translation Engine 개선

- LLM token usage를 응답에서 수집해 metadata에 기록한다. (완료: API usage 제공 시 합산)
- batch별 input/output token을 책 단위로 합산한다. (완료: input/output/total token 기록)
- Translation Memory hit/miss 수를 metadata에 기록한다. (완료)
- protected glossary term 검증을 강화한다.
- placeholder 누락, 중복, 순서 변경을 별도 warning code로 기록한다.
- segment 단위 retry 정책을 추가한다.
- 문단 단위/문장 단위 segment 분리 옵션을 추가한다.

## Validation

- EPUB output을 다시 열어 OPF와 XHTML이 존재하는지 확인한다.
- EPUBCheck 연동을 검토한다.
- AZW3/MOBI는 Calibre ebook-viewer 또는 Kindle Previewer 검증 가능성을 확인한다.
- KFX는 Kindle Previewer 검증 중심으로 관리한다.
- DRM 없는 작은 fixture를 포맷별로 준비한다.
- 저작권 있는 실제 도서는 repository에 넣지 않는다.
- 큰 샘플은 checksum만 문서화한다.

## CLI

- `--format epub|azw3|mobi|kfx` 옵션을 유지한다.
- `--metadata-only` 옵션을 추가한다.
- `--dry-run` 옵션을 추가한다.
- `--debug` 옵션을 추가한다.
- 특정 파일 하나만 처리하는 `--input-file` 옵션을 검토한다.
- output 검증만 수행하는 `--validate` 옵션을 검토한다.