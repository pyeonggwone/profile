# Document Model 설계

## 목적

PDF reader가 읽은 원본 구조와 웹 편집으로 발생한 변경분을 함께 보존하는 내부 모델을 설계한다. 목표는 원본 무손실, 변경 추적, incremental write를 동시에 만족하는 것이다.

## 기준 기술

| 영역 | 기술 | 기준 버전 |
|---|---|---:|
| 구현 언어 | Rust | `1.78+` |
| 직렬화 | `serde` | `1.0.x` |
| 임시 metadata 저장 | JSON 또는 SQLite | SQLite `3.45+` optional |

## 모델 계층

내부 모델은 세 계층으로 나눈다.

```text
RawPdf
  원본 bytes, byte ranges, xref revisions

ParsedPdf
  object map, trailer chain, catalog, page tree, resources

EditableDocument
  page model, edit operations, generated objects, dirty set
```

## RawPdf

원본 보존을 담당한다.

보관 항목은 다음과 같다.

- 전체 원본 bytes 경로 또는 memory map handle
- PDF header offset
- EOF marker offset
- xref section 목록
- object별 byte range
- stream별 raw byte range
- incremental revision chain

RawPdf는 저장 시 편집하지 않은 객체를 원본 그대로 복사하거나 참조하기 위한 근거가 된다.

## ParsedPdf

파싱된 PDF object graph를 담당한다.

주요 항목은 다음과 같다.

- object id와 generation을 key로 하는 object map
- trailer dictionary chain
- catalog reference
- page tree node
- resource dictionary inheritance 결과
- font/image/form XObject reference index
- decoded stream cache handle

ParsedPdf는 모든 object를 완벽히 의미 분석하지 않아도 된다. 알 수 없는 object는 `UnknownObject`로 유지한다.

## EditableDocument

웹 UI에서 발생한 변경을 PDF 구조로 변환하기 전 단계의 모델이다.

편집 operation 예시는 다음과 같다.

- `AddText`
- `AddImage`
- `AddAnnotation`
- `ReplaceTextLogical`
- `DeleteAnnotation`
- `SetMetadata`
- `RotatePage`

각 operation은 다음 정보를 가진다.

- operation id
- 대상 page
- 좌표계
- 입력 값
- 생성해야 할 PDF object 후보
- 원본 object를 dirty로 만들지 여부

## 좌표계

내부 좌표계는 PDF user space를 기준으로 한다.

- 원점은 PDF page의 lower-left다.
- 웹 Canvas 좌표는 upper-left 기준이므로 변환 layer가 필요하다.
- page rotation, crop box, user unit을 반영한다.

좌표 변환은 다음 순서로 처리한다.

```text
Canvas point
-> viewport scale 제거
-> y축 반전
-> page rotation 역변환
-> crop/media box offset 보정
-> PDF user space point
```

## 변경 추적

Dirty tracking은 object 단위와 semantic operation 단위로 모두 관리한다.

```text
DirtySet {
  modified_objects,
  new_objects,
  deleted_logical_entities,
  preserved_objects
}
```

원칙은 다음과 같다.

- 원본 object를 직접 수정하지 않는다.
- 기존 page content를 바꾸어야 하면 새 content stream을 추가하고 page dictionary를 새 revision으로 쓴다.
- 기존 annotation을 삭제해야 하면 page의 `/Annots` 배열을 새 revision으로 쓴다.
- 삭제 대상 원본 object bytes는 파일에서 제거하지 않는다.

## 객체 번호 할당

새 object number는 기존 `/Size` 이후부터 할당한다.

```text
next_object_number = max(existing_object_number) + 1
```

object stream 내부 object도 번호 충돌에 포함한다.

## 캐시 설계

decoded stream과 page render plan은 비용이 크므로 cache한다.

캐시 key는 다음을 포함한다.

- document id
- object id/generation
- stream filter hash
- edit revision id
- render scale 또는 page viewport option

원본 bytes 자체를 cache에 중복 저장하지 않는다.

## 완료 기준

- 원본 byte range와 parsed object가 연결되어 있다.
- 편집 operation이 PDF object 변경으로 변환될 준비가 되어 있다.
- dirty object와 preserved object가 명확히 구분된다.
- writer가 incremental update를 만들 수 있는 enough metadata를 제공한다.