# PDF Writer 설계

## 목적

웹 편집 결과나 새 문서 생성을 PDF bytes로 직렬화하는 writer를 설계한다. 기본 저장 방식은 `07-incremental-update`에서 정의하지만, 이 문서는 object와 stream을 어떻게 PDF 문법으로 쓰는지에 집중한다.

## 기준 기술

| 영역 | 기술 | 기준 버전 |
|---|---|---:|
| 구현 언어 | Rust | `1.78+` |
| 압축 | zlib | `1.3.1` |
| JPEG encode | libjpeg-turbo | `3.0.x` |
| byte buffer | Rust std `Vec<u8>`/`Write` trait | 표준 |

## Writer 책임

Writer는 다음을 수행한다.

- PDF primitive 직렬화
- indirect object 직렬화
- stream dictionary와 stream body 작성
- content stream 생성
- image XObject 생성
- font resource reference 생성
- xref table 또는 xref stream 작성
- trailer 작성

## PDF primitive 직렬화

지원 primitive는 reader와 대칭이어야 한다.

| Primitive | 직렬화 방식 |
|---|---|
| null | `null` |
| boolean | `true`, `false` |
| integer/real | PDF number grammar에 맞춰 출력 |
| name | `/Name` 형태, 특수 문자는 `#XX` escape |
| literal string | 괄호 escape 처리 |
| hex string | `<...>` |
| array | `[ item item ]` |
| dictionary | `<< /Key value >>` |
| indirect reference | `1 0 R` |
| stream | dictionary + `stream` + bytes + `endstream` |

## Object 직렬화

기본 형식은 다음과 같다.

```text
12 0 obj
<< /Type /Example >>
endobj
```

Writer는 각 object의 시작 offset을 기록한다. 이 offset은 xref 작성에 사용한다.

## Stream 작성

stream 작성 순서는 다음과 같다.

```text
1. logical stream bytes 생성
2. filter policy 결정
3. encode 수행
4. `/Length` 확정
5. stream dictionary 직렬화
6. stream body 출력
```

초기 policy는 다음과 같다.

- 새 content stream은 `FlateDecode`로 압축한다.
- 새 JPEG 이미지는 `DCTDecode`를 사용한다.
- 작은 metadata stream은 압축하지 않을 수 있다.
- 기존 stream은 편집하지 않았으면 원본을 그대로 둔다.

## Content stream 생성

텍스트 추가 operation은 PDF graphics/text operator로 변환한다.

예시는 다음과 같다.

```text
q
BT
/F1 12 Tf
1 0 0 1 120 240 Tm
(Sample) Tj
ET
Q
```

구현 로직은 다음을 포함한다.

- graphics state save/restore를 항상 감싼다.
- text object `BT`/`ET` 범위를 명확히 둔다.
- 문자열 escape와 font encoding을 적용한다.
- 좌표는 PDF user space 기준으로 쓴다.
- 기존 content stream 앞/뒤 어느 쪽에 붙일지 operation z-order로 결정한다.

## Font 처리

초기 단계는 Base14 font를 우선한다.

| 단계 | 범위 |
|---|---|
| 1단계 | Helvetica, Times, Courier 등 Base14 reference |
| 2단계 | TrueType subset embedding |
| 3단계 | CID font, CMap, vertical writing |

Base14만 사용할 때도 viewer 호환성을 위해 resource dictionary에 font entry를 명확히 추가한다.

## Image XObject 작성

새 이미지 추가는 다음 format을 우선한다.

- JPEG 입력: `DCTDecode` 유지 또는 libjpeg-turbo 재인코딩
- PNG 입력: alpha가 없으면 Flate image stream, alpha가 있으면 soft mask 생성
- 기타 입력: 초기 범위에서는 서버에서 명시 오류

Image dictionary에는 다음을 쓴다.

- `/Type /XObject`
- `/Subtype /Image`
- `/Width`
- `/Height`
- `/ColorSpace`
- `/BitsPerComponent`
- `/Filter`
- `/Length`

## xref 작성

초기 writer는 xref table을 기본으로 쓴다.

```text
xref
0 N
0000000000 65535 f
0000012345 00000 n
trailer
<< /Size N /Root 1 0 R /Prev oldXref >>
startxref
123456
%%EOF
```

xref stream은 PDF 1.5+ 최적화로 나중에 추가한다. 단, reader는 xref stream을 읽을 수 있어야 한다.

## Trailer 작성

trailer는 기존 trailer를 기반으로 필요한 값만 갱신한다.

- `/Size`: 새 max object number + 1
- `/Root`: 기존 root 유지 또는 새 root reference
- `/Info`: metadata 변경 시 새 info reference
- `/ID`: 기존 ID 유지, 필요 시 두 번째 ID 갱신
- `/Encrypt`: 암호화 PDF 저장 지원 시 유지
- `/Prev`: incremental update에서 이전 xref offset 기록

## 완료 기준

- 새 object와 stream을 PDF grammar로 직렬화할 수 있다.
- xref offset이 실제 byte offset과 일치한다.
- 새 content stream으로 텍스트/이미지/주석 추가를 표현할 수 있다.
- 기존 객체를 불필요하게 재직렬화하지 않는다.