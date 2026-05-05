# Analysis and Extraction 설계

## 목적

PDF에서 텍스트, 이미지, 메타데이터, 폰트, 주석 정보를 추출하는 분석 계층을 설계한다. 이 계층은 웹 표시와 편집 UI의 기반 데이터를 제공한다.

## 기준 기술

| 영역 | 기술 | 기준 버전 |
|---|---|---:|
| 구현 언어 | Rust | `1.78+` |
| Stream decode | `pdf_filters` | 같은 workspace |
| Text mapping | 직접 ToUnicode/CMap parser | PDF spec 기반 |
| Image decode | zlib/libjpeg-turbo/OpenJPEG adapter | 각 설계 기준 버전 |

## 분석 대상

| 대상 | 산출물 |
|---|---|
| 문서 metadata | title, author, subject, keywords, creation/mod date |
| Page 구조 | page count, size, rotation, resources |
| Text | 문자열, 위치, font, size, writing mode |
| Image | object id, 크기, 색상 공간, preview 가능 여부 |
| Font | font name, subtype, encoding, embedded 여부 |
| Annotation | subtype, rect, contents, target page |
| Form | AcroForm field tree, widget annotation |
| Embedded file | 존재 여부와 metadata, 실행 없음 |

## Content stream 해석

content stream은 PDF graphics operator를 순서대로 해석한다.

초기 operator 범위는 다음과 같다.

- graphics state: `q`, `Q`, `cm`, `w`, `J`, `j`, `M`, `d`, `ri`, `i`, `gs`
- path: `m`, `l`, `c`, `v`, `y`, `h`, `re`, `S`, `s`, `f`, `F`, `f*`, `B`, `B*`, `b`, `b*`, `n`
- text: `BT`, `ET`, `Tf`, `Td`, `TD`, `Tm`, `T*`, `Tj`, `TJ`, `'`, `"`, `Tc`, `Tw`, `Tz`, `TL`, `Tr`, `Ts`
- color: `CS`, `cs`, `SC`, `SCN`, `sc`, `scn`, `G`, `g`, `RG`, `rg`, `K`, `k`
- XObject: `Do`

Operator parser는 rendering과 extraction이 함께 사용할 intermediate instruction을 만든다.

## 텍스트 추출

텍스트 추출은 단순 string decode가 아니라 graphics state와 font encoding을 반영한다.

처리 순서는 다음과 같다.

```text
1. page content stream decode
2. text state stack 초기화
3. `BT`/`ET` 범위에서 text operator 해석
4. current font resource 확인
5. character code -> Unicode 변환
6. text matrix와 font size로 glyph 위치 계산
7. line/block 후보로 grouping
```

Unicode 변환 우선순위는 다음과 같다.

1. ToUnicode CMap
2. embedded encoding dictionary
3. standard encoding 또는 WinAnsi/MacRoman
4. glyph name mapping
5. unknown character marker

## 이미지 추출

이미지는 image XObject와 inline image를 모두 고려한다.

수집 항목은 다음과 같다.

- object id 또는 inline image 위치
- width, height
- bits per component
- color space
- filter chain
- mask/soft mask 여부
- preview 생성 가능 여부

편집하지 않은 이미지는 원본 stream을 보존한다. preview가 필요한 경우에만 decode한다.

## 폰트 분석

폰트 분석은 렌더링과 텍스트 추출 모두에 필요하다.

수집 항목은 다음과 같다.

- font resource name
- subtype: Type1, TrueType, Type0, CIDFontType2 등
- base font name
- encoding
- ToUnicode 존재 여부
- embedded font file reference
- descendant font 정보

초기 구현은 extraction quality를 위해 ToUnicode와 simple font encoding을 우선한다. full shaping은 장기 과제다.

## 주석 분석

page dictionary의 `/Annots`를 순회한다.

지원 우선순위는 다음과 같다.

1. Text annotation
2. Link annotation
3. FreeText annotation
4. Highlight/Underline/Squiggly/StrikeOut
5. Widget annotation

JavaScript action이나 Launch action은 실행하지 않고 존재 여부만 표시한다.

## Render Plan 산출

웹 viewer가 PDF content stream을 직접 파싱하지 않도록 서버는 render plan을 제공한다.

예시 구조는 다음과 같다.

```json
{
  "page": 1,
  "size": { "width": 595.0, "height": 842.0 },
  "commands": [
    { "op": "text", "text": "Hello", "x": 120.0, "y": 240.0, "fontSize": 12.0 },
    { "op": "image", "assetId": "img-12", "x": 10.0, "y": 10.0, "width": 100.0, "height": 80.0 }
  ]
}
```

이 구조는 PDF 원본을 완전히 표현하는 목적이 아니라 웹 표시와 편집에 필요한 중간 표현이다.

## 완료 기준

- page별 텍스트와 이미지 목록을 추출한다.
- ToUnicode 기반 텍스트 추출을 지원한다.
- annotation 목록을 page와 연결한다.
- 웹 viewer가 사용할 render plan을 생성한다.