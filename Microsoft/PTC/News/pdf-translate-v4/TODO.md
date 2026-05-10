# TODO — pdf-translate-v4

## 구현 완료

- [x] v3 를 `pdf-translate-v4` 로 분리
- [x] 기본 출력 방식을 overlay 에서 rebuild 로 변경
- [x] 새 PDF 생성 후 원본 page size 유지
- [x] 원본 text object 를 출력 PDF로 복사하지 않음
- [x] 원본 vector drawing 재구성 (`page.get_drawings()`)
- [x] 원본 image block 재구성 (`page.get_text("dict")` image blocks)
- [x] 번역 텍스트를 bbox 기반 text box 로 삽입
- [x] embedded CJK font subsetting 적용
- [x] rebuild 모드에서 원문과 번역문이 같아도 텍스트 출력
- [x] 긴 번역문 text box 확장 / 줄바꿈 / font shrink 적용
- [x] PDF text object 형태의 도형 안 텍스트 추출 및 출력 경로 확인

## Smoke test

- [x] 작은 PDF rebuild self-test: 원문 텍스트 미복사, 번역 텍스트 삽입 확인
- [x] 도형 안 text object self-test: 추출 및 긴 한글 삽입 확인
- [x] 실제 IDC PDF extract smoke test: 46 페이지, 1837 세그먼트
- [ ] 실제 IDC PDF 로 전체 파이프라인 실행
- [ ] 결과 PDF 를 standard viewer 에서 육안 검수
- [ ] 원본 대비 파일 크기 비교

## 미해결 / 향후

- [ ] `page.get_drawings()` 로 복원되지 않는 복잡한 shading/pattern/transparency 처리
- [ ] 원본 annotations, links, outlines/bookmarks 복사
- [ ] image OCR / vision pass 로 이미지 안 텍스트 번역
- [ ] table cell / paragraph 단위 segment 병합 및 overflow 품질 개선
- [ ] page render diff 기반 자동 품질 점수 산출
