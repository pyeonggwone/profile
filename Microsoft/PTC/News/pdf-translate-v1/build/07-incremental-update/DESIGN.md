# Incremental Update 설계

## 목적

원본 PDF를 손상시키지 않고 편집 결과를 저장하는 append-only 저장 방식을 설계한다. 이 기능은 README의 “모르는 부분은 건드리지 말고 그대로 유지” 원칙을 구현하는 핵심이다.

## 기준 기술

| 영역 | 기술 | 기준 버전 |
|---|---|---:|
| 구현 언어 | Rust | `1.78+` |
| Writer | 자체 `pdf_writer` | 같은 workspace |
| 압축 | zlib | `1.3.1` |

## 기본 구조

Incremental Update 결과는 다음 구조를 가진다.

```text
[원본 PDF 전체 bytes]
[새 object 또는 수정된 object의 새 generation/revision]
[새 xref table]
[새 trailer, /Prev는 이전 xref offset]
startxref
[새 xref offset]
%%EOF
```

원본 bytes는 그대로 유지한다. 기존 object를 삭제하거나 재배치하지 않는다.

## 저장 원칙

- 변경되지 않은 object는 새로 쓰지 않는다.
- 변경된 object는 같은 object number와 generation으로 새 revision을 쓴다.
- 새 object는 기존 max object number 이후 번호를 사용한다.
- 기존 xref chain은 `/Prev`로 연결한다.
- 기존 `/Root`, `/Info`, `/Encrypt`, `/ID`는 필요한 경우만 새 trailer에서 갱신한다.

## Page에 content 추가하기

텍스트를 추가하는 경우 기존 content stream을 직접 수정하지 않는다.

```text
기존 page object
  /Contents 20 0 R

새 content stream
  101 0 obj << /Length ... /Filter /FlateDecode >> stream ... endstream endobj

새 page object revision
  기존 page dictionary 복사
  /Contents [20 0 R 101 0 R]
```

이 방식은 기존 content stream을 보존하면서 새 표시 내용을 뒤에 추가한다.

## Annotation 추가하기

주석 추가는 새 annotation object와 page dictionary revision으로 처리한다.

```text
102 0 obj
<< /Type /Annot /Subtype /Text /Rect [...] /Contents (...) >>
endobj

새 page object revision
  /Annots [기존 annots... 102 0 R]
```

## Metadata 변경

metadata 변경은 `/Info` dictionary 또는 XMP metadata stream을 새 object로 작성한다.

원칙은 다음과 같다.

- 기존 metadata object는 제거하지 않는다.
- trailer의 `/Info`가 새 object를 가리키게 한다.
- XMP stream은 새 stream object를 만들고 catalog의 `/Metadata`를 새 reference로 갱신한다.

## 암호화 PDF

암호화 PDF는 초기 구현에서 별도 단계로 둔다.

지원할 때는 다음 원칙을 따른다.

- 기존 `/Encrypt` dictionary를 유지한다.
- 새로 쓰는 string과 stream은 해당 object key로 암호화한다.
- trailer의 `/Encrypt` reference는 유지한다.
- 권한 bit에 따라 편집/저장 가능 여부를 확인한다.

암호화 처리가 완료되지 않은 단계에서는 읽기 분석만 허용하고 다운로드 저장은 명시 오류로 막는다.

## Linearized PDF 영향

Linearized PDF에 incremental update를 추가하면 선형화 최적화는 사실상 최신 상태가 아닐 수 있다. 하지만 PDF 표준 viewer는 마지막 xref를 따라가므로 문서는 열려야 한다.

처리 방침은 다음과 같다.

- 원본 linearization dictionary는 보존한다.
- 저장 후 `linearized=false` warning을 metadata에 표시한다.
- 향후 전체 rewrite + relinerization은 별도 기능으로 둔다.

## 검증 로직

저장 직후 다음을 자체 검증한다.

1. 새 `startxref` 위치가 새 xref 시작 offset과 일치하는지 확인한다.
2. 새 trailer의 `/Prev`가 이전 xref offset을 가리키는지 확인한다.
3. 새 xref entry offset으로 object header를 읽을 수 있는지 확인한다.
4. `/Size`가 모든 object number를 포함하는지 확인한다.
5. reader로 다시 열어 page count와 변경 operation 결과를 확인한다.

## 완료 기준

- 원본 bytes 뒤에만 변경분을 추가한다.
- 변경하지 않은 object는 byte-for-byte로 보존된다.
- 새 xref/trailer chain이 PDF reader에서 다시 읽힌다.
- 편집 후 다운로드 PDF가 표준 viewer에서 열린다.