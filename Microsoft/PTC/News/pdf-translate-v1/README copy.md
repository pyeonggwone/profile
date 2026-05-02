텍스트(ASCII) + 바이너리(binary)



PDF 표준 필터 목록 (ISO 32000)
Filter 이름	알고리즘	용도
/FlateDecode	zlib / Deflate	🔥 가장 많이 쓰임. 일반 텍스트, 폰트, 벡터 그래픽 압축
/LZWDecode	LZW	옛날 방식 (GIF와 동일), 요즘 거의 안 씀
/ASCII85Decode	ASCII85	바이너리를 ASCII로 인코딩 (압축 X)
/ASCIIHexDecode	Hex	바이너리를 16진수 텍스트로
/RunLengthDecode	RLE	단순 반복 압축
/DCTDecode	JPEG	사진 이미지
/JPXDecode	JPEG 2000	고품질 이미지
/CCITTFaxDecode	CCITT Fax (G3/G4)	흑백 스캔 문서 (팩스 압축)
/JBIG2Decode	JBIG2	흑백 스캔 문서 (고압축)
/Crypt	암호화	보안 PDF
가장 핵심: De
Filter 이름	알고리즘	표준	용도
/FlateDecode	Deflate (zlib)	RFC 1950/1951	🔥 모든 stream 기본. 텍스트, 폰트, 벡터
/LZWDecode	LZW	—	옛날 방식 (GIF와 동일). PDF 1.2 이전
/RunLengthDecode	RLE (반복 압축)	—	단순 반복 데이터
/CCITTFaxDecode	CCITT G3/G4	ITU T.4/T.6	흑백 스캔 문서, 팩스
/JBIG2Decode	JBIG2	ISO/IEC 14492	흑백 스캔 (고압축) — JPEG의 흑백판
/DCTDecode	JPEG	ISO/IEC 10918	컬러 사진, 풀컬러 이미지
/JPXDecode	JPEG 2000	ISO/IEC 15444	고품질 이미지 (JPEG보다 좋음)
flate (zlib)
/ASCII85Decode	ASCII85 (Base85)	바이너리를 ASCII로 (~25% 부풀림)
/ASCIIHexDecode	Hex (16진수)	바이너리를 hex 텍스트로 (2배로 부풀림)
Filter	어디에
/FlateDecode	텍스트, 폰트, 벡터 그래픽, 메타데이터
/DCTDecode	JPEG 사진 (그대로 임베딩)
/CCITTFaxDecode	흑백 스캔 PDF
나머지는 거의 안 보임:

/LZWDecode — 1996년 이후 거의 안 씀 (특허 문제 있었음)
/RunLengthDecode — 너무 단순해서 안 씀
/ASCII85Decode, /ASCIIHexDecode — 옛날 호환용
/JBIG2Decode, /JPXDecode — 특수 용도
/Crypt — 암호화 PDF


PDF 바이너리의 90% 이상은 Deflate 알고리즘입니다.

Deflate = LZ77 + 허프만 부호화 조합
1996년 RFC 1951로 표준화
같은 알고리즘을 쓰는 곳:
ZIP 파일 (.zip)
gzip (.gz)
PNG 이미지
HTTP gzip 압축
Git 내부 객체 저장




qpdf --qdf --object-streams=disable --stream-data=uncompress 원본.pdf 풀린.pdf
qpdf = Jay Berkenbilt가 2008년에 만든 오픈소스 PDF 조작 도구 (C++).


ISO 32000



4 0 obj

<</Length 50>>

stream

BT /F1 12 Tf 100 700 Td (Hello) Tj ET

endstream

endobj





stream 부분을 zlib으로 압축





원본 텍스트:  "BT /F1 12 Tf 100 700 Td (Hello) Tj ET"

                          ↓ zlib 압축

압축 결과:    78 9C 73 0A E3 92 ... (바이너리 바이트들)







4 0 obj

<</Length 24/Filter/FlateDecode>>     ← "이거 zlib 압축됨" 표시

stream

[여기에 압축된 바이너리 바이트 24개]   ← 텍스트 에디터로 보면 깨짐

endstream

endobj







Copilot said: # zlib 압축하는 방법 — **Deflate 알고리즘을
zlib 압축하는 방법 — Deflate 알고리즘을 실행하는 것
손으로는 사실상 불가능하고(수학적으로 너무 복잡), 실무에선 zlib 구현체를 호출합니다. 알고리즘 자체와 실제 방법 둘 다 설명할게요.

알고리즘 자체 (Deflate)
zlib 압축 = 두 단계:

1단계: LZ77 (반복 패턴 찾기)
원본에서 앞에 나왔던 같은 문자열을 찾아서 "(거리, 길이)"로 대체.

Code
원본:   "BT /F1 12 Tf BT /F1 12 Tf"
                       ↑ 앞에 나온 거 반복

LZ77:   "BT /F1 12 Tf <13바이트 전, 13글자 복사>"
2단계: Huffman 부호화 (자주 나오는 글자에 짧은 비트 할당)
Code
자주 나오는 글자 'e' → 2비트 (예: 01)
드문 글자 'z'        → 8비트 (예: 11010110)
결과: 비트 단위로 빽빽하게 묶어서 바이트로 출력
Code
원본:    "BT /F1 12 Tf 100 700 Td (Hello) Tj ET"  (37 바이트)
                ↓ Deflate
결과:    78 9C 73 0A E3 92 ...                    (예: 24 바이트)
→ 이게 PDF stream에 들어가는 그 깨진 바이너리.

실제로 어떻게 하나? — zlib 라이브러리 호출
손으로 LZ77 + Huffman 계산하는 건 사실상 불가능. 그래서 모든 운영체제/언어에 zlib 구현체가 기본으로 깔려있어요.

방법 1: 명령줄 한 줄 (가장 쉬움)
Linux/macOS/Git Bash 어디서나:

Code
echo -n "BT /F1 12 Tf 100 700 Td (Hello) Tj ET" | openssl zlib > compressed.bin
→ compressed.bin 파일에 zlib 압축된 바이너리가 만들어짐. 이걸 stream 안에 그대로 넣으면 됨.

방법 2: pigz / gzip (옵션 조정)
Code
gzip < input.txt > output.gz       (gzip 헤더 포함)
zlib과 거의 같지만 헤더가 약간 달라요.

방법 3: 운영체제 내장 도구
OS	도구
Windows	PowerShell의 [System.IO.Compression.DeflateStream]
macOS/Linux	openssl zlib, pigz, zlib-flate (qpdf에 포함)
zlib-flate (qpdf 설치 시 같이 옴):

Code
zlib-flate -compress < input.txt > output.bin
zlib-flate -uncompress < output.bin > original.txt
압축 7개: FlateDecode, LZWDecode, RunLengthDecode, CCITTFaxDecode, JBIG2Decode, DCTDecode, JPXDecode
인코딩 2개: ASCII85Decode, ASCIIHexDecode (압축 X, 표현만 변환)
암호화 1개: Crypt








웹에서는 



PDF.js







zlib 디코더       ← FlateDecode 풀 때
JPEG 디코더       ← DCTDecode 풀 때
JPEG2000 디코더   ← JPXDecode 풀 때
CCITT 디코더      ← CCITTFaxDecode 풀 때
JBIG2 디코더      ← JBIG2Decode 풀 때
LZW 디코더        ← LZWDecode 풀 때
RLE 디코더        ← RunLengthDecode 풀 때
ASCII85 디코더    ← ASCII85Decode 풀 때
Hex 디코더        ← ASCIIHexDecode 풀 때


[1] 사용자: 웹페이지에서 PDF 업로드
프론트엔드 (직접 작성):

HTML
<form action="/upload" method="POST" enctype="multipart/form-data">
  <input type="file" name="pdf" accept="application/pdf">
  <button>업로드</button>
</form>
→ 브라우저 표준 기능. 라이브러리 필요 없음.

[2] 서버: PDF 받아서 저장
서버 코드 (언어 선택):

언어	표준 방식
Python	표준 라이브러리 http.server 또는 직접 소켓
Node.js	표준 http 모듈
Java	표준 HttpServer
Go	표준 net/http
C++	직접 소켓 프로그래밍
→ 받은 바이트를 디스크에 .pdf로 저장. 표준 파일 I/O.

[3] 서버: PDF 직접 파싱 ★ 핵심
여기가 진짜 작업입니다. ISO 32000 규격대로 직접 구현:

3-1. 파일 구조 파싱
Code
%PDF-1.7              ← 헤더 읽기
...
xref                  ← 색인 위치 찾기 (파일 끝에서 startxref 읽음)
0 25
0000000000 65535 f
0000000015 00000 n    ← 각 객체의 바이트 위치
...
trailer
<</Root 1 0 R>>       ← Catalog 위치
%%EOF
직접 구현할 것:

파일 끝에서 startxref 찾기
xref 테이블 읽어서 객체 위치 매핑
trailer 파싱해서 Catalog 찾기
3-2. 객체 파싱
Code
4 0 obj
<</Type/Page/Contents 5 0 R/Resources<<...>>>>
endobj
직접 구현할 것:

PDF 객체 문법 파서 (사전 <<>>, 배열 [], 문자열 (), 이름 /, 참조 N 0 R)
3-3. Stream 디코드 ★★
각 Filter별 디코더를 직접 호출:

Filter	직접 구현?	시스템 표준
FlateDecode	zlib는 운영체제 표준 (RFC 1950)	OS의 zlib API 호출
DCTDecode	JPEG는 운영체제 표준 (ISO 10918)	OS의 JPEG API 호출
JPXDecode	JPEG2000 표준	OS API 또는 직접
CCITTFaxDecode	ITU T.6 표준	직접 구현
JBIG2Decode	ISO 14492 표준	직접 구현
LZWDecode	LZW 알고리즘	직접 구현 (간단)
RunLengthDecode	RLE	직접 구현 (매우 간단)
ASCII85Decode	Base85	직접 구현 (매우 간단)
ASCIIHexDecode	Hex	직접 구현 (매우 간단)
zlib과 JPEG은 운영체제 시스템 콜로 호출 (표준이라 라이브러리 아님). 나머지는 RFC/ISO 명세대로 직접 코드 작성.

3-4. 분석 작업
압축 풀린 stream에서:

텍스트 추출: BT ... Tj ... ET 명령어에서 글자 뽑기 + ToUnicode CMap으로 실제 문자 매핑
이미지 추출: XObject Image stream 그대로 .jpg/.png로 저장
메타데이터: Info 사전 읽기
폰트: Font 사전과 임베디드 폰트 stream
양식: AcroForm 사전 → 필드별 값
주석: Page의 Annots 배열
[4] 서버: 분석 결과 저장
표준 방식:

파일 시스템에 JSON으로 저장 (직접 JSON 직렬화)
또는 직접 만든 바이너리 포맷
DB는 SQLite 같은 표준 내장 DB 사용
[5] 사용자가 볼 때
원본 .pdf 표시:

서버가 .pdf 파일 그대로 전송
브라우저가 받음
여기서 선택:

옵션 A: 브라우저 내장 PDF 뷰어에 맡김 (가장 쉬움)
옵션 B: PDF.js 같은 거 안 쓰고 HTML5 Canvas API로 직접 그리기 엔진 작성
항목	표준
HTTP	RFC 9110
파일 업로드	RFC 7578 (multipart/form-data)
PDF	ISO 32000-2
zlib 압축	RFC 1950, RFC 1951
JPEG	ISO/IEC 10918
JPEG2000	ISO/IEC 15444
CCITT Fax	ITU T.6
JBIG2	ISO/IEC 14492
HTML5 Canvas	W3C 표준
JSON	RFC 8259


Phase 1: 뼈대 (1~2일)
HTTP 서버 + 파일 업로드 폼
.pdf 받아서 디스크에 저장
저장된 .pdf 그대로 다시 다운로드
→ AI한테: "Python으로 파일 업로드 받는 HTTP 서버 만들어줘. 라이브러리 최소로."

Phase 2: PDF 구조 파싱 (3~7일)
파일 끝에서 startxref 찾기
xref 테이블 읽기
trailer 파싱 → Catalog 위치
객체 파서 (사전, 배열, 문자열, 이름, 참조)
모든 객체 dict로 만들기
→ AI한테: "ISO 32000-2 규격대로 PDF의 xref 테이블 파싱하는 함수 작성. 입력은 .pdf 바이트, 출력은 객체번호 → 바이트오프셋 dict."

Phase 3: Stream 디코드 (5~14일)
stream 객체 찾기 (/Length, /Filter 읽기)
FlateDecode (zlib): OS 표준 zlib 호출
ASCIIHexDecode, ASCII85Decode, RunLengthDecode: 직접 구현 (간단)
LZWDecode: 직접 구현
DCTDecode: stream 그대로 .jpg로 (디코드 안 해도 됨)
CCITTFaxDecode, JBIG2Decode, JPXDecode: 나중에
→ AI한테 Filter별로 따로따로 시킴.

Phase 4: 분석 기능 (당신이 원했던 거)
메타데이터 추출: Info 사전 읽어서 JSON
페이지 수: Pages 트리 순회
텍스트 추출: Contents stream에서 Tj/TJ 명령어 + ToUnicode 매핑
이미지 추출: XObject Image stream → .jpg/.png
폰트 정보: Font 사전
양식 필드: AcroForm
주석/책갈피: Annots, Outlines
각각을 별도 함수로. AI한테 하나씩 시키면 잘 만듦.

Phase 5: 결과 저장
분석 결과를 JSON으로 저장
SQLite에 메타데이터 인덱싱
Phase 6: 웹 표시
원본 .pdf 전송 엔드포인트
분석 결과 JSON API 엔드포인트
프론트: 브라우저 내장 PDF 뷰어로 일단 표시 (<iframe src="...pdf">)
또는 직접 Canvas 렌더러 작성 (Phase 7로)
Phase 7 (선택): 직접 렌더링 엔진
JavaScript로 PDF 파서 (Phase 2~3을 JS로)
PDF 그리기 명령 → Canvas 2D API 변환
폰트 처리, 텍스트 레이어


