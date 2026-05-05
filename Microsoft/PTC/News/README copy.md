1. 전체 프로젝트의 목적
이 프로젝트 묶음의 핵심 목적은 다음과 같습니다.

영어 기술 자료, 뉴스, 문서, 발표자료를 빠르게 한국어로 변환한다.
원본 문서의 레이아웃, 이미지, 표, 스타일, 슬라이드 디자인, EPUB 구조 등을 최대한 유지한다.
반복되는 문장은 Translation Memory로 재사용해 비용과 시간을 줄인다.
Azure OpenAI 또는 OpenAI API를 사용해 번역 품질을 높인다.
사람이 최종 검토하기 쉬운 결과물을 만든다.
즉, “기계 번역 결과를 텍스트로만 얻는 도구”가 아니라, 실제 업무 문서 파일을 그대로 번역본으로 재생성하는 자동화 도구 모음에 가깝습니다.

2. docs-translate-v2
docs-translate-v2는 Microsoft Word 문서 번역 도구입니다. 대상 파일은 .docx, .doc이고, Markdown이나 단순 텍스트 파일 번역기가 아닙니다.

이 프로젝트의 가장 중요한 특징은 Microsoft Word 데스크톱 앱을 직접 실행해서 문서를 처리한다는 점입니다. Python에서 pywin32를 통해 Word COM Automation을 호출하고, Word가 실제로 문서를 열고 저장하게 만듭니다.

그래서 일반적인 XML 직접 수정 방식보다 안정적으로 Word 문서 구조를 보존할 수 있습니다.

동작 방식은 크게 세 단계입니다.

EXTRACT
Word 문서를 열고 StoryRanges, paragraph 등을 순회하면서 번역할 텍스트를 추출합니다.

TRANSLATE
추출된 문장을 Translation Memory SQLite DB에서 먼저 조회합니다. 이미 번역한 문장은 재사용하고, 없는 문장만 LLM에 배치로 보냅니다.

APPLY
원본 Word 파일을 복사한 뒤, 같은 위치의 텍스트 Range만 번역문으로 치환합니다. 결과는 output 폴더에 _KR.docx 형태로 저장됩니다.

보존하려는 대상은 표, 이미지, 섹션, 스타일, 머리글, 바닥글, 페이지 설정 같은 Word 문서 구조입니다. URL, email, 변수, 보호 용어도 placeholder로 마스킹해서 번역 중 깨지지 않게 합니다.

다만 Word의 paragraph 단위 Range 치환 특성상, 한 문단 안에서 일부 단어만 bold이거나 italic인 세부 run formatting은 단순화될 수 있습니다. 그래서 이 프로젝트는 “완벽한 Word 내부 서식 보존”보다는 문서 구조와 레이아웃을 최대한 유지하면서 실무용 번역본을 빠르게 만드는 도구라고 설명하면 좋습니다.

한 줄로 설명하면:

docs-translate-v2는 Word 데스크톱 엔진을 직접 사용해서 .docx와 .doc 파일의 문서 구조를 보존한 채 텍스트만 한국어로 치환하는 Word 번역 자동화 도구입니다.

3. ppt-translate-v4
ppt-translate-v4는 PowerPoint 발표자료 번역 도구입니다. 대상은 .pptx, .ppt 파일입니다.

이 프로젝트도 docs-translate-v2와 비슷하게 Office COM Automation을 사용하지만, Word가 아니라 PowerPoint 데스크톱 앱을 직접 제어합니다. python-pptx나 lxml로 PPTX 내부 XML을 수정하지 않고, Microsoft PowerPoint가 제공하는 객체 모델을 사용합니다.

가장 중요한 목표는 슬라이드 디자인을 깨뜨리지 않는 것입니다.

PPT는 Word보다 레이아웃 손상이 더 치명적입니다. 텍스트 박스 위치, 글꼴 크기, SmartArt, 표, 그룹, 차트, 애니메이션, 마스터 레이아웃 등이 조금만 깨져도 발표자료로 쓰기 어렵기 때문입니다.

그래서 이 도구는 원본 PPT를 복사한 뒤, 기존 Shape의 TextRange 또는 Run 텍스트만 번역문으로 바꿉니다. 이미지, 도형, SmartArt, 차트, 애니메이션, 마스터 등은 건드리지 않는 구조입니다.

파이프라인은 다음과 같습니다.

EXTRACT
PowerPoint COM으로 슬라이드를 열고 Slides, Shapes, TextFrame, Runs, Group, Table, Notes 등을 순회하며 텍스트를 추출합니다.

TRANSLATE
SQLite 기반 Translation Memory를 먼저 확인하고, 새 문장만 LLM에 보냅니다. 용어집 glossary.csv도 활용합니다.

APPLY
원본 PPT를 복사한 뒤, 추출할 때 기록한 path를 따라 같은 Shape와 Run 위치에 번역문을 넣습니다. 한글 출력 시 기본 폰트는 맑은 고딕으로 맞춥니다.

ppt-translate-v4는 특히 운영 기능이 더 많이 들어가 있습니다. 예를 들어 input 폴더에 여러 PPT 파일을 넣으면 일괄 처리할 수 있고, 성공한 원본은 input/done으로 이동합니다. 잔여 영문을 검증하고 재번역을 시도하는 기능도 문서에 포함되어 있습니다.

지원하는 언어 옵션은 en, kr, ch, jp 형태로 되어 있고, 기본값은 영어 입력, 한국어 출력입니다.

한 줄로 설명하면:

ppt-translate-v4는 PowerPoint 데스크톱 엔진을 직접 사용해 발표자료의 디자인, 도형, 표, 노트, 애니메이션을 보존하면서 슬라이드 텍스트만 다국어로 번역하는 PPT 번역 자동화 도구입니다.

4. epup-translate-v3
폴더명은 epup-translate-v3로 되어 있지만, 실제 내용은 EPUB 번역 도구입니다.

EPUB은 내부적으로 ZIP 파일입니다. 그 안에 XHTML, CSS, 이미지, 폰트, OPF 메타데이터 등이 들어 있습니다. 그래서 EPUB을 번역하려면 단순히 파일 전체를 텍스트로 읽으면 안 되고, ZIP 구조를 유지하면서 XHTML 안의 텍스트 노드만 골라 번역해야 합니다.

이 프로젝트는 Node.js 기반이고, 주요 라이브러리는 다음과 같습니다.

jszip: EPUB ZIP 입출력
fast-xml-parser: OPF, container.xml 파싱
parse5: XHTML 파싱과 직렬화
openai: OpenAI 또는 Azure OpenAI 호출
better-sqlite3: Translation Memory
csv-parse: 용어집 CSV 처리
commander: CLI 구성
동작 방식은 다음과 같습니다.

input 폴더에 .epub 파일을 넣습니다.
run-translate.sh를 실행합니다.
EPUB 내부 ZIP을 읽고 OPF spine을 따라 XHTML 문서를 찾습니다.
XHTML에서 번역 가능한 텍스트 노드만 추출합니다.
<script>, <style>, <code>, <pre>, <svg>, <math> 같은 영역은 건너뜁니다.
용어집에서 보호해야 하는 용어는 placeholder로 마스킹합니다.
LLM으로 번역하고 SQLite TM에 저장합니다.
번역된 텍스트만 원래 XHTML 위치에 다시 넣습니다.
ZIP 구조, 이미지, 폰트, CSS를 유지한 채 output/{파일명}_KR.epub으로 다시 패키징합니다.
이 프로젝트의 핵심은 EPUB 포맷 보존입니다. 특히 EPUB 스펙상 중요한 mimetype 파일을 ZIP의 첫 엔트리로 두고 무압축으로 저장하는 규칙도 고려되어 있습니다.

또한 DRM 감지도 포함되어 있습니다. META-INF/encryption.xml이 있으면 DRM이 걸린 EPUB으로 보고 처리하지 않습니다.

한 줄로 설명하면:

epup-translate-v3는 EPUB 파일의 ZIP 구조, XHTML 마크업, 이미지, CSS, 폰트를 유지하면서 본문 텍스트 노드만 LLM으로 번역해 새로운 한국어 EPUB을 만드는 Node.js 기반 포맷 보존 번역기입니다.

5. pdf-translate-v1
pdf-translate-v1은 앞의 세 프로젝트와 성격이 조금 다릅니다.

docs, ppt, epub 프로젝트는 실제 실행 가능한 번역 파이프라인에 가깝지만, pdf-translate-v1은 현재 기준으로는 PDF 번역기 구현을 위한 개념 정리와 설계 문서 프로젝트에 가깝습니다.

PDF는 Word, PPT, EPUB보다 훨씬 까다로운 포맷입니다. PDF는 “문단과 제목이 저장된 문서”라기보다, 페이지 위에 텍스트와 이미지를 어떻게 그릴지에 대한 명령어, 객체, stream, 압축 데이터, 폰트, 좌표 정보가 들어 있는 복합 포맷입니다.

그래서 PDF 번역기를 만들려면 단순히 텍스트를 추출해서 바꾸는 수준으로는 부족합니다.

이 프로젝트의 README는 다음 내용을 설명합니다.

PDF는 단순 텍스트 파일이 아니라 객체와 stream으로 구성된 포맷이다.
실제 페이지 내용은 stream ... endstream 안에 들어간다.
stream은 /FlateDecode, /DCTDecode 같은 Filter로 압축되거나 인코딩된다.
가장 중요한 압축 방식은 /FlateDecode, 즉 zlib/Deflate 계열이다.
PDF를 웹에서 분석하거나 편집하려면 PDF 구조 파서, stream 디코더, 텍스트 분석기, 이미지 추출기, 렌더러가 필요하다.
직접 구현하려면 startxref, xref table, trailer, Catalog, Pages tree, Contents stream 순서로 구조를 읽어야 한다.
또한 BUILD.md를 보면, 실제 구현 전 설계를 여러 단계로 나누고 있습니다.

주요 설계 영역은 다음과 같습니다.

요구사항 정리
런타임 기반
웹 업로드/다운로드 경계
PDF reader
stream filter 처리
document model
PDF writer
incremental update
텍스트, 이미지, 메타데이터 분석
웹 viewer/editor
호환성 테스트
delivery roadmap
특히 이 프로젝트는 기존 PDF 엔진을 블랙박스처럼 가져다 쓰는 방식이 아니라, PDF 읽기와 쓰기를 직접 제어하는 방향으로 설계되어 있습니다. pdf.js, poppler, qpdf, iText, PDFBox 같은 엔진 대체를 사용하지 않는다는 원칙도 명시되어 있습니다.

즉, pdf-translate-v1은 당장 “PDF 넣으면 번역본이 나오는 도구”라기보다, PDF 번역/편집기를 직접 만들기 위해 PDF 내부 구조, stream 압축, parser, writer, incremental update 전략을 정리한 설계 프로젝트입니다.

한 줄로 설명하면:

pdf-translate-v1은 PDF를 직접 분석하고 번역 가능한 웹 기반 PDF 편집/번역기를 만들기 위한 기반 설계 프로젝트로, PDF 객체 구조, stream decoding, parser, writer, incremental update 전략을 단계별로 정리한 문서 중심 프로젝트입니다.

6. 네 프로젝트의 차이
프로젝트	대상 포맷	구현 상태/성격	핵심 방식	주요 목표
docs-translate-v2	Word .docx, .doc	실행 가능한 번역 도구	Word COM Automation	Word 문서 구조 보존 번역
ppt-translate-v4	PowerPoint .pptx, .ppt	실행 가능한 번역 도구	PowerPoint COM Automation	슬라이드 디자인 보존 번역
epup-translate-v3	EPUB .epub	실행 가능한 번역 도구	ZIP/XHTML 파싱 후 텍스트 노드 치환	EPUB 구조 보존 번역
pdf-translate-v1	PDF .pdf	설계/로드맵 중심	PDF parser/writer 직접 구현 설계	PDF 분석/편집/번역 엔진 설계