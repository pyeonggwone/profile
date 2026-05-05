# MOBI Adapter 설계

## 목적

MOBI 파일을 native adapter로 처리해 텍스트를 번역하고 `.mobi`로 다시 저장한다.

## MVP 목표

- MOBI 파일 인식
- 본문 텍스트 record 추출
- 압축 방식 확인
- 번역 적용
- `.mobi` 출력 생성

## Reader 책임

- PalmDB header 읽기
- record offset table 파싱
- MOBI header와 EXTH metadata 확인
- text encoding 확인
- PalmDOC/HUFF/CDIC 등 압축 여부 확인
- 번역 가능한 본문 text stream 추출
- DRM 여부 감지

## Writer 책임

- 번역된 text stream을 record 단위로 재구성
- 필요한 경우 text record 재분할
- record offset table 갱신
- EXTH metadata 보존 및 language 갱신 후보 처리
- `.mobi` 출력 생성

## 위험 요소

- MOBI는 오래된 포맷이라 레이아웃 정보가 제한적이다.
- text 길이 변화가 record 분할과 offset 갱신에 영향을 준다.
- 압축 방식별 구현 난이도가 다르다.

## 완료 기준

- 비DRM MOBI 샘플에서 번역 output이 생성된다.
- record table이 일관된 상태로 저장된다.
- 출력 검증 결과를 metadata JSON에 남긴다.
