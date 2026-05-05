# AZW3 Adapter 설계

## 목적

AZW3/KF8 파일을 native adapter로 처리해 텍스트를 번역하고 `.azw3`로 다시 저장한다.

## MVP 목표

초기 목표는 완벽한 Kindle 보존이 아니라 다음을 확인하는 것이다.

- AZW3 파일 인식
- 본문 텍스트 추출
- 번역 적용
- `.azw3` 출력 생성
- 출력 파일 열림 여부 확인

## Reader 책임

- Palm database 구조 파악
- MOBI/KF8 header 식별
- text record와 resource record 구분
- 메타데이터 후보 추출
- DRM 또는 암호화 여부 감지
- 번역 가능한 HTML 계열 text payload 추출

## Writer 책임

- 번역된 text payload를 원래 record 구조에 반영
- record 길이와 offset table 갱신
- 원본 이미지, font, resource record 보존
- 가능한 경우 metadata language 갱신
- `.azw3` 출력 생성

## 위험 요소

- record offset 갱신 실패 시 파일이 열리지 않을 수 있다.
- Kindle 전용 metadata와 레이아웃 정보 보존이 어렵다.
- DRM 파일은 처리 대상이 아니다.

## 완료 기준

- 샘플 AZW3 1개 이상에서 번역된 output이 생성된다.
- 실패 시 원본 파일은 손상되지 않는다.
- AZW3 제한사항이 metadata와 로그에 기록된다.
