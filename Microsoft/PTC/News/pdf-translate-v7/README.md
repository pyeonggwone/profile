# pdf-translate-v7

PDF를 번역하지 않고, 원본과 같은 page size / image / vector drawing 구조만 새 PDF로 재구성한다.

텍스트 객체는 출력 PDF에 쓰지 않는다.

## 실행

```bash
./run-v7.sh input/sample.pdf
```

```bash
./run-v7.sh
```

## 입력과 출력

```text
input/sample.pdf -> output/sample_textless.pdf
work/<job-id>/state/object-manifest.json
work/<job-id>/pdf/textless.pdf
```

## 범위

| 기능 | 상태 |
|---|---|
| page size 유지 | O |
| image 추출/재삽입 | O |
| vector drawing 재구성 | O |
| 텍스트 제거 | O |
| OpenAI/Azure OpenAI | X |
| OCR | X |
| annotation/link/bookmark | X |
| form/AcroForm | X |
