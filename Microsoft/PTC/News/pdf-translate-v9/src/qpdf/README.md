# qpdf

qpdf 실행 모듈 설계를 설명하는 디렉토리다.

qpdf availability check, QDF reference 생성, 원본/최종 PDF check를 담당한다.

## 책임

```text
qpdf 실행 파일 존재 확인
qpdf --qdf --object-streams=disable 실행
qpdf --check 실행
stdout/stderr/exit code를 JSON report로 저장
```

## 실패 원칙

```text
qpdf가 없으면 실패한다.
qpdf 검증 실패 시 publish 단계로 진행하지 않는다.
```
