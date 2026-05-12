# KFX Adapter 설계

## 목적

KFX 파일을 native adapter로 처리하기 위한 실행계획을 정의한다. KFX는 난이도가 가장 높으므로 MVP와 장기 목표를 분리한다.

## MVP 목표

- KFX 파일 인식
- 처리 가능 여부 판단
- 텍스트 fragment 후보 추출
- 가능한 샘플에서 번역 적용과 `.kfx` 저장 시도
- 미지원 구조는 명확한 skip 또는 failure로 기록

## Reader 책임

- KFX container signature 확인
- fragment 목록 탐색
- metadata fragment와 text fragment 구분
- DRM 또는 obfuscation 여부 감지
- 번역 가능한 text fragment 후보 수집

## Writer 책임

- 번역된 fragment를 원래 container 구조에 반영
- fragment 길이, checksum, index 갱신 필요 여부 확인
- 원본 resource fragment 보존
- `.kfx` 출력 생성

## 제한사항 기록

초기 구현에서는 다음을 명확히 기록해야 한다.

- enhanced typesetting 정보 보존 여부
- 위치 정보와 동기화 정보 보존 여부
- 지원 가능한 KFX variant
- 실패한 fragment type

## 완료 기준

- KFX 파일을 unsupported로만 끝내지 않고 구조 분석 결과를 metadata에 남긴다.
- 처리 가능한 샘플이 있으면 번역 output을 생성한다.
- 처리 불가 샘플은 명확한 reason으로 skip한다.
