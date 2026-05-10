| 기능 | pdf-translate-v1 | pdf-translate-v2 | pdf-translate-v3 | pdf-translate-v4 | pdf-translate-v5 | pdf-translate-v6 | pdf-translate-v7 |
|---|---|---|---|---|---|---|---|
| 프로젝트 성격 | 설계/기반 | v1 연동 자동화 | 자립형 통합 | rebuild 개선 | 품질 우선 다중엔진 | object manifest 단순화 | 구조 재생성+원문 재삽입 |
| 실행 가능한 전체 파이프라인 | X | △ | △ | △ | O | O | O |
| 단일 실행 스크립트 | X | O | O | O | O | O | O |
| input/output/work 구조 | X | O | O | O | O | O | O |
| 성공 원본 done 이동 | X | O | O | O | X | X | X |
| OpenAI 번역 | X | O | O | O | O | O | X |
| Azure OpenAI 번역 | X | O | O | O | O | X | X |
| Translation Memory SQLite | X | O | O | O | O | O | X |
| glossary 보호 | X | O | O | O | O | X | X |
| PDF 직접 구조 분석 | O | O | O | O | O | △ | O |
| stream/filter decode | O | O | O | O | △ | X | O |
| content stream `BT...ET` 추출 | O | X | X | X | △ | X | O |
| text bbox 추출 | X | O | O | O | O | O | X |
| image 추출/보존 | △ | X | X | O | O | O | O |
| vector/drawing 보존 | △ | X | X | O | △ | △ | △ |
| overlay 방식 | X | O | O | X | X | X | X |
| 새 PDF 재생성 | △ | X | X | O | O | O | O |
| 텍스트 제거 | X | X | X | X | X | X | O |
| 원문 `BT...ET` block 주입 | X | X | X | X | X | X | O |
| annotation/link/bookmark 보존 | △ | X | X | X | △ | X | X |
| OCR | X | X | X | X | O | X | X |
| table 인식 | X | X | X | X | O | X | X |
| CJK font/layout 보정 | X | X | △ | O | O | △ | △ |
| HarfBuzz/Pango/Cairo | X | X | X | X | O | X | X |
| render diff 품질 검증 | X | X | X | X | O | X | X |
| doctor/bootstrap | X | X | △ | △ | O | △ | △ |
| 최종 PDF publish | X | △ | △ | △ | O | O | O |
| smoke 검증 | X | X | X | △ | O | X | X |

