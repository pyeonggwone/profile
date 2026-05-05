# PDF Reader 설계

## 목적

PDF 파일을 직접 읽어 document model을 만들기 위한 parser를 설계한다. 목표는 원본 bytes를 최대한 보존하면서 필요한 구조만 정확히 해석하는 것이다.

## 기준 기술

| 영역 | 기술 | 기준 버전 |
|---|---|---:|
| 구현 언어 | Rust | `1.78+` |
| 입력 모델 | `&[u8]`, memory mapped file optional | Rust std 기준 |
| 파서 방식 | 직접 구현 recursive descent + byte scanner | PDF 전용 |
| 오류 모델 | typed error enum | `thiserror 1.0.x` 사용 가능 |

## Reader가 처리할 PDF 구조

처리 순서는 다음과 같다.

```text
1. Header 탐색
2. EOF marker 탐색
3. startxref 탐색
4. xref table 또는 xref stream 판별
5. trailer dictionary 해석
6. Root, Info, Encrypt, ID 참조 해석
7. indirect object index 생성
8. object stream이 있으면 내부 object index 확장
9. page tree 탐색
10. stream dictionary와 content stream metadata 수집
```

## Header와 version 처리

PDF header는 파일 맨 앞에만 있다고 가정하지 않는다. 일부 파일은 앞에 binary garbage나 transport wrapper가 붙을 수 있다.

구현 로직은 다음과 같다.

- 파일 시작 후 제한된 범위에서 `%PDF-` signature를 찾는다.
- version은 `1.0`부터 `2.0`까지 문자열로 보존한다.
- 실제 feature 사용 여부는 header version만으로 판단하지 않고 catalog와 object 구조를 함께 본다.

## startxref 탐색

파일 끝에서 역방향으로 `%%EOF`와 `startxref`를 찾는다.

- 마지막 `%%EOF`를 우선한다.
- `startxref` 값은 byte offset으로 해석한다.
- offset이 깨졌으면 주변 byte window에서 `xref` 또는 xref stream object를 복구 탐색한다.
- 복구 탐색 결과는 document warning에 기록한다.

## xref table 파싱

전통적인 xref table은 다음을 읽는다.

```text
xref
0 3
0000000000 65535 f
0000000017 00000 n
0000000081 00000 n
trailer
<< /Size 3 /Root 1 0 R >>
```

구현 포인트는 다음과 같다.

- subsection 시작 번호와 count를 검증한다.
- entry offset, generation, in-use/free flag를 저장한다.
- 같은 object number가 여러 번 나오면 마지막 revision을 활성으로 본다.
- 이전 revision은 incremental chain 분석에 사용한다.

## xref stream 파싱

PDF 1.5+의 xref stream은 일반 stream object처럼 읽은 뒤 `/W`, `/Index`, `/Size`를 해석한다.

필요 로직은 다음과 같다.

- xref stream object dictionary 파싱
- stream bytes 추출
- filter chain으로 decode
- `/W` 배열에 따라 type, field1, field2를 읽음
- type `0`, `1`, `2`를 각각 free, normal, compressed object로 매핑

## indirect object 파싱

기본 grammar는 다음을 지원한다.

- null
- boolean
- integer, real number
- name object
- literal string
- hex string
- array
- dictionary
- stream
- indirect reference

object 파싱 결과는 의미 모델과 원본 byte range를 모두 가진다.

```text
ParsedObject {
  object_id,
  generation,
  value,
  byte_range,
  raw_slice_reference,
  parse_warnings
}
```

## stream 처리

stream은 dictionary와 raw body를 분리한다.

주의할 점은 다음과 같다.

- `/Length`가 indirect reference일 수 있다.
- `stream` keyword 뒤 EOL 처리는 `\r`, `\n`, `\r\n` 모두 허용한다.
- `endstream` 탐색은 `/Length` 우선, 실패 시 keyword scan fallback을 사용한다.
- stream decode는 reader가 직접 하지 않고 `pdf_filters`에 위임한다.

## page tree 탐색

Catalog의 `/Pages`에서 시작해 `/Kids`를 순회한다.

- `/Type /Pages` 노드는 inherited attributes를 전달한다.
- `/Type /Page` 노드는 media box, crop box, resources, contents를 수집한다.
- 순환 참조를 방지하기 위해 visited set을 둔다.
- page count가 `/Count`와 다르면 warning으로 기록한다.

## 오류와 복구

Reader는 가능한 경우 partial parse를 반환한다.

| 오류 | 처리 |
|---|---|
| Header 없음 | fatal |
| startxref 깨짐 | 복구 scan 시도 |
| 일부 object 파싱 실패 | object를 raw-preserved unknown으로 기록 |
| stream length 불일치 | fallback scan 후 warning |
| 모르는 filter | raw stream 보존 |

## 완료 기준

- xref table과 xref stream을 모두 인식한다.
- object stream 내부 compressed object를 index에 반영한다.
- page tree와 content stream 참조를 수집한다.
- 편집하지 않은 객체를 재사용할 수 있도록 원본 byte range를 보존한다.