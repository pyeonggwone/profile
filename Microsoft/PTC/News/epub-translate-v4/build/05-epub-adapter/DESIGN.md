# EPUB Adapter 설계

## 목적

EPUB 파일을 native로 읽고, XHTML 텍스트 노드만 번역한 뒤, 원본 EPUB 구조를 유지해 다시 저장한다.

## 기반 로직

`epup-translate-v3`의 EPUB 처리 방식을 v4 adapter 구조로 이전한다.

## Reader 책임

- ZIP 로드
- `META-INF/container.xml` 읽기
- OPF path 탐색
- manifest와 spine 파싱
- XHTML 또는 HTML chapter path 수집
- DRM 감지: `META-INF/encryption.xml`
- EPUB metadata 추출

## Text 처리 책임

- XHTML parse
- 번역 가능한 text node 추출
- `script`, `style`, `code`, `pre`, `svg`, `math` 등 skip
- whitespace 보존 정보 기록
- segment location 기록

## Writer 책임

- 번역된 segment를 원래 XHTML text node 위치에 반영
- XHTML `html lang`, `xml:lang` 갱신
- OPF `dc:language` 갱신
- 원본 이미지, CSS, font, NCX, nav 유지
- `mimetype` 첫 엔트리 및 STORE 압축 유지
- `.epub`으로 저장

## 완료 기준

- v3와 동등한 EPUB 번역 결과를 만든다.
- output EPUB이 일반 EPUB reader에서 열린다.
- EPUB 구조 보존 검증 항목을 metadata에 기록할 수 있다.
