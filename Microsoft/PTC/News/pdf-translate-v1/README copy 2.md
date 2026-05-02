# PDF Stream 압축, 디코딩, 직접 파서 구현 정리

이 문서는 PDF 내부 stream 압축 방식과 웹 기반 PDF 업로드/분석 도구를 직접 구현할 때 필요한 핵심 개념을 정리한 것이다.

## 1. PDF stream과 Filter 개념

PDF의 많은 데이터는 `stream ... endstream` 구간에 저장된다. 텍스트, 폰트, 벡터 그래픽, 이미지, 메타데이터 등이 여기에 들어갈 수 있으며, 용량을 줄이기 위해 압축되거나 인코딩된다.

PDF 객체 예시는 다음과 같다.

```pdf
4 0 obj
<</Length 50>>
stream
BT /F1 12 Tf 100 700 Td (Hello) Tj ET
endstream
endobj
```

위 stream을 zlib으로 압축하면 PDF에는 다음처럼 기록된다.

```pdf
4 0 obj
<</Length 24/Filter/FlateDecode>>
stream
[압축된 바이너리 바이트]
endstream
endobj
```

`/Filter/FlateDecode`는 이 stream이 zlib/Deflate 방식으로 압축되어 있음을 의미한다.

## 2. PDF 표준 Filter 목록

| Filter | 알고리즘 | 표준 | 주요 용도 |
| --- | --- | --- | --- |
| `/FlateDecode` | Deflate, zlib | RFC 1950, RFC 1951 | 텍스트, 폰트, 벡터 그래픽, 메타데이터 등 대부분의 stream |
| `/LZWDecode` | LZW | - | 오래된 PDF에서 사용, 현재는 거의 사용하지 않음 |
| `/RunLengthDecode` | RLE | - | 단순 반복 데이터 압축 |
| `/CCITTFaxDecode` | CCITT G3/G4 | ITU T.4, T.6 | 흑백 스캔 문서, 팩스 이미지 |
| `/JBIG2Decode` | JBIG2 | ISO/IEC 14492 | 흑백 스캔 문서 고압축 |
| `/DCTDecode` | JPEG | ISO/IEC 10918 | 컬러 사진, 풀컬러 이미지 |
| `/JPXDecode` | JPEG 2000 | ISO/IEC 15444 | 고품질 이미지 |
| `/ASCII85Decode` | ASCII85, Base85 | - | 바이너리를 ASCII 텍스트로 표현 |
| `/ASCIIHexDecode` | Hex | - | 바이너리를 16진수 텍스트로 표현 |
| `/Crypt` | 암호화 | PDF 보안 구조 | 암호화된 PDF stream |

실무에서 가장 자주 만나는 Filter는 `/FlateDecode`다. PDF 바이너리의 상당 부분은 Deflate 알고리즘으로 압축되어 있으며, ZIP, gzip, PNG, HTTP gzip, Git 내부 객체 저장에도 같은 계열의 압축 방식이 사용된다.

## 3. 압축과 인코딩 구분

PDF Filter는 크게 압축, 인코딩, 암호화로 나눌 수 있다.

| 구분 | Filter |
| --- | --- |
| 압축 | `/FlateDecode`, `/LZWDecode`, `/RunLengthDecode`, `/CCITTFaxDecode`, `/JBIG2Decode`, `/DCTDecode`, `/JPXDecode` |
| 인코딩 | `/ASCII85Decode`, `/ASCIIHexDecode` |
| 암호화 | `/Crypt` |

`/ASCII85Decode`와 `/ASCIIHexDecode`는 압축이 아니라 바이너리 데이터를 텍스트 형태로 표현하는 방식이다. ASCII85는 약 25% 정도 크기가 늘고, ASCIIHex는 보통 2배 정도 커진다.

## 4. Deflate와 zlib 압축

zlib 압축은 Deflate 알고리즘을 실행하는 것이다. Deflate는 크게 두 단계로 구성된다.

1. LZ77: 앞에서 나온 반복 패턴을 `(거리, 길이)` 형태로 대체한다.
2. Huffman 부호화: 자주 나오는 값에는 짧은 비트열을, 드문 값에는 긴 비트열을 할당한다.

예시는 다음과 같다.

```text
원본: BT /F1 12 Tf BT /F1 12 Tf
LZ77: BT /F1 12 Tf <13바이트 전, 13글자 복사>
```

Huffman 부호화까지 거치면 비트 단위로 압축된 바이너리 결과가 생성되고, 이 값이 PDF stream 안에 들어간다.

```text
원본: BT /F1 12 Tf 100 700 Td (Hello) Tj ET
결과: 78 9C 73 0A E3 92 ...
```

Deflate를 손으로 구현하거나 계산하는 것은 실무적으로 어렵기 때문에 일반적으로 zlib 구현체를 호출한다.

## 5. zlib 압축과 해제 방법

명령줄에서는 다음과 같은 도구를 사용할 수 있다.

```bash
zlib-flate -compress < input.txt > output.bin
zlib-flate -uncompress < output.bin > original.txt
```

qpdf를 사용하면 PDF stream을 사람이 읽기 쉬운 형태로 풀 수 있다.

```bash
qpdf --qdf --object-streams=disable --stream-data=uncompress original.pdf uncompressed.pdf
```

`qpdf`는 Jay Berkenbilt가 만든 오픈소스 PDF 조작 도구이며, PDF 내부 구조를 분석하거나 stream을 풀어볼 때 유용하다.

Windows에서는 PowerShell의 `.NET` API인 `System.IO.Compression.DeflateStream`을 사용할 수 있다.

## 6. 웹에서 PDF를 다룰 때 필요한 디코더

웹에서 PDF를 렌더링하거나 분석하려면 PDF.js 같은 라이브러리가 내부적으로 여러 디코더를 사용한다.

| PDF Filter | 필요한 디코더 |
| --- | --- |
| `/FlateDecode` | zlib 디코더 |
| `/DCTDecode` | JPEG 디코더 |
| `/JPXDecode` | JPEG 2000 디코더 |
| `/CCITTFaxDecode` | CCITT 디코더 |
| `/JBIG2Decode` | JBIG2 디코더 |
| `/LZWDecode` | LZW 디코더 |
| `/RunLengthDecode` | RLE 디코더 |
| `/ASCII85Decode` | ASCII85 디코더 |
| `/ASCIIHexDecode` | Hex 디코더 |

PDF.js를 사용하지 않고 직접 구현하려면 위 디코더와 PDF 문법 파서, 페이지 렌더링 엔진을 직접 작성해야 한다.

## 7. 웹 기반 PDF 업로드/분석 구조

전체 흐름은 다음과 같다.

1. 사용자가 웹페이지에서 PDF를 업로드한다.
2. 서버가 PDF 파일을 받아 디스크에 저장한다.
3. 서버가 PDF 구조를 직접 파싱한다.
4. stream Filter를 읽고 필요한 디코더로 압축을 해제한다.
5. 텍스트, 이미지, 메타데이터, 폰트, 양식, 주석 등을 분석한다.
6. 분석 결과를 JSON이나 SQLite 등에 저장한다.
7. 브라우저에서 원본 PDF와 분석 결과를 표시한다.

파일 업로드 HTML 예시는 다음과 같다.

```html
<form action="/upload" method="POST" enctype="multipart/form-data">
	<input type="file" name="pdf" accept="application/pdf">
	<button>업로드</button>
</form>
```

서버 구현은 언어별 표준 HTTP 기능으로 시작할 수 있다.

| 언어 | 표준 방식 |
| --- | --- |
| Python | `http.server` 또는 직접 소켓 |
| Node.js | `http` 모듈 |
| Java | `HttpServer` |
| Go | `net/http` |
| C++ | 소켓 프로그래밍 |

## 8. PDF 직접 파싱 시 구현할 항목

### 8.1 파일 구조 파싱

PDF 파일 끝에는 `startxref`가 있고, 여기에서 xref 테이블 위치를 찾는다.

```pdf
%PDF-1.7
...
xref
0 25
0000000000 65535 f
0000000015 00000 n
...
trailer
<</Root 1 0 R>>
%%EOF
```

구현해야 할 작업은 다음과 같다.

- 파일 끝에서 `startxref` 찾기
- xref 테이블 읽기
- 객체 번호와 바이트 오프셋 매핑
- trailer 파싱
- Catalog 객체 위치 찾기

### 8.2 PDF 객체 파싱

PDF 객체는 사전, 배열, 문자열, 이름, 참조 등으로 구성된다.

```pdf
4 0 obj
<</Type/Page/Contents 5 0 R/Resources<<...>>>>
endobj
```

직접 구현할 문법 요소는 다음과 같다.

- Dictionary: `<< >>`
- Array: `[ ]`
- String: `( )`
- Name: `/Name`
- Reference: `N 0 R`
- Stream: `stream ... endstream`

### 8.3 Stream 디코드

stream 객체에서는 `/Length`와 `/Filter`를 읽어 실제 데이터를 해석한다.

| Filter | 구현 방향 |
| --- | --- |
| `/FlateDecode` | zlib API 호출 |
| `/ASCIIHexDecode` | 직접 구현 가능 |
| `/ASCII85Decode` | 직접 구현 가능 |
| `/RunLengthDecode` | 직접 구현 가능 |
| `/LZWDecode` | 직접 구현 가능하지만 난이도 있음 |
| `/DCTDecode` | JPEG stream을 그대로 추출 가능 |
| `/CCITTFaxDecode` | 나중 단계에서 구현 |
| `/JBIG2Decode` | 나중 단계에서 구현 |
| `/JPXDecode` | 나중 단계에서 구현 |

### 8.4 분석 기능

압축이 해제된 stream과 PDF 객체 구조를 바탕으로 다음 정보를 추출할 수 있다.

| 분석 항목 | 구현 방식 |
| --- | --- |
| 메타데이터 | Info 사전 읽기 |
| 페이지 수 | Pages 트리 순회 |
| 텍스트 | Contents stream의 `BT`, `Tj`, `TJ`, `ET` 명령 분석 및 ToUnicode CMap 매핑 |
| 이미지 | XObject Image stream 추출 |
| 폰트 | Font 사전 및 임베디드 폰트 stream 분석 |
| 양식 | AcroForm 사전과 필드 값 분석 |
| 주석 | Page의 Annots 배열 분석 |
| 책갈피 | Outlines 구조 분석 |

## 9. 단계별 구현 계획

### Phase 1. 웹 업로드 뼈대

- HTTP 서버 작성
- 파일 업로드 폼 작성
- 업로드된 `.pdf`를 디스크에 저장
- 저장된 PDF를 다시 다운로드하거나 표시

### Phase 2. PDF 구조 파싱

- `startxref` 찾기
- xref 테이블 읽기
- trailer 파싱
- Catalog 찾기
- 객체 번호와 바이트 오프셋 매핑
- 사전, 배열, 문자열, 이름, 참조를 파싱하는 객체 파서 작성

### Phase 3. Stream 디코드

- stream 객체 찾기
- `/Length`와 `/Filter` 읽기
- `/FlateDecode`는 zlib으로 해제
- `/ASCIIHexDecode`, `/ASCII85Decode`, `/RunLengthDecode` 직접 구현
- `/LZWDecode` 직접 구현
- `/DCTDecode` 이미지는 JPEG로 그대로 추출
- `/CCITTFaxDecode`, `/JBIG2Decode`, `/JPXDecode`는 후순위로 처리

### Phase 4. 분석 기능

- Info 사전 기반 메타데이터 추출
- Pages 트리 기반 페이지 수 추출
- Contents stream 기반 텍스트 추출
- XObject Image 기반 이미지 추출
- Font 사전 기반 폰트 정보 추출
- AcroForm 기반 양식 필드 추출
- Annots와 Outlines 기반 주석, 책갈피 추출

### Phase 5. 결과 저장

- 분석 결과를 JSON으로 저장
- 필요하면 SQLite에 메타데이터 인덱싱

### Phase 6. 웹 표시

- 원본 PDF 전송 엔드포인트 작성
- 분석 결과 JSON API 작성
- 브라우저 내장 PDF 뷰어를 `<iframe>`으로 사용

```html
<iframe src="/files/sample.pdf"></iframe>
```

### Phase 7. 직접 렌더링 엔진

- JavaScript PDF 파서 구현
- PDF 그래픽 명령을 Canvas 2D API로 변환
- 폰트 처리
- 텍스트 레이어 처리

## 10. 관련 표준

| 항목 | 표준 |
| --- | --- |
| HTTP | RFC 9110 |
| 파일 업로드 | RFC 7578, multipart/form-data |
| PDF | ISO 32000-2 |
| zlib | RFC 1950 |
| Deflate | RFC 1951 |
| JPEG | ISO/IEC 10918 |
| JPEG 2000 | ISO/IEC 15444 |
| CCITT Fax | ITU T.6 |
| JBIG2 | ISO/IEC 14492 |
| HTML5 Canvas | W3C 표준 |
| JSON | RFC 8259 |

## 11. AI에게 작업을 나눠 요청하는 방식

큰 작업을 한 번에 맡기기보다 단계별 함수나 모듈 단위로 나누는 것이 좋다.

예시 요청:

```text
Python으로 파일 업로드를 받는 HTTP 서버를 만들어줘. 외부 라이브러리는 최소화해줘.
```

```text
ISO 32000-2 규격을 기준으로 PDF의 xref 테이블을 파싱하는 함수를 작성해줘. 입력은 PDF 바이트이고, 출력은 객체 번호와 바이트 오프셋 매핑이야.
```

```text
PDF stream의 /ASCIIHexDecode Filter를 해제하는 함수를 작성해줘. 입력은 bytes, 출력도 bytes로 해줘.
```

```text
PDF Contents stream에서 Tj와 TJ 명령어를 찾아 텍스트 후보를 추출하는 파서를 작성해줘.
```

이렇게 나누면 PDF 파서, stream 디코더, 텍스트 추출기, 웹 API를 각각 독립적으로 구현하고 테스트하기 쉽다.
