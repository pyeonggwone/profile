# terms

고유명사와 용어집 처리 설계를 설명하는 디렉토리다.

v9는 job별로 PDF에서 추출한 고유명사 후보와 사용자가 확정한 번역 규칙을 저장한다.

```text
proper-noun-candidates.json  PDF에서 추출한 고유명사 후보
job-terms.json               job별 확정 용어집
term-application-report.json  번역 전/후 용어 적용 결과
```

고유명사는 PDF 구조 복원 정보와 분리해서 관리한다. text state/operator/font/CMap 정보는 raw-pdf-text-state.json에 남기고, 용어집은 OpenAI 번역 품질과 용어 일관성을 위해 사용한다.
